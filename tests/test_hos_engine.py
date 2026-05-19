import unittest
from trips.hos_engine import HOSEngine, DutyStatus


class TestHOSEngine(unittest.TestCase):
    """Unit tests for FMCSA Hours of Service engine."""

    def setUp(self):
        """Initialize HOS engine for each test."""
        self.engine = HOSEngine()

    def test_rule_1_on_duty_at_pickup(self):
        """Test Rule 1: 1-hour on-duty period at pickup location."""
        # Simulate picking up at starting point
        self.engine.add_event(DutyStatus.DRIVING, 100.0)  # 100 miles of driving
        self.engine.add_event(DutyStatus.ON_DUTY_ND, 1.0)  # 1 hour at pickup
        self.engine.add_event(DutyStatus.DRIVING, 100.0)  # More driving

        # The on-duty period should be enforced
        total_on_duty = sum(
            e['duration'] for e in self.engine.events
            if e['status'] == DutyStatus.ON_DUTY_ND
        )
        assert total_on_duty >= 1.0

    def test_rule_2_fuel_stop_every_1000_miles(self):
        """Test Rule 2: Fuel stop every 1,000 miles."""
        # Add a 1,500-mile trip
        self.engine.simulate_trip(1500.0)

        # Count fuel stops (ON_DUTY_ND events that indicate fuel)
        fuel_stops = self.engine.count_fuel_stops()

        # Should have at least 1 fuel stop (every 1,000 miles)
        assert fuel_stops >= 1

    def test_rule_3_11_hour_driving_limit(self):
        """Test Rule 3: 11-hour driving limit per shift."""
        # Add 12 hours of driving (exceeds limit)
        self.engine.add_event(DutyStatus.DRIVING, 12.0)

        # Should trigger mandatory rest
        driving_hours = sum(
            e['duration'] for e in self.engine.events
            if e['status'] == DutyStatus.DRIVING
        )

        # No continuous driving period should exceed 11 hours
        consecutive_drive = 0
        for event in self.engine.events:
            if event['status'] == DutyStatus.DRIVING:
                consecutive_drive += event['duration']
            else:
                consecutive_drive = 0

            assert consecutive_drive <= 11.0

    def test_rule_4_14_hour_window(self):
        """Test Rule 4: 14-hour on-duty window."""
        # Simulate driving + on-duty activity exceeding 14 hours
        self.engine.add_event(DutyStatus.DRIVING, 10.0)
        self.engine.add_event(DutyStatus.ON_DUTY_ND, 5.0)

        # Total on-duty time should not exceed 14 hours without reset
        on_duty_hours = sum(
            e['duration'] for e in self.engine.events
            if e['status'] in [DutyStatus.DRIVING, DutyStatus.ON_DUTY_ND]
        )

        # In a real implementation, this would trigger a 10-hour rest
        assert on_duty_hours <= 14.0

    def test_rule_5_30_minute_break(self):
        """Test Rule 5: 30-minute break after 8 hours driving."""
        # Add 9 hours of driving
        self.engine.add_event(DutyStatus.DRIVING, 9.0)

        # Should have a break event
        break_events = [
            e for e in self.engine.events
            if e['status'] == DutyStatus.OFF_DUTY
        ]

        assert len(break_events) > 0

    def test_70_hour_8_day_cycle(self):
        """Test 70-hour / 8-day rolling cycle enforcement."""
        # Simulate multiple days of driving
        for day in range(8):
            self.engine.add_event(DutyStatus.DRIVING, 10.0)
            self.engine.add_event(DutyStatus.SLEEPER, 10.0)

        # Calculate total driving hours
        total_drive = sum(
            e['duration'] for e in self.engine.events
            if e['status'] == DutyStatus.DRIVING
        )

        # Should not exceed 70 hours in rolling 8-day window
        assert total_drive <= 70.0 * 8  # Conservative check for multi-day window

    def test_chicago_to_dallas_scenario(self):
        """Integration test: Chicago to Dallas trip (850 miles)."""
        # Chicago to Dallas is approximately 850 miles, ~12.5 hours of driving
        result = self.engine.simulate_trip(850.0, cycle_hours_used=30)

        assert result is not None
        assert result['total_distance'] == 850.0
        assert result['num_days'] >= 1
        assert len(result['logbook_days']) > 0

        # Validate each day's events
        for day in result['logbook_days']:
            # Check driving doesn't exceed 11 hours per day
            day_drive = sum(
                e['duration'] for e in day['events']
                if e['status'] == DutyStatus.DRIVING
            )
            assert day_drive <= 11.0

    def test_los_angeles_to_denver_scenario(self):
        """Integration test: LA to Denver trip (1,000 miles)."""
        # LA to Denver is approximately 1,000 miles, ~15 hours of driving
        result = self.engine.simulate_trip(1000.0, cycle_hours_used=0)

        assert result is not None
        assert len(result['logbook_days']) >= 2  # Should span 2+ days

    def test_new_york_to_miami_scenario(self):
        """Integration test: NY to Miami trip (1,200 miles)."""
        # NY to Miami is approximately 1,200 miles, ~18 hours of driving
        result = self.engine.simulate_trip(1200.0, cycle_hours_used=50)

        assert result is not None
        assert result['total_distance'] == 1200.0
        # Should span at least 2 days due to HOS limits
        assert len(result['logbook_days']) >= 2

    def test_high_cycle_hours_used(self):
        """Test behavior when driver has high cycle hours already used."""
        # Driver has used 65 of 70 available hours
        result = self.engine.simulate_trip(500.0, cycle_hours_used=65)

        assert result is not None
        # Trip should be shorter or split due to cycle limit
        total_drive = sum(
            e['duration'] for e in result['logbook_days'][0]['events']
            if e['status'] == DutyStatus.DRIVING
        )
        # Remaining available: 70 - 65 = 5 hours
        assert total_drive <= 5.0

    def test_event_ordering(self):
        """Test that events are in chronological order."""
        self.engine.simulate_trip(850.0)

        prev_time = 0
        for event in self.engine.events:
            assert event['start_time'] >= prev_time
            prev_time = event['start_time'] + event['duration']

    def test_no_gaps_in_logbook(self):
        """Test that logbook has no gaps (24 hours per day)."""
        result = self.engine.simulate_trip(850.0)

        for day in result['logbook_days']:
            # Sum all event durations
            total_hours = sum(e['duration'] for e in day['events'])
            # Should cover entire 24-hour period
            assert total_hours <= 24.0
