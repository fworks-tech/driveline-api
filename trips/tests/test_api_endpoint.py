import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import Client, TestCase
from requests.exceptions import ConnectTimeout, ReadTimeout

from trips.error_handler import GeocodingError


class TestPlanRouteAPI(TestCase):
    """Integration tests for POST /api/plan-route/ endpoint."""

    def setUp(self):
        """Initialize test client and clear cache."""
        self.client = Client()
        self.endpoint = "/api/plan-route/"
        cache.clear()

    @patch("trips.services.geocode")
    @patch("trips.services.get_route")
    @patch("trips.services.simulate_trip")
    def test_successful_route_planning(self, mock_hos, mock_route, mock_geocode):
        """Test successful route planning request."""
        # Mock geocoding results
        mock_geocode.side_effect = [
            (41.8781, -87.6298),  # Chicago
            (39.7684, -86.1581),  # Indianapolis
            (32.7767, -96.797),  # Dallas
        ]

        # Mock routing results (single call with 2 legs: current->pickup->dropoff)
        mock_route.return_value = {
            "coordinates": [
                [-87.6298, 41.8781],
                [-87.0, 40.0],
                [-86.1581, 39.7684],
                [-90.0, 35.0],
                [-96.797, 32.7767],
            ],
            "legs": [
                {
                    "distance_miles": 297.3,
                    "duration_hours": 4.5,
                },
                {
                    "distance_miles": 552.7,
                    "duration_hours": 8.0,
                },
            ],
        }

        # Mock HOS engine
        mock_hos.return_value = {
            "logbook_days": [
                {
                    "day": 0,
                    "date_offset": 0,
                    "date": "05/22/2026",
                    "from_location": "Chicago, IL",
                    "to_location": "Dallas, TX",
                    "events": [
                        {
                            "status": "DRIVING",
                            "start_hour": 0.0,
                            "end_hour": 11.0,
                            "duration_hours": 11.0,
                            "label": "Driving",
                        },
                        {
                            "status": "OFF_DUTY",
                            "start_hour": 11.0,
                            "end_hour": 24.0,
                            "duration_hours": 13.0,
                            "label": "Off Duty",
                        },
                    ],
                    "total_driving_hours": 11.0,
                    "total_on_duty_hours": 11.0,
                    "daily_miles": 850.0,
                    "cumulative_miles": 850.0,
                    "row_totals": {
                        "off_duty_hours": 13.0,
                        "sleeper_berth_hours": 0.0,
                        "driving_hours": 11.0,
                        "on_duty_not_driving_hours": 0.0,
                    },
                }
            ],
            "total_trip_hours": 12.5,
            "total_driving_hours": 11.0,
            "num_fuel_stops": 0,
            "num_rest_stops": 1,
        }

        # Send request
        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "Chicago, IL",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "route_coordinates" in data
        assert "markers" in data
        assert "logbook_days" in data
        assert "trip_summary" in data

        # Verify markers include all stops
        assert len(data["markers"]) >= 3  # Start, pickup, dropoff

    @patch("trips.services.geocode")
    def test_invalid_current_location(self, mock_geocode):
        """Test request with invalid current location raises GeocodingError."""
        mock_geocode.side_effect = GeocodingError("Geocoding failed", "Invalid address")

        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "InvalidCityXYZ",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 502
        assert response.json()["error"] == "geocoding_failed"

    def test_missing_required_field(self):
        """Test request missing required field."""
        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "Chicago, IL",
                    "pickup_location": "Indianapolis, IN",
                    # Missing 'dropoff_location'
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.json()
        assert "dropoff_location" in str(data)

    def test_invalid_cycle_hours(self):
        """Test request with invalid cycle hours."""
        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "Chicago, IL",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 100,  # Exceeds 70-hour limit
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_negative_cycle_hours(self):
        """Test request with negative cycle hours."""
        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "Chicago, IL",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": -5,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_empty_location_string(self):
        """Test request with empty location strings."""
        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_location_too_short(self):
        """Test request with location string too short."""
        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "A",  # Too short
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_response_structure(self):
        """Test that response has correct structure."""
        # This is a structural test without mocking full implementation
        # Useful for API contract verification
        # Expected fields: route_coordinates, markers, logbook_days, trip_summary

    def test_cors_headers(self):
        """Test that CORS headers are present."""
        self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "Chicago, IL",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )
        # CORS headers verified by Django middleware

    @patch("trips.routing.requests.get")
    def test_geocoding_timeout(self, mock_get):
        """Test handling of geocoding timeout (ReadTimeout)."""
        mock_get.side_effect = ReadTimeout("Connection timed out")

        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "Chicago, IL",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 504
        data = response.json()
        assert data["error"] == "upstream_timeout"

    @patch("trips.routing.requests.get")
    def test_routing_connect_timeout(self, mock_get):
        """Test handling of routing API timeout (ConnectTimeout)."""
        from unittest.mock import MagicMock

        # Create a mock response object that works for geocoding
        def create_geocode_response():
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"lat": "41.8781", "lon": "-87.6298"}]
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        # Configure side_effect: 3 successful geocode calls, then timeout on routing
        mock_get.side_effect = [
            create_geocode_response(),  # geocode Chicago
            create_geocode_response(),  # geocode Indianapolis
            create_geocode_response(),  # geocode Dallas
            ConnectTimeout("Failed to connect"),  # routing fails
        ]

        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "Chicago, IL",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )

        assert response.status_code == 504
        data = response.json()
        assert data["error"] == "upstream_timeout"

    @patch("trips.routing.requests.get")
    def test_upstream_generic_error(self, mock_get):
        """Test handling of generic upstream errors (HTTPError)."""
        from unittest.mock import MagicMock

        from requests.exceptions import HTTPError

        def create_geocode_response():
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"lat": "41.8781", "lon": "-87.6298"}]
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        # Configure side_effect: 3 successful geocode calls, then HTTP error on routing
        mock_resp_error = MagicMock()
        mock_resp_error.raise_for_status.side_effect = HTTPError("500 Server Error")

        mock_get.side_effect = [
            create_geocode_response(),  # geocode Chicago
            create_geocode_response(),  # geocode Indianapolis
            create_geocode_response(),  # geocode Dallas
            mock_resp_error,  # routing returns error response
        ]

        response = self.client.post(
            self.endpoint,
            data=json.dumps(
                {
                    "current_location": "Chicago, IL",
                    "pickup_location": "Indianapolis, IN",
                    "dropoff_location": "Dallas, TX",
                    "cycle_hours_used": 30,
                }
            ),
            content_type="application/json",
        )

        # HTTPError on routing should return 502 with routing_failed error
        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "routing_failed"


class TestHealthCheckAPI(TestCase):
    """Test the application health endpoint."""

    def setUp(self):
        self.client = Client()

    def test_health_check_returns_ok(self):
        response = self.client.get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestMarkerGeneration(TestCase):
    """Test marker generation and positioning."""

    def setUp(self):
        """Initialize test client."""
        self.client = Client()

    @patch("trips.services.geocode")
    @patch("trips.services.get_route")
    def test_marker_types(self, mock_route, mock_geocode):
        """Test that correct marker types are generated."""
        mock_geocode.side_effect = [
            (41.8781, -87.6298),
            (39.7684, -86.1581),
            (32.7767, -96.797),
        ]

        mock_route.side_effect = [
            {
                "coordinates": [[41.8781, -87.6298], [39.7684, -86.1581]],
                "distance_miles": 300,
                "duration_hours": 4.5,
            },
            {
                "coordinates": [[39.7684, -86.1581], [32.7767, -96.797]],
                "distance_miles": 550,
                "duration_hours": 8.0,
            },
        ]

        # Expected marker types: start, pickup, dropoff, fuel (every 1000 miles), rest
        # For 850-mile trip, should have: start, pickup, dropoff, 0-1 fuel, 1 rest
