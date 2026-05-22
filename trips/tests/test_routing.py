import unittest
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from trips.error_handler import GeocodingError, RoutingError
from trips.routing import geocode, get_route


@pytest.mark.integration
class TestGeocoding(unittest.TestCase):
    """Unit tests for Nominatim geocoding integration."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    @patch("trips.routing.requests.get")
    def test_geocode_valid_address(self, mock_get):
        """Test geocoding a valid address."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"lat": "41.8781", "lon": "-87.6298"}]
        mock_get.return_value = mock_response

        result = geocode("Chicago, IL")

        assert result == (41.8781, -87.6298)
        mock_get.assert_called_once()
        assert "Chicago" in mock_get.call_args[1]["params"]["q"]

    @patch("trips.routing.requests.get")
    def test_geocode_invalid_address(self, mock_get):
        """Test geocoding an invalid address raises GeocodingError."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        with self.assertRaises(GeocodingError):
            geocode("InvalidCityThatDoesNotExist")

    @patch("trips.routing.requests.get")
    def test_geocode_with_timeout(self, mock_get):
        """Test geocoding with timeout error."""
        mock_get.side_effect = TimeoutError("Request timed out")

        with self.assertRaises(TimeoutError):
            geocode("Chicago, IL")

    @patch("trips.routing.requests.get")
    def test_geocode_multiple_results(self, mock_get):
        """Test geocoding returns first result from multiple."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"lat": "41.8781", "lon": "-87.6298"},
            {"lat": "41.8811", "lon": "-87.6298"},
        ]
        mock_get.return_value = mock_response

        result = geocode("Chicago, IL")

        # Should return first result
        assert result == (41.8781, -87.6298)


@pytest.mark.integration
class TestRouting(unittest.TestCase):
    """Unit tests for OSRM routing integration."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    @patch("trips.routing.requests.get")
    def test_get_route_valid_waypoints(self, mock_get):
        """Test getting a valid route between waypoints."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "routes": [
                {
                    "geometry": {
                        "coordinates": [
                            [-87.6298, 41.8781],
                            [-87.5, 41.8],
                            [-86.1581, 39.7684],
                        ]
                    },
                    "legs": [
                        {"distance": 75000, "duration": 2700},  # leg 1: 75km, 45min
                        {"distance": 75000, "duration": 2700},  # leg 2: 75km, 45min
                    ],
                }
            ],
            "code": "Ok",
        }
        mock_get.return_value = mock_response

        origin = (41.8781, -87.6298)
        waypoint = (41.0, -87.0)
        destination = (39.7684, -86.1581)

        result = get_route(origin, waypoint, destination)

        assert result is not None
        assert "coordinates" in result
        assert "legs" in result
        assert len(result["legs"]) == 2
        assert result["legs"][0]["distance_miles"] > 0
        assert result["legs"][0]["duration_hours"] > 0

    @patch("trips.routing.requests.get")
    def test_get_route_no_route_found(self, mock_get):
        """Test routing when no route is found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": "NoRoute"}
        mock_get.return_value = mock_response

        with self.assertRaises(RoutingError):
            get_route(
                (41.8781, -87.6298),
                (50.0, -120.0),  # Unreachable waypoint
                (39.7684, -86.1581),
            )

    @patch("trips.routing.requests.get")
    def test_get_route_with_timeout(self, mock_get):
        """Test routing with timeout error."""
        mock_get.side_effect = TimeoutError("Request timed out")

        with self.assertRaises(TimeoutError):
            get_route((41.8781, -87.6298), (41.0, -87.0), (39.7684, -86.1581))

    @patch("trips.routing.requests.get")
    def test_get_route_distance_conversion(self, mock_get):
        """Test that distances are converted from meters to miles."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "routes": [
                {
                    "geometry": {
                        "coordinates": [[-87.6298, 41.8781], [-86.1581, 39.7684]]
                    },
                    "legs": [
                        {
                            "distance": 160934,
                            "duration": 36000,
                        },  # meters (100 miles), seconds (10 hours)
                    ],
                }
            ],
            "code": "Ok",
        }
        mock_get.return_value = mock_response

        result = get_route((41.8781, -87.6298), (40.0, -86.0), (39.7684, -86.1581))

        assert result is not None
        # 160934 meters = approximately 100 miles
        assert abs(result["legs"][0]["distance_miles"] - 100) < 1

    @patch("trips.routing.requests.get")
    def test_get_route_duration_conversion(self, mock_get):
        """Test that durations are converted from seconds to hours."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "routes": [
                {
                    "geometry": {
                        "coordinates": [[-87.6298, 41.8781], [-86.1581, 39.7684]]
                    },
                    "legs": [
                        {"distance": 160934, "duration": 36000},  # 10 hours in seconds
                    ],
                }
            ],
            "code": "Ok",
        }
        mock_get.return_value = mock_response

        result = get_route((41.8781, -87.6298), (40.0, -86.0), (39.7684, -86.1581))

        assert result is not None
        assert abs(result["legs"][0]["duration_hours"] - 10.0) < 0.01
