"""Circuit breaker + retry logic for resilience."""
import logging
import time
from enum import Enum
from typing import Callable, TypeVar, Optional
from functools import wraps

logger = logging.getLogger("resilience")

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Working normally
    OPEN = "open"      # Failing, reject fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time > self.recovery_timeout
            ):
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit {self.name} entering HALF_OPEN state")
            else:
                raise Exception(
                    f"Circuit {self.name} is OPEN, failing fast"
                )

        try:
            result = func(*args, **kwargs)
            # Success: reset state
            if self.state != CircuitState.CLOSED:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info(f"Circuit {self.name} recovered to CLOSED state")
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(
                    f"Circuit {self.name} opened after {self.failure_count} failures: {e}"
                )

            raise


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
):
    """Retry decorator with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )

            raise last_exception or Exception(
                f"{func.__name__} failed after {max_attempts} attempts"
            )

        return wrapper
    return decorator


# Global circuit breakers
circuit_breakers = {
    "yfinance": CircuitBreaker("yfinance", failure_threshold=3, recovery_timeout=60),
    "redis": CircuitBreaker("redis", failure_threshold=5, recovery_timeout=30),
    "database": CircuitBreaker("database", failure_threshold=3, recovery_timeout=60),
}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """Get or create a circuit breaker."""
    if name not in circuit_breakers:
        circuit_breakers[name] = CircuitBreaker(name)
    return circuit_breakers[name]
