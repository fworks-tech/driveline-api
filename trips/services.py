"""Service layer for trip planning operations."""

from trips.hos_engine import simulate_trip
from trips.routing import geocode, get_route


class TripPlanningService:
    """Orchestrates trip planning: geocoding, routing, and HOS simulation."""

    @staticmethod
    def plan_route(
        current_location: str,
        pickup_location: str,
        dropoff_location: str,
        cycle_hours_used: float,
        start_date=None,
    ) -> dict:
        """Plan a complete trip from input locations and hours.

        Args:
            current_location: Starting location string (e.g., "Chicago, IL")
            pickup_location: Pickup location string
            dropoff_location: Final destination string
            cycle_hours_used: Hours already used in 70-hour cycle (0-70)
            start_date: Optional trip start date; defaults to today

        Returns:
            dict with route, logbook_days, and trip_summary
        """
        # 1. Geocode all three locations
        current_ll = geocode(current_location)
        pickup_ll = geocode(pickup_location)
        dropoff_ll = geocode(dropoff_location)

        # 2. Fetch route from OSRM
        route = get_route(current_ll, pickup_ll, dropoff_ll)

        leg1 = route["legs"][0]
        leg2 = route["legs"][1]
        total_miles = leg1["distance_miles"] + leg2["distance_miles"]

        # 3. Run HOS simulation
        logbook = simulate_trip(
            total_distance_miles=total_miles,
            leg1_hours=leg1["duration_hours"],
            leg2_hours=leg2["duration_hours"],
            current_cycle_used_hours=cycle_hours_used,
            leg1_miles=leg1["distance_miles"],
            leg2_miles=leg2["distance_miles"],
            start_date=start_date,
            from_location=current_location,
            pickup_location=pickup_location,
            to_location=dropoff_location,
        )

        return {
            "route_coordinates": route["coordinates"],
            "leg1": leg1,
            "leg2": leg2,
            "total_miles": total_miles,
            "logbook": logbook,
            "locations": {
                "current": {"ll": current_ll, "name": current_location},
                "pickup": {"ll": pickup_ll, "name": pickup_location},
                "dropoff": {"ll": dropoff_ll, "name": dropoff_location},
            },
        }
