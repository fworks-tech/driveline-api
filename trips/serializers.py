from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Trip


class TripInputSerializer(serializers.Serializer):
    current_location = serializers.CharField(min_length=2, max_length=500)
    pickup_location = serializers.CharField(min_length=2, max_length=500)
    dropoff_location = serializers.CharField(min_length=2, max_length=500)
    cycle_hours_used = serializers.FloatField(min_value=0, max_value=70)
    trip_date = serializers.DateField(required=False, allow_null=True)
    tractor_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    trailer_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    shipper_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )


class MarkerSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    type = serializers.CharField(max_length=50)
    label = serializers.CharField(max_length=255)


class LogbookEventSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=50)
    start_time = serializers.CharField(max_length=5)
    end_time = serializers.CharField(max_length=5)
    duration_hours = serializers.FloatField()
    label = serializers.CharField(max_length=255)
    location = serializers.CharField(max_length=255, required=False, allow_blank=True)


class LogbookDaySerializer(serializers.Serializer):
    day = serializers.IntegerField()
    date_offset = serializers.IntegerField()
    date = serializers.CharField(max_length=10)
    from_location = serializers.CharField(max_length=255)
    to_location = serializers.CharField(max_length=255)
    daily_miles = serializers.FloatField()
    cumulative_miles = serializers.FloatField()
    total_driving_hours = serializers.FloatField()
    total_on_duty_hours = serializers.FloatField()
    row_totals = serializers.DictField()
    events = LogbookEventSerializer(many=True)


class TripSummarySerializer(serializers.Serializer):
    total_distance_miles = serializers.FloatField()
    total_trip_hours = serializers.FloatField()
    total_drive_hours = serializers.FloatField()
    legs = serializers.IntegerField()
    rest_stops = serializers.IntegerField()
    fuel_stops = serializers.IntegerField()


class TripOutputSerializer(serializers.Serializer):
    route_coordinates = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField())
    )
    markers = MarkerSerializer(many=True)
    logbook_days = LogbookDaySerializer(many=True)
    trip_summary = TripSummarySerializer()


class HealthCheckSerializer(serializers.Serializer):
    status = serializers.CharField()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["username"] = user.username
        return token


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class TripSerializer(serializers.ModelSerializer):
    """Serializer for Trip model with full trip data."""

    class Meta:
        model = Trip
        fields = [
            "id",
            "user",
            "current_location",
            "pickup_location",
            "dropoff_location",
            "cycle_hours_used",
            "trip_date",
            "tractor_number",
            "trailer_number",
            "shipper_name",
            "route_coordinates",
            "markers",
            "logbook_days",
            "trip_summary",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def create(self, validated_data):
        """Create a new trip associated with the current user."""
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class TripListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for trip list endpoints."""

    class Meta:
        model = Trip
        fields = [
            "id",
            "current_location",
            "pickup_location",
            "dropoff_location",
            "cycle_hours_used",
            "trip_date",
            "tractor_number",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TripCreateSerializer(serializers.Serializer):
    """Serializer for creating a new trip from form input."""

    current_location = serializers.CharField(min_length=2, max_length=500)
    pickup_location = serializers.CharField(min_length=2, max_length=500)
    dropoff_location = serializers.CharField(min_length=2, max_length=500)
    cycle_hours_used = serializers.FloatField(min_value=0, max_value=70)
    trip_date = serializers.DateField(required=False, allow_null=True)
    tractor_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    trailer_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    shipper_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def create(self, validated_data):
        """Create and save a new trip with calculated route data."""
        from datetime import date as date_type

        from .hos_engine import simulate_trip
        from .routing import geocode, get_route
        from .views import _build_stop_markers

        data = validated_data
        try:
            # Geocode locations
            current_ll = geocode(data["current_location"])
            pickup_ll = geocode(data["pickup_location"])
            dropoff_ll = geocode(data["dropoff_location"])

            # Fetch route
            route = get_route(current_ll, pickup_ll, dropoff_ll)
            leg1 = route["legs"][0]
            leg2 = route["legs"][1]
            total_miles = leg1["distance_miles"] + leg2["distance_miles"]

            # Use provided trip_date or default to today
            trip_date = data.get("trip_date") or date_type.today()

            # Run HOS simulation
            logbook = simulate_trip(
                total_distance_miles=total_miles,
                leg1_hours=leg1["duration_hours"],
                leg2_hours=leg2["duration_hours"],
                current_cycle_used_hours=data["cycle_hours_used"],
                leg1_miles=leg1["distance_miles"],
                leg2_miles=leg2["distance_miles"],
                start_date=trip_date,
                from_location=data["current_location"],
                to_location=data["dropoff_location"],
            )

            # Build markers
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
            stop_markers = _build_stop_markers(
                route["coordinates"],
                logbook["logbook_days"],
                logbook["total_trip_hours"],
            )
            markers.extend(stop_markers)

            # Transform logbook
            logbook_days_transformed = []
            for day in logbook["logbook_days"]:
                events_transformed = []
                for ev in day["events"]:
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

            # Create Trip instance
            trip = Trip(
                user=self.context["request"].user,
                current_location=data["current_location"],
                pickup_location=data["pickup_location"],
                dropoff_location=data["dropoff_location"],
                cycle_hours_used=data["cycle_hours_used"],
                trip_date=trip_date,
                tractor_number=data.get("tractor_number", ""),
                trailer_number=data.get("trailer_number", ""),
                shipper_name=data.get("shipper_name", ""),
                route_coordinates=route["coordinates"],
                markers=markers,
                logbook_days=logbook_days_transformed,
                trip_summary={
                    "total_distance_miles": round(total_miles, 1),
                    "total_trip_hours": round(logbook["total_trip_hours"], 1),
                    "total_drive_hours": round(logbook["total_driving_hours"], 1),
                    "legs": 2,
                    "rest_stops": logbook["num_rest_stops"],
                    "fuel_stops": logbook["num_fuel_stops"],
                },
                status="completed",
            )
            trip.save()
            return trip

        except Exception as exc:
            raise serializers.ValidationError(
                f"Trip creation failed: {str(exc)}"
            ) from exc
