"""Cooldown state repository pattern."""
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("cooldown_repository")


class CooldownRepository(ABC):
    """Abstract base for cooldown state management."""

    @abstractmethod
    def is_active(self, key: str) -> bool:
        """Check if cooldown is active for a key."""

    @abstractmethod
    def set_cooldown(self, key: str, duration_seconds: int) -> None:
        """Set cooldown for a key."""

    @abstractmethod
    def clear_cooldown(self, key: str) -> None:
        """Clear cooldown for a key."""

    @abstractmethod
    def get_remaining_seconds(self, key: str) -> int:
        """Get remaining cooldown seconds. Returns 0 if not active."""


class InMemoryCooldown(CooldownRepository):
    """In-memory cooldown storage (development/testing)."""

    def __init__(self):
        self.state: dict[str, datetime] = {}

    def is_active(self, key: str) -> bool:
        if key not in self.state:
            return False
        if datetime.now() >= self.state[key]:
            del self.state[key]
            return False
        return True

    def set_cooldown(self, key: str, duration_seconds: int) -> None:
        expiry = datetime.now() + timedelta(seconds=duration_seconds)
        self.state[key] = expiry
        logger.debug(f"Cooldown set: {key} expires in {duration_seconds}s")

    def clear_cooldown(self, key: str) -> None:
        self.state.pop(key, None)
        logger.debug(f"Cooldown cleared: {key}")

    def get_remaining_seconds(self, key: str) -> int:
        if key not in self.state:
            return 0
        remaining = (self.state[key] - datetime.now()).total_seconds()
        return max(0, int(remaining))


class RedisCooldown(CooldownRepository):
    """Redis-backed cooldown storage (production)."""

    def __init__(self, redis_client):
        self.redis = redis_client

    def is_active(self, key: str) -> bool:
        ttl = self.redis.ttl(key)
        # ttl > 0 means key exists and has TTL
        # ttl = -1 means key exists with no expiry
        # ttl = -2 means key does not exist
        return ttl > 0 or ttl == -1

    def set_cooldown(self, key: str, duration_seconds: int) -> None:
        self.redis.setex(key, duration_seconds, "1")
        logger.debug(f"Cooldown set (Redis): {key} expires in {duration_seconds}s")

    def clear_cooldown(self, key: str) -> None:
        self.redis.delete(key)
        logger.debug(f"Cooldown cleared (Redis): {key}")

    def get_remaining_seconds(self, key: str) -> int:
        ttl = self.redis.ttl(key)
        if ttl <= 0:
            return 0
        return ttl


class CooldownFactory:
    """Factory for creating cooldown repositories."""

    _backends: dict[str, type[CooldownRepository]] = {
        "memory": InMemoryCooldown,
        "redis": RedisCooldown,
    }

    @classmethod
    def create(
        cls,
        backend: str = "memory",
        redis_client=None,
    ) -> CooldownRepository:
        """Create cooldown repository by backend name.

        Args:
            backend: "memory" (default) or "redis"
            redis_client: Required if backend="redis"

        Returns:
            CooldownRepository instance
        """
        if backend == "redis":
            if not redis_client:
                raise ValueError("redis_client required for redis backend")
            return RedisCooldown(redis_client)
        elif backend == "memory":
            return InMemoryCooldown()
        else:
            raise ValueError(f"Unknown backend: {backend}")
