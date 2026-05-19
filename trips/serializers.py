from rest_framework import serializers


class TripInputSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=500)
    pickup_location = serializers.CharField(max_length=500)
    dropoff_location = serializers.CharField(max_length=500)
    current_cycle_used = serializers.FloatField(min_value=0, max_value=70)


class MarkerSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    type = serializers.CharField(max_length=50)
    label = serializers.CharField(max_length=255)


class LogbookEventSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=50)
    start_minute = serializers.IntegerField()
    duration_minutes = serializers.IntegerField()
    label = serializers.CharField(max_length=255)


class LogbookDaySerializer(serializers.Serializer):
    day = serializers.IntegerField()
    events = LogbookEventSerializer(many=True)


class TripSummarySerializer(serializers.Serializer):
    total_distance_miles = serializers.FloatField()
    total_trip_hours = serializers.FloatField()
    total_drive_hours = serializers.FloatField()
    legs = serializers.IntegerField()
    rest_stops = serializers.IntegerField()
    fuel_stops = serializers.IntegerField()


class TripOutputSerializer(serializers.Serializer):
    route_coordinates = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    markers = MarkerSerializer(many=True)
    logbook_days = LogbookDaySerializer(many=True)
    trip_summary = TripSummarySerializer()
