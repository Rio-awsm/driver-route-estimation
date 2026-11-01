from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

MAX_DAYS_AHEAD = 7


class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=200)
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)


class PlanRequestSerializer(serializers.Serializer):
    origin = PlaceSerializer()
    destination = PlaceSerializer()
    departure = serializers.DateTimeField()
    load_lb = serializers.IntegerField(min_value=0, max_value=120_000)
    interval_miles = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate_departure(self, value):
        now = timezone.now()
        if value < now - timedelta(hours=1):
            raise serializers.ValidationError("Departure cannot be in the past.")
        if value > now + timedelta(days=MAX_DAYS_AHEAD):
            raise serializers.ValidationError(
                f"Departure must be within {MAX_DAYS_AHEAD} days; forecasts degrade after that."
            )
        return value

    def validate(self, attrs):
        origin, destination = attrs["origin"], attrs["destination"]
        if (origin["lat"], origin["lon"]) == (destination["lat"], destination["lon"]):
            raise serializers.ValidationError("Origin and destination must be different.")
        return attrs
