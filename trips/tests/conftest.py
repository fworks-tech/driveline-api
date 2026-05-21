"""Shared pytest fixtures for trips app tests."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_geocode_response():
    """Fixture: valid Nominatim geocoding response."""
    return MagicMock(
        json=MagicMock(
            return_value=[
                {"lat": "41.8781", "lon": "-87.6298", "display_name": "Chicago, IL"}
            ]
        )
    )


@pytest.fixture
def mock_osrm_response():
    """Fixture: valid OSRM routing response."""
    return MagicMock(
        json=MagicMock(
            return_value={
                "code": "Ok",
                "routes": [
                    {
                        "geometry": {
                            "coordinates": [
                                [-87.6298, 41.8781],
                                [-87.5, 41.8],
                                [-86.1581, 39.7684],
                            ]
                        },
                        "distance": 150000,  # meters
                        "duration": 5400,  # seconds
                    }
                ],
            }
        )
    )


@pytest.fixture
def mock_hos_result():
    """Fixture: valid HOS engine simulation result."""
    return {
        "logbook_days": [
            {
                "day": 1,
                "date_offset": 0,
                "total_driving_hours": 11.0,
                "total_on_duty_hours": 12.0,
                "events": [
                    {
                        "status": "DRIVING",
                        "start_hour": 0.0,
                        "end_hour": 11.0,
                        "label": "Driving",
                    },
                    {
                        "status": "ON_DUTY_ND",
                        "start_hour": 11.0,
                        "end_hour": 12.0,
                        "label": "On-duty",
                    },
                    {
                        "status": "OFF_DUTY",
                        "start_hour": 12.0,
                        "end_hour": 24.0,
                        "label": "Off-duty",
                    },
                ],
            }
        ],
        "total_trip_hours": 13.5,
        "total_driving_hours": 11.0,
        "num_fuel_stops": 1,
        "num_rest_stops": 1,
    }


@pytest.fixture
def valid_trip_request():
    """Fixture: valid trip planning request payload."""
    return {
        "current_location": "Chicago, IL",
        "pickup_location": "Indianapolis, IN",
        "dropoff_location": "Dallas, TX",
        "cycle_hours_used": 30.0,
    }


@pytest.fixture
def geocode_coordinates():
    """Fixture: common test coordinates for geocoded locations."""
    return {
        "chicago": (41.8781, -87.6298),
        "indianapolis": (39.7684, -86.1581),
        "dallas": (32.7767, -96.797),
    }
