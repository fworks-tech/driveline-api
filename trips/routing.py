import json
from functools import wraps

import requests
from django.core.cache import cache

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

# Cache TTL in seconds (24 hours for geocoding, 48 hours for routes)
GEOCODE_CACHE_TIMEOUT = 86400
ROUTE_CACHE_TIMEOUT = 172800


def _make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a cache key from function arguments (memcached-safe)."""
    import hashlib

    args_key = json.dumps(args, sort_keys=True, default=str)
    kwargs_key = json.dumps(kwargs, sort_keys=True, default=str)
    combined = f"{args_key}{kwargs_key}"
    hash_val = hashlib.md5(combined.encode()).hexdigest()
    return f"{prefix}_{hash_val}"


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
def geocode(address: str) -> tuple[float, float]:
    """Return (lat, lon) for a given address string using Nominatim."""
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": "SpotterELD/1.0 (fritzelborges@gmail.com)"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(
            f"Could not geocode address: '{address}'. Please check the spelling."
        )
    return float(data[0]["lat"]), float(data[0]["lon"])


@_cached_api_call(ROUTE_CACHE_TIMEOUT, "route")
def get_route(
    origin_ll: tuple[float, float],
    waypoint_ll: tuple[float, float],
    dest_ll: tuple[float, float],
) -> dict:
    """
    Fetch a driving route from origin -> waypoint -> destination via OSRM.

    Returns:
        {
            "coordinates": [[lon, lat], ...],  # GeoJSON-style
            "legs": [
                {"distance_miles": float, "duration_hours": float},
                {"distance_miles": float, "duration_hours": float},
            ]
        }
    """
    coords_str = (
        f"{origin_ll[1]},{origin_ll[0]};"
        f"{waypoint_ll[1]},{waypoint_ll[0]};"
        f"{dest_ll[1]},{dest_ll[0]}"
    )
    resp = requests.get(
        f"{OSRM_URL}/{coords_str}",
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
        timeout=30,
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

    coordinates = route["geometry"]["coordinates"]  # [[lon, lat], ...]
    return {"coordinates": coordinates, "legs": legs}
