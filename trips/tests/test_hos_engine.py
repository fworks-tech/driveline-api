import pytest
from django.core.cache import cache

from trips.hos_engine import _make_hos_cache_key, _snap_to_15min, simulate_trip

VALID_STATUSES = {"OFF_DUTY", "SLEEPER_BERTH", "DRIVING", "ON_DUTY_NOT_DRIVING"}


def make_trip(
    total_miles, leg1_miles=None, leg1_hours=None, leg2_hours=None, cycle_hours=0
):
    """Helper: build a simulate_trip call with sensible defaults."""
    if leg1_miles is None:
        leg1_miles = total_miles * 0.4
    leg2_miles = total_miles - leg1_miles
    avg_speed = 55.0
    if leg1_hours is None:
        leg1_hours = leg1_miles / avg_speed
    if leg2_hours is None:
        leg2_hours = leg2_miles / avg_speed
    return simulate_trip(
        total_distance_miles=total_miles,
        leg1_hours=leg1_hours,
        leg2_hours=leg2_hours,
        current_cycle_used_hours=cycle_hours,
        leg1_miles=leg1_miles,
        leg2_miles=leg2_miles,
    )


@pytest.mark.unit
class TestHOSEngineRules:
    """Unit tests for FMCSA Hours of Service simulate_trip() engine."""

    def test_rule_1_pickup_and_dropoff_on_duty_events(self):
        """Rule 1: 1-hour ON_DUTY_NOT_DRIVING events are inserted at pickup and dropoff."""
        result = make_trip(300)
        all_events = [e for day in result["logbook_days"] for e in day["events"]]
        pickup = [e for e in all_events if e.get("label") == "Pickup"]
        dropoff = [e for e in all_events if e.get("label") == "Dropoff"]
        assert len(pickup) == 1
        assert len(dropoff) == 1
        assert pickup[0]["status"] == "ON_DUTY_NOT_DRIVING"
        assert dropoff[0]["status"] == "ON_DUTY_NOT_DRIVING"
        assert pickup[0]["duration_hours"] == pytest.approx(1.0)
        assert dropoff[0]["duration_hours"] == pytest.approx(1.0)

    def test_rule_2_fuel_stop_every_1000_miles(self):
        """Rule 2: At least one fuel stop is inserted for a 1500-mile trip."""
        result = make_trip(1500)
        assert result["num_fuel_stops"] >= 1

    def test_rule_2_no_fuel_stop_under_1000_miles(self):
        """Rule 2: No fuel stop is inserted for a sub-1000-mile trip."""
        result = make_trip(800)
        assert result["num_fuel_stops"] == 0

    def test_rule_3_driving_does_not_exceed_11_hours_per_shift(self):
        """Rule 3: No single logbook day has more than 11 hours of driving."""
        result = make_trip(600)
        for day in result["logbook_days"]:
            day_drive = sum(
                e["duration_hours"] for e in day["events"] if e["status"] == "DRIVING"
            )
            assert day_drive <= 11.0 + 0.001

    def test_rule_4_30_minute_break_after_8_hours(self):
        """Rule 4: A 30-min OFF_DUTY break appears when driving exceeds 8 hours."""
        # 600 miles at 55 mph ≈ 10.9 hours driving — will trigger the break
        result = make_trip(600)
        all_events = [e for day in result["logbook_days"] for e in day["events"]]
        breaks = [
            e
            for e in all_events
            if e["status"] == "OFF_DUTY" and e.get("label") == "30-min Break"
        ]
        assert len(breaks) >= 1
        assert breaks[0]["duration_hours"] == pytest.approx(0.5)

    def test_rule_5_rest_stop_on_multi_day_trip(self):
        """Rule 5: A 10-hour SLEEPER_BERTH reset is inserted on a multi-day trip."""
        result = make_trip(1000)
        all_events = [e for day in result["logbook_days"] for e in day["events"]]
        rests = [e for e in all_events if e["status"] == "SLEEPER_BERTH"]
        assert len(rests) >= 1
        assert rests[0]["duration_hours"] == pytest.approx(10.0)

    def test_rule_6_70_hour_cycle_limits_driving(self):
        """Rule 6: High cycle hours used leaves little remaining driving capacity."""
        # 65 hours already used → only 5 hours available before rest needed
        result = make_trip(500, cycle_hours=65)
        all_events = [e for day in result["logbook_days"] for e in day["events"]]
        # All driving before first rest must be ≤ 5 hours
        driving_before_rest = 0.0
        for e in all_events:
            if e["status"] == "SLEEPER_BERTH":
                break
            if e["status"] == "DRIVING":
                driving_before_rest += e["duration_hours"]
        assert driving_before_rest <= 5.0 + 0.001

    def test_all_event_statuses_are_valid(self):
        """All events use recognised FMCSA status strings."""
        result = make_trip(850)
        for day in result["logbook_days"]:
            for event in day["events"]:
                assert event["status"] in VALID_STATUSES

    def test_logbook_days_cover_full_24_hours(self):
        """Each logbook day sums to exactly 24 hours (gaps filled with OFF_DUTY)."""
        result = make_trip(850)
        for day in result["logbook_days"]:
            total = sum(e["duration_hours"] for e in day["events"])
            assert total == pytest.approx(24.0, abs=0.01)

    def test_return_structure(self):
        """simulate_trip returns the expected top-level keys."""
        result = make_trip(300)
        assert "logbook_days" in result
        assert "total_trip_hours" in result
        assert "total_driving_hours" in result
        assert "num_fuel_stops" in result
        assert "num_rest_stops" in result

    def test_chicago_to_dallas_scenario(self):
        """Integration: Chicago → Dallas (~850 miles) produces a valid logbook."""
        result = make_trip(
            850, leg1_miles=297, leg1_hours=4.5, leg2_hours=8.0, cycle_hours=30
        )
        assert result["total_driving_hours"] > 0
        assert len(result["logbook_days"]) >= 1
        # Driving limit per shift is tested in test_rule_3; here we just verify
        # the scenario completes and accumulates the expected total driving hours.
        assert result["total_driving_hours"] <= 12.5 + 0.1

    def test_la_to_denver_scenario(self):
        """Integration: LA → Denver (~1000 miles) spans 2+ logbook days."""
        result = make_trip(1000, cycle_hours=0)
        assert len(result["logbook_days"]) >= 2

    def test_ny_to_miami_scenario(self):
        """Integration: NY → Miami (~1200 miles) with high cycle hours still works."""
        result = make_trip(1200, cycle_hours=50)
        assert result is not None
        assert len(result["logbook_days"]) >= 2

    def test_events_are_chronologically_ordered(self):
        """Events within each day are sorted by start_hour."""
        result = make_trip(850)
        for day in result["logbook_days"]:
            starts = [e["start_hour"] for e in day["events"]]
            assert starts == sorted(starts)

    def test_from_and_to_location_in_logbook_days(self):
        """from_location and to_location are propagated to each logbook day."""
        result = simulate_trip(
            total_distance_miles=300,
            leg1_hours=2.0,
            leg2_hours=3.0,
            current_cycle_used_hours=0,
            leg1_miles=120,
            leg2_miles=180,
            from_location="Origin City",
            to_location="Dest City",
        )
        for day in result["logbook_days"]:
            assert day["from_location"] == "Origin City"
            assert day["to_location"] == "Dest City"

    def test_num_rest_stops_in_return_structure(self):
        """num_rest_stops is present and non-negative."""
        result = make_trip(300)
        assert "num_rest_stops" in result
        assert result["num_rest_stops"] >= 0

    def test_multi_day_trip_has_rest_stops(self):
        """A long trip requiring rests increments num_rest_stops."""
        result = make_trip(1200)
        assert result["num_rest_stops"] >= 1

    def test_total_trip_hours_exceeds_driving_hours(self):
        """total_trip_hours includes non-driving time so it exceeds driving hours."""
        result = make_trip(500)
        assert result["total_trip_hours"] > result["total_driving_hours"]


@pytest.mark.unit
class TestHOSHelpers:
    """Unit tests for hos_engine helper functions."""

    def test_snap_to_15min_rounds_down(self):
        assert _snap_to_15min(1.1) == pytest.approx(1.0)

    def test_snap_to_15min_rounds_to_quarter(self):
        assert _snap_to_15min(1.3) == pytest.approx(1.25)

    def test_snap_to_15min_exact_quarter_unchanged(self):
        assert _snap_to_15min(2.25) == pytest.approx(2.25)

    def test_snap_to_15min_zero(self):
        assert _snap_to_15min(0.0) == pytest.approx(0.0)

    def test_cache_key_is_deterministic(self):
        """Same inputs produce the same cache key."""
        key1 = _make_hos_cache_key(500, 4.0, 5.0, 10.0, 200, 300)
        key2 = _make_hos_cache_key(500, 4.0, 5.0, 10.0, 200, 300)
        assert key1 == key2

    def test_cache_key_differs_on_different_inputs(self):
        """Different inputs produce different cache keys."""
        key1 = _make_hos_cache_key(500, 4.0, 5.0, 10.0, 200, 300)
        key2 = _make_hos_cache_key(600, 4.0, 5.0, 10.0, 200, 400)
        assert key1 != key2

    def test_simulate_trip_uses_cache(self):
        """Calling simulate_trip twice with same args returns cached result."""
        cache.clear()
        result1 = make_trip(300)
        result2 = make_trip(300)
        assert result1 == result2
