from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class TripInputSerializer(serializers.Serializer):
    current_location = serializers.CharField(min_length=2, max_length=500)
    pickup_location = serializers.CharField(min_length=2, max_length=500)
    dropoff_location = serializers.CharField(min_length=2, max_length=500)
    cycle_hours_used = serializers.FloatField(min_value=0, max_value=70)


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
    total_driving_hours = serializers.FloatField()
    total_on_duty_hours = serializers.FloatField()
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
