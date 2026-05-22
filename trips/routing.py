import json
import os
from functools import wraps

import requests
from django.core.cache import cache

from trips.error_handler import (
    GeocodingError,
    RetryConfig,
    RoutingError,
    nominatim_breaker,
    osrm_breaker,
    with_retry,
)

NOMINATIM_URL = os.environ.get(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"
)
OSRM_URL = os.environ.get(
    "OSRM_URL", "https://router.project-osrm.org/route/v1/driving"
)

# User-Agent for external API requests (avoid personal email)
USER_AGENT = os.environ.get(
    "API_USER_AGENT", "SpotterELD/1.0 (support@spotter-eld.app)"
)

# API Request timeouts (seconds)
NOMINATIM_TIMEOUT = int(os.environ.get("NOMINATIM_TIMEOUT", "10"))
OSRM_TIMEOUT = int(os.environ.get("OSRM_TIMEOUT", "30"))

# Cache TTL in seconds (24 hours for geocoding, 48 hours for routes)
GEOCODE_CACHE_TIMEOUT = int(os.environ.get("GEOCODE_CACHE_TIMEOUT", "86400"))
ROUTE_CACHE_TIMEOUT = int(os.environ.get("ROUTE_CACHE_TIMEOUT", "172800"))

# Route distance limits (miles)
MIN_ROUTE_DISTANCE = 0.1
MAX_ROUTE_DISTANCE = 10000


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from function arguments (memcached-safe)."""
    import hashlib

    args_key = json.dumps(args, sort_keys=True, default=str)
    kwargs_key = json.dumps(sorted(kwargs.items()), default=str)
    combined = f"{args_key}{kwargs_key}"
    hash_val = hashlib.md5(combined.encode()).hexdigest()
    return f"{prefix}_{hash_val}"


def _validate_route(legs: list[dict]) -> None:
    """Validate route legs for distance sanity and sequence.

    Raises ValueError if route appears invalid or suspicious.
    """
    if not legs or len(legs) != 2:
        raise ValueError(
            "Route must have exactly 2 legs (origin→waypoint→destination)."
        )

    leg1_miles = legs[0]["distance_miles"]
    leg2_miles = legs[1]["distance_miles"]

    # leg 0 (current→pickup) may be 0 when driver is already at pickup location
    if leg2_miles < MIN_ROUTE_DISTANCE:
        raise ValueError("Pickup to dropoff distance must be at least 0.1 miles.")

    total_miles = leg1_miles + leg2_miles
    if total_miles > MAX_ROUTE_DISTANCE:
        raise ValueError(
            f"Route distance {total_miles:.1f} miles exceeds maximum "
            f"of {MAX_ROUTE_DISTANCE} miles. Check location input."
        )


def _cached_api_call(timeout: int, key_prefix: str):
    """Decorator to cache API call results."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = _make_cache_key(key_prefix, *args, **kwargs)
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator


@_cached_api_call(GEOCODE_CACHE_TIMEOUT, "geocode")
@with_retry(RetryConfig(max_retries=3, base_delay=1.0, max_delay=8.0))
def _geocode_call(address: str) -> tuple[float, float]:
    """Internal geocoding call with retry logic."""
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=NOMINATIM_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(
            f"Could not geocode address: '{address}'. Please check the spelling."
        )
    return float(data[0]["lat"]), float(data[0]["lon"])


def geocode(address: str) -> tuple[float, float]:
    """Return (lat, lon) for a given address string using Nominatim.

    Uses circuit breaker to fail gracefully if Nominatim is down.
    Raises GeocodingError on failure (but lets Timeout bubble up to caller).
    """
    try:
        return nominatim_breaker.call(_geocode_call, address)
    except requests.exceptions.Timeout:
        raise
    except (requests.exceptions.RequestException, ValueError) as e:
        raise GeocodingError(
            f"Nominatim API error for '{address}'",
            detail="Unable to look up location. Please try again.",
        ) from e


@_cached_api_call(ROUTE_CACHE_TIMEOUT, "route")
@with_retry(RetryConfig(max_retries=3, base_delay=1.0, max_delay=8.0))
def _get_route_call(
    origin_ll: tuple[float, float],
    waypoint_ll: tuple[float, float],
    dest_ll: tuple[float, float],
) -> dict:
    """Internal route calculation call with retry logic."""
    coords_str = (
        f"{origin_ll[1]},{origin_ll[0]};"
        f"{waypoint_ll[1]},{waypoint_ll[0]};"
        f"{dest_ll[1]},{dest_ll[0]}"
    )
    resp = requests.get(
        f"{OSRM_URL}/{coords_str}",
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
        timeout=OSRM_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("OSRM could not find a route between the provided locations.")

    route = data["routes"][0]
    legs = []
    for leg in route["legs"]:
        legs.append(
            {
                "distance_miles": leg["distance"] / 1609.344,
                "duration_hours": leg["duration"] / 3600,
            }
        )

    _validate_route(legs)
    coordinates = route["geometry"]["coordinates"]
    return {"coordinates": coordinates, "legs": legs}


def get_route(
    origin_ll: tuple[float, float],
    waypoint_ll: tuple[float, float],
    dest_ll: tuple[float, float],
) -> dict:
    """Fetch a driving route from origin -> waypoint -> destination via OSRM.

    Uses circuit breaker to fail gracefully if OSRM is down.
    Raises RoutingError on failure (but lets Timeout bubble up to caller).

    Returns:
        {
            "coordinates": [[lon, lat], ...],  # GeoJSON-style
            "legs": [
                {"distance_miles": float, "duration_hours": float},
                {"distance_miles": float, "duration_hours": float},
            ]
        }
    """
    try:
        return osrm_breaker.call(_get_route_call, origin_ll, waypoint_ll, dest_ll)
    except requests.exceptions.Timeout:
        raise
    except (requests.exceptions.RequestException, ValueError) as e:
        raise RoutingError(
            "OSRM routing API error",
            detail="Unable to calculate route. Please try again.",
        ) from e
