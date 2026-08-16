"""Tests for resilience (circuit breaker + retry)."""
import time
import pytest

from backend.services.resilience import (
    CircuitBreaker,
    CircuitState,
    retry,
    get_circuit_breaker,
)


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_circuit_initially_closed(self):
        """Circuit should start in CLOSED state."""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_circuit_opens_after_threshold(self):
        """Circuit should open after failure threshold is reached."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=60)

        def failing_func():
            raise ValueError("Test error")

        # First failure
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.CLOSED

        # Second failure — triggers OPEN
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

    def test_circuit_fails_fast_when_open(self):
        """Circuit should fail fast when OPEN without calling function."""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=60)

        def failing_func():
            raise ValueError("Should not be called")

        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

        # Second call should fail fast (different exception)
        with pytest.raises(Exception, match="Circuit .* is OPEN"):
            cb.call(failing_func)

    def test_circuit_enters_half_open_after_timeout(self):
        """Circuit should enter HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1)

        def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        with pytest.raises(ValueError):
            cb.call(failing_func)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Next call should attempt recovery (HALF_OPEN)
        with pytest.raises(ValueError):
            cb.call(failing_func)
        # State should still be HALF_OPEN after failed attempt
        assert cb.state in (CircuitState.HALF_OPEN, CircuitState.OPEN)

    def test_circuit_closes_after_successful_call(self):
        """Circuit should close (return to normal) after successful call."""
        cb = CircuitBreaker("test", failure_threshold=2)

        def working_func():
            return "success"

        result = cb.call(working_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0


class TestRetryDecorator:
    """Test retry decorator with exponential backoff."""

    def test_retry_succeeds_on_first_attempt(self):
        """Retry should return immediately on success."""
        @retry(max_attempts=3, initial_delay=0.01)
        def working_func():
            return "success"

        result = working_func()
        assert result == "success"

    def test_retry_fails_after_max_attempts(self):
        """Retry should fail after max attempts exceeded."""
        attempt_count = 0

        @retry(max_attempts=2, initial_delay=0.01)
        def failing_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_func()
        assert attempt_count == 2

    def test_retry_succeeds_after_failures(self):
        """Retry should succeed if function eventually succeeds."""
        attempt_count = 0

        @retry(max_attempts=3, initial_delay=0.01)
        def eventually_working():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not yet")
            return "success"

        result = eventually_working()
        assert result == "success"
        assert attempt_count == 3

    def test_retry_preserves_return_value(self):
        """Retry should preserve function return value."""
        @retry(max_attempts=1, initial_delay=0.01)
        def return_dict():
            return {"key": "value", "count": 42}

        result = return_dict()
        assert result == {"key": "value", "count": 42}


class TestGlobalCircuitBreakers:
    """Test global circuit breaker registry."""

    def test_get_circuit_breaker_creates_if_missing(self):
        """get_circuit_breaker should create new one if not found."""
        cb = get_circuit_breaker("new_service")
        assert cb is not None
        assert cb.state == CircuitState.CLOSED

    def test_get_circuit_breaker_returns_existing(self):
        """get_circuit_breaker should return existing instance."""
        cb1 = get_circuit_breaker("existing_service")
        cb2 = get_circuit_breaker("existing_service")
        assert cb1 is cb2

    def test_predefined_circuit_breakers_exist(self):
        """Should have predefined breakers for yfinance, redis, database."""
        for name in ["yfinance", "redis", "database"]:
            cb = get_circuit_breaker(name)
            assert cb.state == CircuitState.CLOSED
