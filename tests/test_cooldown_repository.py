"""Tests for CooldownRepository pattern."""
import time
from unittest.mock import MagicMock

import pytest

from backend.services.cooldown_repository import (
    CooldownFactory,
    InMemoryCooldown,
    RedisCooldown,
)


class TestInMemoryCooldown:
    """Test in-memory cooldown implementation."""

    def test_cooldown_initially_inactive(self):
        """Cooldown should be inactive for new keys."""
        repo = InMemoryCooldown()
        assert not repo.is_active("test_key")

    def test_set_cooldown_activates_key(self):
        """Setting cooldown should activate the key."""
        repo = InMemoryCooldown()
        repo.set_cooldown("test_key", 10)
        assert repo.is_active("test_key")

    def test_cooldown_expires_after_duration(self):
        """Cooldown should expire after duration passes."""
        repo = InMemoryCooldown()
        repo.set_cooldown("test_key", 1)  # 1 second
        assert repo.is_active("test_key")
        time.sleep(1.1)
        assert not repo.is_active("test_key")

    def test_clear_cooldown_deactivates_key(self):
        """Clearing cooldown should deactivate the key."""
        repo = InMemoryCooldown()
        repo.set_cooldown("test_key", 10)
        assert repo.is_active("test_key")
        repo.clear_cooldown("test_key")
        assert not repo.is_active("test_key")

    def test_get_remaining_seconds_returns_positive(self):
        """Remaining seconds should be positive while active."""
        repo = InMemoryCooldown()
        repo.set_cooldown("test_key", 10)
        remaining = repo.get_remaining_seconds("test_key")
        assert remaining > 0
        assert remaining <= 10

    def test_get_remaining_seconds_returns_zero_when_inactive(self):
        """Remaining seconds should be 0 when cooldown is inactive."""
        repo = InMemoryCooldown()
        remaining = repo.get_remaining_seconds("nonexistent_key")
        assert remaining == 0

    def test_multiple_keys_independent(self):
        """Different keys should have independent cooldowns."""
        repo = InMemoryCooldown()
        repo.set_cooldown("key1", 10)
        repo.set_cooldown("key2", 5)
        assert repo.is_active("key1")
        assert repo.is_active("key2")
        repo.clear_cooldown("key1")
        assert not repo.is_active("key1")
        assert repo.is_active("key2")


class TestRedisCooldown:
    """Test Redis-backed cooldown implementation."""

    def test_cooldown_inactive_when_key_missing(self):
        """Cooldown should be inactive when Redis key missing (TTL=-2)."""
        mock_redis = MagicMock()
        mock_redis.ttl.return_value = -2  # Key missing
        repo = RedisCooldown(mock_redis)
        assert not repo.is_active("test_key")

    def test_cooldown_active_with_ttl(self):
        """Cooldown should be active when Redis key has TTL."""
        mock_redis = MagicMock()
        mock_redis.ttl.return_value = 5  # 5 seconds remaining
        repo = RedisCooldown(mock_redis)
        assert repo.is_active("test_key")

    def test_cooldown_active_with_no_expiry(self):
        """Cooldown should be active when Redis key has no expiry (TTL=-1)."""
        mock_redis = MagicMock()
        mock_redis.ttl.return_value = -1  # No expiry
        repo = RedisCooldown(mock_redis)
        assert repo.is_active("test_key")

    def test_set_cooldown_calls_redis_setex(self):
        """Setting cooldown should call Redis setex."""
        mock_redis = MagicMock()
        repo = RedisCooldown(mock_redis)
        repo.set_cooldown("test_key", 10)
        mock_redis.setex.assert_called_once_with("test_key", 10, "1")

    def test_clear_cooldown_calls_redis_delete(self):
        """Clearing cooldown should call Redis delete."""
        mock_redis = MagicMock()
        repo = RedisCooldown(mock_redis)
        repo.clear_cooldown("test_key")
        mock_redis.delete.assert_called_once_with("test_key")

    def test_get_remaining_seconds_returns_ttl(self):
        """Remaining seconds should return Redis TTL."""
        mock_redis = MagicMock()
        mock_redis.ttl.return_value = 7
        repo = RedisCooldown(mock_redis)
        remaining = repo.get_remaining_seconds("test_key")
        assert remaining == 7

    def test_get_remaining_seconds_returns_zero_when_missing(self):
        """Remaining seconds should be 0 when key missing."""
        mock_redis = MagicMock()
        mock_redis.ttl.return_value = -2
        repo = RedisCooldown(mock_redis)
        remaining = repo.get_remaining_seconds("test_key")
        assert remaining == 0


class TestCooldownFactory:
    """Test factory pattern for cooldown repositories."""

    def test_factory_creates_memory_backend_by_default(self):
        """Factory should create in-memory backend by default."""
        repo = CooldownFactory.create()
        assert isinstance(repo, InMemoryCooldown)

    def test_factory_creates_memory_backend_explicitly(self):
        """Factory should create in-memory backend when requested."""
        repo = CooldownFactory.create(backend="memory")
        assert isinstance(repo, InMemoryCooldown)

    def test_factory_creates_redis_backend_with_client(self):
        """Factory should create Redis backend when client provided."""
        mock_redis = MagicMock()
        repo = CooldownFactory.create(backend="redis", redis_client=mock_redis)
        assert isinstance(repo, RedisCooldown)

    def test_factory_raises_error_for_unknown_backend(self):
        """Factory should raise error for unknown backend."""
        with pytest.raises(ValueError, match="Unknown backend"):
            CooldownFactory.create(backend="unknown")

    def test_factory_raises_error_for_redis_without_client(self):
        """Factory should raise error for Redis backend without client."""
        with pytest.raises(ValueError, match="redis_client required"):
            CooldownFactory.create(backend="redis")
