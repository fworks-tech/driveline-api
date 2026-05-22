from drf_spectacular.utils import extend_schema
from requests.exceptions import RequestException, Timeout
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .error_handler import CircuitOpenError, GeocodingError, RoutingError
from .hos_engine import simulate_trip
from .models import Trip
from .routing import geocode, get_route
from .serializers import (
    HealthCheckSerializer,
    TripCreateSerializer,
    TripInputSerializer,
    TripListSerializer,
    TripOutputSerializer,
    TripSerializer,
)
from .throttles import AuthThrottle, PlanRouteThrottle


class HealthCheckView(APIView):
    """Simple liveness endpoint for container and deployment health checks."""

    authentication_classes = []
    permission_classes = []
    serializer_class = HealthCheckSerializer

    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class PlanRouteView(APIView):
    """
    POST /api/plan-route/

    Accepts trip details, geocodes locations, fetches route from OSRM,
    runs HOS simulation, and returns full trip data.

    Authentication is optional - allows both authenticated and public requests.
    """

    serializer_class = TripInputSerializer
    permission_classes = [AllowAny]
    throttle_classes = [PlanRouteThrottle]

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
                from_location=data["current_location"],
                to_location=data["dropoff_location"],
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
                            "location": ev.get("location", ""),
                        }
                    )
                logbook_days_transformed.append(
                    {
                        "day": day["day"],
                        "date_offset": day["date_offset"],
                        "date": day["date"],
                        "from_location": day["from_location"],
                        "to_location": day["to_location"],
                        "daily_miles": day["daily_miles"],
                        "cumulative_miles": day["cumulative_miles"],
                        "total_driving_hours": day["total_driving_hours"],
                        "total_on_duty_hours": day["total_on_duty_hours"],
                        "row_totals": day["row_totals"],
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

        except CircuitOpenError as exc:
            return Response(
                {
                    "error": "service_unavailable",
                    "detail": exc.detail,
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except GeocodingError as exc:
            return Response(
                {
                    "error": "geocoding_failed",
                    "detail": exc.detail,
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except RoutingError as exc:
            return Response(
                {
                    "error": "routing_failed",
                    "detail": exc.detail,
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError:
            return Response(
                {
                    "error": "invalid_input",
                    "detail": "Request validation failed. Please check your input.",
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Timeout:
            return Response(
                {
                    "error": "upstream_timeout",
                    "detail": "External API request timed out. Please try again later.",
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except RequestException:
            return Response(
                {
                    "error": "upstream_error",
                    "detail": "External service error. Please try again later.",
                    "request_id": getattr(request, "request_id", None),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            return Response(
                {
                    "error": "internal_error",
                    "detail": "An unexpected error occurred. Please try again later.",
                    "request_id": getattr(request, "request_id", None),
                },
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
        marker_type = ev.get("marker_type")
        if not marker_type:
            continue
        fraction = ev["abs_start"] / total_trip_hours
        fraction = max(0.0, min(1.0, fraction))
        idx = int(fraction * (n - 1))
        lon, lat = coordinates[idx]
        markers.append(
            {
                "lat": lat,
                "lon": lon,
                "type": marker_type,
                "label": ev["label"],
            }
        )

    return markers


class TokenObtainView(APIView):
    """
    POST /api/auth/token/

    Obtain JWT tokens using username and password.
    Stateless JWT auth: no session cookies, CSRF protection not applicable.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(
        description="Obtain JWT access and refresh tokens",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                },
                "required": ["username", "password"],
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access": {"type": "string", "description": "JWT access token"},
                    "refresh": {"type": "string", "description": "JWT refresh token"},
                },
            },
        },
    )
    def post(self, request):
        from .serializers import CustomTokenObtainPairSerializer

        serializer = CustomTokenObtainPairSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class UserRegistrationView(APIView):
    """
    POST /api/auth/register/

    Register a new user account.
    Stateless JWT auth: no session cookies, CSRF protection not applicable.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(
        description="Register a new user account",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string", "minLength": 8},
                },
                "required": ["username", "email", "password"],
            }
        },
        responses={
            201: {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "username": {"type": "string"},
                    "email": {"type": "string"},
                },
            },
        },
    )
    def post(self, request):
        from .serializers import UserRegistrationSerializer

        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


class TripViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CRUD operations on user trips.

    Endpoints:
    - GET /api/trips/ - List user's trips (paginated)
    - POST /api/trips/ - Create new trip
    - GET /api/trips/{id}/ - Retrieve trip
    - PUT /api/trips/{id}/ - Update trip
    - DELETE /api/trips/{id}/ - Delete trip
    """

    permission_classes = [IsAuthenticated]
    queryset = Trip.objects.all()
    serializer_class = TripSerializer

    def get_queryset(self):
        """Return only trips owned by the current user."""
        return Trip.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == "create":
            return TripCreateSerializer
        elif self.action == "list":
            return TripListSerializer
        return TripSerializer

    def create(self, request, *args, **kwargs):
        """Create a new trip from form input and return full trip data."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()

        # Return full trip data in response
        output_serializer = TripSerializer(trip, context={"request": request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        """Soft-delete by archiving trip (can be changed to hard delete)."""
        instance.status = "archived"
        instance.save()
