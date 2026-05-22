import functools
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)


class TripPlanningError(Exception):
    """Base exception for trip planning errors."""

    status_code = 500

    def __init__(self, message: str, detail: Optional[str] = None):
        self.message = message
        self.detail = detail or message
        super().__init__(message)


class GeocodingError(TripPlanningError):
    """Raised when geocoding (location lookup) fails."""

    status_code = 502


class RoutingError(TripPlanningError):
    """Raised when route calculation fails."""

    status_code = 502


class CircuitOpenError(TripPlanningError):
    """Raised when a circuit breaker is open (service is failing)."""

    status_code = 503


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 8.0
    jitter: bool = True


def with_retry(config: Optional[RetryConfig] = None) -> Callable:
    """Decorator that retries a function with exponential backoff and jitter.

    Retries on transient errors (ConnectionError, etc.) but not on timeouts or
    bad responses. ValueError from bad API responses (empty results) is not retried.

    Args:
        config: RetryConfig with backoff settings. Defaults to 3 retries, 1s-8s delays.
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import requests

            last_exception = None
            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout:
                    raise
                except ValueError:
                    raise
                except requests.exceptions.ConnectionError as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = min(config.base_delay * (2**attempt), config.max_delay)
                        if config.jitter:
                            delay *= 0.9 + random.random() * 0.2
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_retries} for {func.__name__} "
                            f"after {delay:.2f}s due to {type(e).__name__}"
                        )
                        time.sleep(delay)
                    else:
                        raise

            raise last_exception

        return wrapper

    return decorator


class CircuitBreaker:
    """Redis-backed circuit breaker for external service calls.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests rejected immediately
    - HALF_OPEN: Testing if service recovered, allow limited requests
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        """Initialize circuit breaker.

        Args:
            name: Unique name for this breaker (used as cache key prefix)
            failure_threshold: Open circuit after this many failures
            recovery_timeout: Seconds before trying to recover (half-open)
            success_threshold: Successes needed in half-open to close
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

    def _get_state_key(self) -> str:
        return f"circuit:{self.name}:state"

    def _get_failures_key(self) -> str:
        return f"circuit:{self.name}:failures"

    def _get_opened_at_key(self) -> str:
        return f"circuit:{self.name}:opened_at"

    def _get_half_open_successes_key(self) -> str:
        return f"circuit:{self.name}:half_open_successes"

    def get_state(self) -> str:
        """Get current circuit state."""
        try:
            state = cache.get(self._get_state_key(), self.CLOSED)
            if state == self.OPEN:
                opened_at = cache.get(self._get_opened_at_key())
                if opened_at:
                    try:
                        opened_time = datetime.fromisoformat(opened_at)
                        if (
                            opened_time + timedelta(seconds=self.recovery_timeout)
                            < datetime.utcnow()
                        ):
                            self._transition_to_half_open()
                            return self.HALF_OPEN
                    except (ValueError, TypeError) as e:
                        logger.error(
                            f"Failed to parse circuit breaker timestamp for '{self.name}': {e}"
                        )
                        cache.delete(self._get_opened_at_key())
                        return self.CLOSED
            return state
        except Exception as e:
            logger.error(
                f"Cache error in circuit breaker '{self.name}': {e}. "
                f"Defaulting to CLOSED state."
            )
            return self.CLOSED

    def _transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN state."""
        cache.set(self._get_state_key(), self.HALF_OPEN, None)
        cache.set(self._get_half_open_successes_key(), 0, None)
        logger.info(f"Circuit breaker '{self.name}' entering half-open state")

    def record_success(self) -> None:
        """Record a successful request."""
        state = cache.get(self._get_state_key(), self.CLOSED)
        if state == self.HALF_OPEN:
            successes = cache.get(self._get_half_open_successes_key(), 0) + 1
            cache.set(self._get_half_open_successes_key(), successes, None)
            if successes >= self.success_threshold:
                cache.set(self._get_state_key(), self.CLOSED, None)
                cache.delete(self._get_failures_key())
                cache.delete(self._get_opened_at_key())
                cache.delete(self._get_half_open_successes_key())
                logger.info(f"Circuit breaker '{self.name}' closed")
        elif state == self.CLOSED:
            cache.set(self._get_failures_key(), 0, None)

    def record_failure(self) -> None:
        """Record a failed request."""
        state = cache.get(self._get_state_key(), self.CLOSED)
        if state == self.OPEN:
            return

        failures = cache.get(self._get_failures_key(), 0) + 1
        cache.set(self._get_failures_key(), failures, None)

        if failures >= self.failure_threshold:
            cache.set(self._get_state_key(), self.OPEN, None)
            cache.set(self._get_opened_at_key(), datetime.utcnow().isoformat(), None)
            logger.error(
                f"Circuit breaker '{self.name}' opened after {failures} failures"
            )

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Raises:
            CircuitOpenError: If circuit is open

        Returns:
            Result of func(*args, **kwargs)
        """
        if self.get_state() == self.OPEN:
            raise CircuitOpenError(
                f"Circuit breaker '{self.name}' is open",
                detail=f"Service temporarily unavailable. Try again in {self.recovery_timeout}s.",
            )

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


nominatim_breaker = CircuitBreaker(
    name="nominatim",
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=2,
)
osrm_breaker = CircuitBreaker(
    name="osrm",
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=2,
)
