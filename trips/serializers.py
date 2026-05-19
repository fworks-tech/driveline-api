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
    start_hour = serializers.FloatField()
    end_hour = serializers.FloatField()
    label = serializers.CharField(max_length=255)


class LogbookDaySerializer(serializers.Serializer):
    date_offset = serializers.IntegerField()
    events = LogbookEventSerializer(many=True)


class TripSummarySerializer(serializers.Serializer):
    total_miles = serializers.FloatField()
    total_trip_hours = serializers.FloatField()
    total_driving_hours = serializers.FloatField()
    num_days = serializers.IntegerField()
    num_fuel_stops = serializers.IntegerField()
    num_rest_stops = serializers.IntegerField()
    leg1_miles = serializers.FloatField()
    leg2_miles = serializers.FloatField()


class TripOutputSerializer(serializers.Serializer):
    route_coordinates = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    markers = MarkerSerializer(many=True)
    logbook_days = LogbookDaySerializer(many=True)
    trip_summary = TripSummarySerializer()
