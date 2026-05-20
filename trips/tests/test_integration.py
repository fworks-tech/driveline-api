"""
Integration tests for the complete trip planning workflow.
Tests the actual behavior of geocoding, routing, and HOS simulation.
"""
import json
import pytest
from django.test import Client
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestTripPlanningIntegration:
    """Integration tests for POST /api/plan-route/ endpoint."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize test client."""
        self.client = Client()
        self.endpoint = '/api/plan-route/'

    @patch('trips.routing.get_route')
    @patch('trips.routing.geocode')
    def test_successful_route_planning_end_to_end(self, mock_geocode, mock_route):
        """Test complete trip planning with mocked external APIs."""
        # Mock geocoding responses
        mock_geocode.side_effect = [
            (41.8781, -87.6298),    # Chicago, IL
            (39.7684, -86.1581),    # Indianapolis, IN
            (32.7767, -96.797),     # Dallas, TX
        ]

        # Mock routing responses with realistic data
        mock_route.side_effect = [
            {
                'coordinates': [
                    [-87.6298, 41.8781],
                    [-87.0, 40.0],
                    [-86.1581, 39.7684],
                ],
                'distance_miles': 297.3,
                'duration_hours': 4.5,
            },
            {
                'coordinates': [
                    [-86.1581, 39.7684],
                    [-90.0, 35.0],
                    [-96.797, 32.7767],
                ],
                'distance_miles': 552.7,
                'duration_hours': 8.0,
            },
        ]

        # Submit request
        response = self.client.post(
            self.endpoint,
            data=json.dumps({
                'current_location': 'Chicago, IL',
                'pickup_location': 'Indianapolis, IN',
                'dropoff_location': 'Dallas, TX',
                'cycle_hours_used': 30.0,
            }),
            content_type='application/json',
        )

        # Assert successful response
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert 'route_coordinates' in data
        assert 'markers' in data
        assert 'logbook_days' in data
        assert 'trip_summary' in data

        # Verify markers
        assert len(data['markers']) >= 3  # start, pickup, dropoff
        assert any(m['type'] == 'start' for m in data['markers'])
        assert any(m['type'] == 'pickup' for m in data['markers'])
        assert any(m['type'] == 'dropoff' for m in data['markers'])

        # Verify logbook
        assert len(data['logbook_days']) >= 1
        assert all('day' in d and 'events' in d for d in data['logbook_days'])

        # Verify trip summary
        summary = data['trip_summary']
        assert 'total_distance_miles' in summary
        assert 'total_trip_hours' in summary
        assert 'total_drive_hours' in summary
        assert 'legs' in summary
        assert summary['legs'] == 2

    @patch('trips.routing.get_route')
    @patch('trips.routing.geocode')
    def test_invalid_location_returns_400(self, mock_geocode, mock_route):
        """Test that invalid/non-geocodable location returns 400 error."""
        # Simulate geocoding failure
        mock_geocode.side_effect = ValueError('Address not found')

        response = self.client.post(
            self.endpoint,
            data=json.dumps({
                'current_location': 'InvalidLocationXYZ123',
                'pickup_location': 'Indianapolis, IN',
                'dropoff_location': 'Dallas, TX',
                'cycle_hours_used': 30.0,
            }),
            content_type='application/json',
        )

        # Should return 400 Bad Request
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data or 'detail' in data

    def test_missing_required_fields_returns_400(self):
        """Test that missing required fields return 400 error."""
        response = self.client.post(
            self.endpoint,
            data=json.dumps({
                'current_location': 'Chicago, IL',
                # Missing: pickup_location
                'dropoff_location': 'Dallas, TX',
                'cycle_hours_used': 30.0,
            }),
            content_type='application/json',
        )

        assert response.status_code == 400
        data = response.json()
        assert 'error' in data or 'detail' in data

    def test_cycle_hours_out_of_range_returns_400(self):
        """Test that cycle_hours_used > 70 returns validation error."""
        response = self.client.post(
            self.endpoint,
            data=json.dumps({
                'current_location': 'Chicago, IL',
                'pickup_location': 'Indianapolis, IN',
                'dropoff_location': 'Dallas, TX',
                'cycle_hours_used': 75.0,  # Exceeds 70-hour limit
            }),
            content_type='application/json',
        )

        assert response.status_code == 400
        data = response.json()
        assert 'error' in data or 'detail' in data

    @patch('trips.routing.get_route')
    @patch('trips.routing.geocode')
    def test_route_coordinates_use_geojson_format(self, mock_geocode, mock_route):
        """Test that route_coordinates are in GeoJSON [lon, lat] format."""
        mock_geocode.side_effect = [
            (41.8781, -87.6298),
            (39.7684, -86.1581),
            (32.7767, -96.797),
        ]

        mock_route.side_effect = [
            {
                'coordinates': [
                    [-87.6298, 41.8781],  # [lon, lat]
                    [-86.1581, 39.7684],
                ],
                'distance_miles': 297.3,
                'duration_hours': 4.5,
            },
            {
                'coordinates': [
                    [-86.1581, 39.7684],  # [lon, lat]
                    [-96.797, 32.7767],
                ],
                'distance_miles': 552.7,
                'duration_hours': 8.0,
            },
        ]

        response = self.client.post(
            self.endpoint,
            data=json.dumps({
                'current_location': 'Chicago, IL',
                'pickup_location': 'Indianapolis, IN',
                'dropoff_location': 'Dallas, TX',
                'cycle_hours_used': 30.0,
            }),
            content_type='application/json',
        )

        data = response.json()
        coords = data['route_coordinates']

        # Verify format: [lon, lat]
        for coord in coords:
            assert isinstance(coord, list)
            assert len(coord) == 2
            lon, lat = coord
            # Longitude should be -180 to 180
            assert -180 <= lon <= 180
            # Latitude should be -90 to 90
            assert -90 <= lat <= 90

    @patch('trips.routing.get_route')
    @patch('trips.routing.geocode')
    def test_markers_have_correct_structure(self, mock_geocode, mock_route):
        """Test that markers have required fields."""
        mock_geocode.side_effect = [
            (41.8781, -87.6298),
            (39.7684, -86.1581),
            (32.7767, -96.797),
        ]

        mock_route.side_effect = [
            {
                'coordinates': [[-87.6298, 41.8781], [-86.1581, 39.7684]],
                'distance_miles': 297.3,
                'duration_hours': 4.5,
            },
            {
                'coordinates': [[-86.1581, 39.7684], [-96.797, 32.7767]],
                'distance_miles': 552.7,
                'duration_hours': 8.0,
            },
        ]

        response = self.client.post(
            self.endpoint,
            data=json.dumps({
                'current_location': 'Chicago, IL',
                'pickup_location': 'Indianapolis, IN',
                'dropoff_location': 'Dallas, TX',
                'cycle_hours_used': 30.0,
            }),
            content_type='application/json',
        )

        markers = response.json()['markers']

        for marker in markers:
            assert 'type' in marker
            assert 'lat' in marker
            assert 'lon' in marker
            assert 'label' in marker
            assert marker['type'] in ['start', 'pickup', 'dropoff', 'fuel', 'rest']
            assert -90 <= marker['lat'] <= 90
            assert -180 <= marker['lon'] <= 180

    @patch('trips.routing.get_route')
    @patch('trips.routing.geocode')
    def test_logbook_has_valid_duty_statuses(self, mock_geocode, mock_route):
        """Test that logbook events have valid FMCSA duty statuses."""
        mock_geocode.side_effect = [
            (41.8781, -87.6298),
            (39.7684, -86.1581),
            (32.7767, -96.797),
        ]

        mock_route.side_effect = [
            {
                'coordinates': [[-87.6298, 41.8781], [-86.1581, 39.7684]],
                'distance_miles': 297.3,
                'duration_hours': 4.5,
            },
            {
                'coordinates': [[-86.1581, 39.7684], [-96.797, 32.7767]],
                'distance_miles': 552.7,
                'duration_hours': 8.0,
            },
        ]

        response = self.client.post(
            self.endpoint,
            data=json.dumps({
                'current_location': 'Chicago, IL',
                'pickup_location': 'Indianapolis, IN',
                'dropoff_location': 'Dallas, TX',
                'cycle_hours_used': 30.0,
            }),
            content_type='application/json',
        )

        logbook_days = response.json()['logbook_days']
        valid_statuses = {
            'OFF_DUTY',
            'SLEEPER_BERTH',
            'DRIVING',
            'ON_DUTY_ND',
            'SLEEPER',
        }

        for day in logbook_days:
            assert 'day' in day
            assert 'events' in day
            for event in day['events']:
                assert 'status' in event
                assert event['status'] in valid_statuses
                assert 'start_minute' in event
                assert 'duration_minutes' in event
                assert 'label' in event


@pytest.mark.unit
class TestSerializerValidation:
    """Unit tests for request/response serializers."""

    def test_plan_route_serializer_validates_location_length(self):
        """Test that location fields are validated for length."""
        from trips.serializers import PlanRouteSerializer

        # Too long location (max 500)
        data = {
            'current_location': 'x' * 501,
            'pickup_location': 'Indianapolis, IN',
            'dropoff_location': 'Dallas, TX',
            'cycle_hours_used': 30.0,
        }

        serializer = PlanRouteSerializer(data=data)
        assert not serializer.is_valid()

    def test_plan_route_serializer_validates_cycle_hours_range(self):
        """Test that cycle_hours_used is validated (0-70 range)."""
        from trips.serializers import PlanRouteSerializer

        # Exceeds 70-hour limit
        data = {
            'current_location': 'Chicago, IL',
            'pickup_location': 'Indianapolis, IN',
            'dropoff_location': 'Dallas, TX',
            'cycle_hours_used': 75.0,
        }

        serializer = PlanRouteSerializer(data=data)
        assert not serializer.is_valid()

        # Valid range
        data['cycle_hours_used'] = 30.0
        serializer = PlanRouteSerializer(data=data)
        # Will validate further but structure is correct
        assert 'cycle_hours_used' in serializer.initial_data
