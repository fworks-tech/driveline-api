from django.contrib.auth.models import User
from django.db import models


class Trip(models.Model):
    """User trip plan with calculated route and logbook data."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="trips")

    # Trip inputs
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    cycle_hours_used = models.FloatField(
        default=0, help_text="Hours already used in current 70-hour cycle"
    )

    # ELD log header metadata (FMCSA standard fields)
    trip_date = models.DateField(null=True, blank=True)
    tractor_number = models.CharField(max_length=50, blank=True, default="")
    trailer_number = models.CharField(max_length=50, blank=True, default="")
    shipper_name = models.CharField(max_length=255, blank=True, default="")

    # Trip outputs (JSON)
    route_coordinates = models.JSONField(default=list)
    markers = models.JSONField(default=list)
    logbook_days = models.JSONField(default=list)
    trip_summary = models.JSONField(default=dict)

    # Status & metadata
    status = models.CharField(
        max_length=20,
        choices=[
            ("draft", "Draft"),
            ("completed", "Completed"),
            ("archived", "Archived"),
        ],
        default="draft",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Trip {self.id}: {self.current_location} → {self.dropoff_location}"
