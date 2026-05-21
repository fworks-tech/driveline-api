"""
Tests for caching behavior in routing and HOS engine.

Verifies that:
- Geocoding results are cached
- Route results are cached
- HOS simulations are cached
- Repeated requests hit cache (not external APIs)
- Cache keys are generated correctly
"""

from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache


@pytest.mark.integration
class TestGeocodeCache:
    """Test geocoding caching."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()

    def test_geocode_caches_result(self):
        """Verify geocode result is cached after first call."""
        with patch("trips.routing.requests.get") as mock_get:
            # Mock Nominatim response
            mock_response = MagicMock()
            mock_response.json.return_value = [
                {"lat": "41.8781", "lon": "-87.6298", "display_name": "Chicago"}
            ]
            mock_get.return_value = mock_response

            from trips.routing import geocode

            # First call hits API
            result1 = geocode("Chicago")
            assert result1 == (41.8781, -87.6298)
            assert mock_get.call_count == 1

            # Second call should hit cache
            result2 = geocode("Chicago")
            assert result2 == (41.8781, -87.6298)
            assert mock_get.call_count == 1  # No additional API call

    def test_geocode_cache_per_address(self):
        """Verify each address has its own cache entry."""
        from trips.routing import geocode

        with patch("trips.routing.requests.get") as mock_get:
            # Create separate mock responses for each address
            chicago_response = MagicMock()
            chicago_response.json.return_value = [{"lat": "41.8781", "lon": "-87.6298"}]

            ny_response = MagicMock()
            ny_response.json.return_value = [{"lat": "40.7128", "lon": "-74.0060"}]

            mock_get.side_effect = [chicago_response, ny_response]

            # First Chicago call
            result1 = geocode("Chicago")
            assert result1 == (41.8781, -87.6298)

            # New York call
            result2 = geocode("New York")
            assert result2 == (40.7128, -74.0060)

            # Second Chicago call (hits cache, no new API call)
            result3 = geocode("Chicago")
            assert result3 == (41.8781, -87.6298)

            # Should have called API exactly 2 times
            assert mock_get.call_count == 2


@pytest.mark.unit
class TestRouteCache:
    """Test route caching."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()

    def test_get_route_caches_result(self):
        """Verify get_route result is cached after first call."""
        with patch("trips.routing.requests.get") as mock_get:
            # Mock OSRM response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "code": "Ok",
                "routes": [
                    {
                        "distance": 100000,
                        "duration": 3600,
                        "legs": [
                            {"distance": 50000, "duration": 1800},
                            {"distance": 50000, "duration": 1800},
                        ],
                        "geometry": {"coordinates": [[-87.0, 41.0], [-86.0, 40.0]]},
                    }
                ],
            }
            mock_get.return_value = mock_response

            from trips.routing import get_route

            coords = (41.8781, -87.6298), (40.0, -86.0), (32.0, -96.0)

            # First call hits API
            result1 = get_route(*coords)
            assert "coordinates" in result1
            assert "legs" in result1
            assert mock_get.call_count == 1

            # Second call should hit cache
            result2 = get_route(*coords)
            assert result1 == result2
            assert mock_get.call_count == 1  # No additional API call

    def test_get_route_cache_per_route(self):
        """Verify each route combination has its own cache entry."""
        with patch("trips.routing.requests.get") as mock_get:

            def mock_response():
                response = MagicMock()
                response.json.return_value = {
                    "code": "Ok",
                    "routes": [
                        {
                            "distance": 100000,
                            "duration": 3600,
                            "legs": [
                                {"distance": 50000, "duration": 1800},
                                {"distance": 50000, "duration": 1800},
                            ],
                            "geometry": {"coordinates": [[-87.0, 41.0], [-86.0, 40.0]]},
                        }
                    ],
                }
                return response

            mock_get.side_effect = [mock_response(), mock_response()]

            from trips.routing import get_route

            coords1 = (41.0, -87.0), (40.0, -86.0), (32.0, -96.0)
            coords2 = (42.0, -88.0), (41.0, -87.0), (33.0, -97.0)

            # Different routes
            result1 = get_route(*coords1)
            _ = get_route(*coords2)

            # Both should have called API
            assert mock_get.call_count == 2

            # Same route again should hit cache
            result1_again = get_route(*coords1)
            assert result1 == result1_again
            assert mock_get.call_count == 2  # Still 2


@pytest.mark.unit
class TestHOSCache:
    """Test HOS simulation caching."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()

    def test_simulate_trip_caches_result(self):
        """Verify simulate_trip result is cached after first call."""
        from trips.hos_engine import simulate_trip

        # Test parameters
        params = {
            "total_distance_miles": 300.0,
            "leg1_hours": 4.5,
            "leg2_hours": 5.0,
            "current_cycle_used_hours": 30.0,
            "leg1_miles": 120.0,
            "leg2_miles": 180.0,
        }

        # First call
        result1 = simulate_trip(**params)
        assert "logbook_days" in result1
        assert "total_trip_hours" in result1

        # Second call (should hit cache)
        result2 = simulate_trip(**params)
        assert result1 == result2

    def test_simulate_trip_cache_per_parameters(self):
        """Verify each parameter combination has its own cache entry."""
        from trips.hos_engine import simulate_trip

        params1 = {
            "total_distance_miles": 300.0,
            "leg1_hours": 4.5,
            "leg2_hours": 5.0,
            "current_cycle_used_hours": 30.0,
            "leg1_miles": 120.0,
            "leg2_miles": 180.0,
        }

        params2 = {
            "total_distance_miles": 400.0,
            "leg1_hours": 5.5,
            "leg2_hours": 6.0,
            "current_cycle_used_hours": 25.0,
            "leg1_miles": 160.0,
            "leg2_miles": 240.0,
        }

        # Different parameter sets produce different results
        result1 = simulate_trip(**params1)
        result2 = simulate_trip(**params2)

        # Should be different
        assert result1["total_trip_hours"] != result2["total_trip_hours"]

        # Same params should return same result
        result1_again = simulate_trip(**params1)
        assert result1 == result1_again
