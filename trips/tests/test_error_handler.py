import time
from unittest.mock import patch

import pytest
from django.core.cache import cache

from trips.error_handler import (
    CircuitBreaker,
    CircuitOpenError,
    GeocodingError,
    RetryConfig,
    RoutingError,
    TripPlanningError,
    nominatim_breaker,
    osrm_breaker,
    with_retry,
)


class TestErrorHierarchy:
    """Test error class hierarchy and properties."""

    def test_trip_planning_error_base(self):
        err = TripPlanningError("test message")
        assert err.message == "test message"
        assert err.detail == "test message"
        assert err.status_code == 500

    def test_geocoding_error(self):
        err = GeocodingError("Geocode failed", "Invalid address")
        assert err.message == "Geocode failed"
        assert err.detail == "Invalid address"
        assert err.status_code == 502

    def test_routing_error(self):
        err = RoutingError("Route failed", "No route found")
        assert err.message == "Route failed"
        assert err.detail == "No route found"
        assert err.status_code == 502

    def test_circuit_open_error(self):
        err = CircuitOpenError("Circuit open")
        assert err.message == "Circuit open"
        assert err.status_code == 503


class TestRetryDecorator:
    """Test retry logic with exponential backoff."""

    def test_retry_succeeds_immediately(self):
        config = RetryConfig(max_retries=3)
        call_count = 0

        @with_retry(config)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = success_func()
        assert result == "ok"
        assert call_count == 1

    def test_retry_succeeds_after_failures(self):
        config = RetryConfig(max_retries=3, base_delay=0.01, max_delay=0.05)
        call_count = 0

        @with_retry(config)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "ok"

        result = flaky_func()
        assert result == "ok"
        assert call_count == 3

    def test_retry_exhausted(self):
        config = RetryConfig(max_retries=2, base_delay=0.01, max_delay=0.05)

        @with_retry(config)
        def always_fails():
            raise ValueError("persistent error")

        with pytest.raises(ValueError, match="persistent error"):
            always_fails()

    def test_retry_backoff_timing(self):
        config = RetryConfig(max_retries=2, base_delay=0.1, max_delay=0.2)
        call_times = []

        @with_retry(config)
        def timing_func():
            call_times.append(time.time())
            raise ConnectionError()

        with pytest.raises(ConnectionError):
            timing_func()

        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        assert delay1 >= 0.08
        assert delay1 <= 0.15
        assert delay2 >= 0.15
        assert delay2 <= 0.25


class TestCircuitBreaker:
    """Test circuit breaker state transitions and behavior."""

    def setup_method(self):
        cache.clear()

    def test_circuit_starts_closed(self):
        breaker = CircuitBreaker("test_service")
        assert breaker.get_state() == CircuitBreaker.CLOSED

    def test_circuit_opens_after_failures(self):
        breaker = CircuitBreaker(
            "test_service",
            failure_threshold=3,
            recovery_timeout=60,
        )

        def failing_func():
            raise ValueError("error")

        for _ in range(3):
            try:
                breaker.call(failing_func)
            except ValueError:
                pass

        assert breaker.get_state() == CircuitBreaker.OPEN

    def test_circuit_open_raises_immediately(self):
        breaker = CircuitBreaker("test_service", failure_threshold=1)

        def failing_func():
            raise ValueError("error")

        try:
            breaker.call(failing_func)
        except ValueError:
            pass

        assert breaker.get_state() == CircuitBreaker.OPEN

        with pytest.raises(CircuitOpenError):
            breaker.call(failing_func)

    def test_circuit_transitions_to_half_open(self):
        breaker = CircuitBreaker(
            "test_service",
            failure_threshold=1,
            recovery_timeout=1,
            success_threshold=1,
        )

        def failing_func():
            raise ValueError("error")

        try:
            breaker.call(failing_func)
        except ValueError:
            pass

        assert breaker.get_state() == CircuitBreaker.OPEN

        time.sleep(1.1)

        assert breaker.get_state() == CircuitBreaker.HALF_OPEN

    def test_circuit_closes_after_successes_in_half_open(self):
        breaker = CircuitBreaker(
            "test_service",
            failure_threshold=1,
            recovery_timeout=1,
            success_threshold=2,
        )

        def failing_func():
            raise ValueError("error")

        def success_func():
            return "ok"

        try:
            breaker.call(failing_func)
        except ValueError:
            pass

        assert breaker.get_state() == CircuitBreaker.OPEN

        time.sleep(1.1)

        assert breaker.get_state() == CircuitBreaker.HALF_OPEN

        breaker.call(success_func)
        assert breaker.get_state() == CircuitBreaker.HALF_OPEN

        breaker.call(success_func)
        assert breaker.get_state() == CircuitBreaker.CLOSED

    def test_record_success_in_closed_state(self):
        breaker = CircuitBreaker("test_service")

        def success_func():
            return "ok"

        assert breaker.get_state() == CircuitBreaker.CLOSED
        result = breaker.call(success_func)
        assert result == "ok"
        assert breaker.get_state() == CircuitBreaker.CLOSED

    def test_separate_breaker_instances(self):
        breaker1 = CircuitBreaker("service_a", failure_threshold=1)
        breaker2 = CircuitBreaker("service_b", failure_threshold=1)

        def fail():
            raise ValueError("error")

        try:
            breaker1.call(fail)
        except ValueError:
            pass

        assert breaker1.get_state() == CircuitBreaker.OPEN
        assert breaker2.get_state() == CircuitBreaker.CLOSED


class TestPreBuiltBreakers:
    """Test pre-built breaker instances."""

    def setup_method(self):
        cache.clear()

    def test_nominatim_breaker_exists(self):
        assert nominatim_breaker is not None
        assert nominatim_breaker.name == "nominatim"

    def test_osrm_breaker_exists(self):
        assert osrm_breaker is not None
        assert osrm_breaker.name == "osrm"


class TestIntegration:
    """Integration tests for error handling flow."""

    def setup_method(self):
        cache.clear()

    def test_circuit_breaker_protects_nominatim(self):
        nominatim_breaker_test = CircuitBreaker(
            "nominatim_test", failure_threshold=2, recovery_timeout=1
        )

        def nominatim_call():
            raise ConnectionError("Service down")

        for _ in range(2):
            try:
                nominatim_breaker_test.call(nominatim_call)
            except ConnectionError:
                pass

        assert nominatim_breaker_test.get_state() == CircuitBreaker.OPEN

        with pytest.raises(CircuitOpenError):
            nominatim_breaker_test.call(nominatim_call)

    def test_circuit_breaker_handles_cache_error_gracefully(self):
        """Test that cache errors don't crash the circuit breaker."""
        breaker = CircuitBreaker("cache_test")

        with patch("trips.error_handler.cache.get") as mock_cache_get:
            mock_cache_get.side_effect = Exception("Cache unavailable")

            state = breaker.get_state()
            assert state == CircuitBreaker.CLOSED

    def test_circuit_breaker_handles_invalid_timestamp(self):
        """Test that malformed timestamps are handled gracefully."""
        breaker = CircuitBreaker("timestamp_test")
        breaker_state_key = breaker._get_state_key()
        breaker_opened_key = breaker._get_opened_at_key()

        cache.set(breaker_state_key, CircuitBreaker.OPEN, None)
        cache.set(breaker_opened_key, "invalid-timestamp", None)

        state = breaker.get_state()
        assert state == CircuitBreaker.CLOSED
        assert cache.get(breaker_opened_key) is None
