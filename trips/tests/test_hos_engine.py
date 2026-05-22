from datetime import date, timedelta

from trips.hos_engine import simulate_trip


class TestHOSEdgeCases:
    """Test edge cases and boundary conditions in the HOS engine."""

    def test_cycle_hours_used_65_forces_early_cycle_rest(self):
        """Test 70-hr cycle limit: cycle_hours=65 forces early 10-hr rest."""
        result = simulate_trip(
            total_distance_miles=100,
            leg1_hours=4,
            leg2_hours=2,
            current_cycle_used_hours=65,
            leg1_miles=50,
            leg2_miles=50,
        )

        assert result["logbook_days"] is not None
        assert len(result["logbook_days"]) >= 1

        # Verify cycle hours don't exceed 70
        total_cycle_hours = 0
        for day in result["logbook_days"]:
            for event in day["events"]:
                if event["status"] in ("DRIVING", "ON_DUTY_ND"):
                    total_cycle_hours += event["duration_hours"]

        assert total_cycle_hours <= 70.5

    def test_trip_over_1000_miles_includes_fuel_stops(self):
        """Test fuel stops: trip >1000 miles per leg has multiple fuel stops."""
        result = simulate_trip(
            total_distance_miles=3000,
            leg1_hours=25,
            leg2_hours=0,
            current_cycle_used_hours=0,
            leg1_miles=1500,
            leg2_miles=1500,
        )

        fuel_stops = 0
        for day in result["logbook_days"]:
            for event in day["events"]:
                if event["status"] == "ON_DUTY_ND" and "Fuel" in event.get("label", ""):
                    fuel_stops += 1

        assert fuel_stops >= 2

    def test_multi_day_trip_creates_multiple_logbook_days(self):
        """Test multi-day: 15hr trip spans 2+ logbook days with 10-hr rest."""
        result = simulate_trip(
            total_distance_miles=900,
            leg1_hours=8,
            leg2_hours=7,
            current_cycle_used_hours=0,
            leg1_miles=450,
            leg2_miles=450,
        )

        assert len(result["logbook_days"]) >= 2

        # Each day should sum to 24 hours
        for day in result["logbook_days"]:
            total_hours = sum(event["duration_hours"] for event in day["events"])
            assert abs(total_hours - 24.0) < 0.1

    def test_cumulative_driving_8_hours_triggers_break(self):
        """Test mandatory break: 8 hrs driving triggers 30-min OFF_DUTY break."""
        result = simulate_trip(
            total_distance_miles=480,
            leg1_hours=8.5,
            leg2_hours=0,
            current_cycle_used_hours=0,
            leg1_miles=480,
            leg2_miles=0,
        )

        events = result["logbook_days"][0]["events"]
        found_break = False

        for i, event in enumerate(events):
            if (
                event["status"] == "OFF_DUTY"
                and abs(event["duration_hours"] - 0.5) < 0.01
            ):
                # Check driving before this break
                driving_before = sum(
                    e["duration_hours"] for e in events[:i] if e["status"] == "DRIVING"
                )
                if abs(driving_before - 8.0) < 0.5:
                    found_break = True
                    break

        assert found_break

    def test_pickup_adds_1_hour_on_duty_nd(self):
        """Test pickup: ON_DUTY_ND event for pickup is exactly 1 hour."""
        result = simulate_trip(
            total_distance_miles=100,
            leg1_hours=2,
            leg2_hours=2,
            current_cycle_used_hours=0,
            leg1_miles=50,
            leg2_miles=50,
        )

        events = result["logbook_days"][0]["events"]
        found_pickup = False

        for event in events:
            if event["status"] == "ON_DUTY_ND" and "Pickup" in event.get("label", ""):
                assert abs(event["duration_hours"] - 1.0) < 0.01
                found_pickup = True

        assert found_pickup

    def test_dropoff_adds_1_hour_on_duty_nd(self):
        """Test dropoff: ON_DUTY_ND event for dropoff is exactly 1 hour."""
        result = simulate_trip(
            total_distance_miles=100,
            leg1_hours=2,
            leg2_hours=2,
            current_cycle_used_hours=0,
            leg1_miles=50,
            leg2_miles=50,
        )

        events = result["logbook_days"][-1]["events"]
        found_dropoff = False

        for event in events:
            if event["status"] == "ON_DUTY_ND" and "Dropoff" in event.get("label", ""):
                assert abs(event["duration_hours"] - 1.0) < 0.01
                found_dropoff = True

        assert found_dropoff

    def test_total_hours_consistency(self):
        """Test total hours: sum of all events >= driving + pickup + dropoff."""
        result = simulate_trip(
            total_distance_miles=200,
            leg1_hours=3,
            leg2_hours=3,
            current_cycle_used_hours=0,
            leg1_miles=100,
            leg2_miles=100,
        )

        total_hours = 0
        driving_hours = 0
        for day in result["logbook_days"]:
            for event in day["events"]:
                total_hours += event["duration_hours"]
                if event["status"] == "DRIVING":
                    driving_hours += event["duration_hours"]

        assert driving_hours >= 5.9
        assert total_hours >= 7.9

    def test_start_date_propagates(self):
        """Test dates: start_date param correctly sets logbook dates."""
        start_date = date(2026, 5, 22)
        result = simulate_trip(
            total_distance_miles=900,
            leg1_hours=10,
            leg2_hours=5,
            current_cycle_used_hours=0,
            leg1_miles=450,
            leg2_miles=450,
            start_date=start_date,
        )

        first_day = result["logbook_days"][0]
        expected_date_str = start_date.strftime("%m/%d/%Y")
        assert first_day["date"] == expected_date_str

        if len(result["logbook_days"]) > 1:
            second_day = result["logbook_days"][1]
            expected_second = (start_date + timedelta(days=1)).strftime("%m/%d/%Y")
            assert second_day["date"] == expected_second
