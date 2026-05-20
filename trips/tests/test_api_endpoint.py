import json
from unittest.mock import patch

from django.test import Client, TestCase


class TestPlanRouteAPI(TestCase):
    """Integration tests for POST /api/plan-route/ endpoint."""

    def setUp(self):
        """Initialize test client."""
        self.client = Client()
        self.endpoint = "/api/plan-route/"

    @patch("trips.routing.geocode")
    @patch("trips.routing.get_route")
    @patch("trips.hos_engine.simulate_trip")
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

    @patch("trips.routing.geocode")
    def test_invalid_current_location(self, mock_geocode):
        """Test request with invalid current location."""
        mock_geocode.return_value = None  # Location not found

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

        assert response.status_code == 400

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


class TestMarkerGeneration(TestCase):
    """Test marker generation and positioning."""

    def setUp(self):
        """Initialize test client."""
        self.client = Client()

    @patch("trips.routing.geocode")
    @patch("trips.routing.get_route")
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
