from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .hos_engine import simulate_trip
from .routing import geocode, get_route
from .serializers import TripInputSerializer, TripOutputSerializer


class HealthCheckView(APIView):
    """Simple liveness endpoint for container and deployment health checks."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class PlanRouteView(APIView):
    """
    POST /api/plan-route/

    Accepts trip details, geocodes locations, fetches route from OSRM,
    runs HOS simulation, and returns full trip data.
    """

    serializer_class = TripInputSerializer

    @extend_schema(
        request=TripInputSerializer,
        responses={200: TripOutputSerializer},
    )
    def post(self, request):
        serializer = TripInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            # 1. Geocode all three locations
            current_ll = geocode(data["current_location"])
            pickup_ll = geocode(data["pickup_location"])
            dropoff_ll = geocode(data["dropoff_location"])

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
                current_cycle_used_hours=data["cycle_hours_used"],
                leg1_miles=leg1["distance_miles"],
                leg2_miles=leg2["distance_miles"],
            )

            # 4. Build map markers
            markers = [
                {
                    "lat": current_ll[0],
                    "lon": current_ll[1],
                    "type": "start",
                    "label": data["current_location"],
                },
                {
                    "lat": pickup_ll[0],
                    "lon": pickup_ll[1],
                    "type": "pickup",
                    "label": data["pickup_location"],
                },
                {
                    "lat": dropoff_ll[0],
                    "lon": dropoff_ll[1],
                    "type": "dropoff",
                    "label": data["dropoff_location"],
                },
            ]

            # 5. Derive rest/fuel stop map markers from logbook events
            #    (approximate positions along route — spaced by event timing)
            stop_markers = _build_stop_markers(
                route["coordinates"],
                logbook["logbook_days"],
                logbook["total_trip_hours"],
            )
            markers.extend(stop_markers)

            # 6. Transform logbook to match spec: convert to ISO time format
            logbook_days_transformed = []
            for day_idx, day in enumerate(logbook["logbook_days"]):
                events_transformed = []
                for ev in day["events"]:
                    # Convert hours since start to HH:MM format
                    start_hours = int(ev["start_hour"])
                    start_mins = int((ev["start_hour"] - start_hours) * 60)
                    end_hours = int(ev["end_hour"])
                    end_mins = int((ev["end_hour"] - end_hours) * 60)
                    events_transformed.append(
                        {
                            "status": ev["status"],
                            "start_time": f"{start_hours:02d}:{start_mins:02d}",
                            "end_time": f"{end_hours:02d}:{end_mins:02d}",
                            "duration_hours": round(
                                ev["end_hour"] - ev["start_hour"], 2
                            ),
                            "label": ev["label"],
                        }
                    )
                logbook_days_transformed.append(
                    {
                        "day": day_idx + 1,
                        "events": events_transformed,
                    }
                )

            return Response(
                {
                    "route_coordinates": route["coordinates"],
                    "markers": markers,
                    "logbook_days": logbook_days_transformed,
                    "trip_summary": {
                        "total_distance_miles": round(total_miles, 1),
                        "total_trip_hours": round(logbook["total_trip_hours"], 1),
                        "total_drive_hours": round(logbook["total_driving_hours"], 1),
                        "legs": 2,  # Two legs: current->pickup, pickup->dropoff
                        "rest_stops": logbook["num_rest_stops"],
                        "fuel_stops": logbook["num_fuel_stops"],
                    },
                }
            )

        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": f"Route planning failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def _build_stop_markers(
    coordinates: list,
    logbook_days: list,
    total_trip_hours: float,
) -> list:
    """
    Build approximate lat/lon markers for fuel stops and rest stops by
    interpolating along the route polyline based on each event's timing.
    """
    if total_trip_hours <= 0 or not coordinates:
        return []

    # Flatten all events with absolute hours
    all_events = []
    for day in logbook_days:
        day_offset_hours = day["date_offset"] * 24.0
        for ev in day["events"]:
            all_events.append(
                {
                    "status": ev["status"],
                    "label": ev["label"],
                    "abs_start": ev["start_hour"] + day_offset_hours,
                    "abs_end": ev["end_hour"] + day_offset_hours,
                }
            )

    markers = []
    n = len(coordinates)

    for ev in all_events:
        if ev["label"] not in ("Fuel Stop", "Rest (10-hr Reset)"):
            continue
        fraction = ev["abs_start"] / total_trip_hours
        fraction = max(0.0, min(1.0, fraction))
        idx = int(fraction * (n - 1))
        lon, lat = coordinates[idx]
        marker_type = "fuel" if ev["label"] == "Fuel Stop" else "rest"
        markers.append(
            {
                "lat": lat,
                "lon": lon,
                "type": marker_type,
                "label": ev["label"],
            }
        )

    return markers
