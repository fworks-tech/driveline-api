"""
HOS (Hours of Service) Engine — FMCSA Property-Carrying Rules Simulator.

Rules enforced:
  - 11-hour driving limit per shift
  - 14-hour on-duty window per shift (once started, clock runs)
  - 30-minute mandatory break after 8 cumulative driving hours within a shift
  - 10-hour sleeper-berth / off-duty reset between shifts
  - 70-hour / 8-day rolling cycle limit
  - Fuel stop (On-Duty Not Driving, 0.5 hr) every 1,000 miles
  - 1 hour On-Duty Not Driving for pickup
  - 1 hour On-Duty Not Driving for dropoff
"""

from __future__ import annotations

FUEL_INTERVAL_MILES = 1000.0
FUEL_STOP_HOURS = 0.5  # 30 minutes
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0
MAX_DRIVE_PER_SHIFT = 11.0
MAX_WINDOW_PER_SHIFT = 14.0  # on-duty window
BREAK_DRIVE_THRESHOLD = 8.0  # drive hours before mandatory 30-min break
BREAK_DURATION = 0.5  # 30 minutes
REST_DURATION = 10.0  # 10-hour reset
MAX_CYCLE_HOURS = 70.0


def simulate_trip(
    total_distance_miles: float,
    leg1_hours: float,
    leg2_hours: float,
    current_cycle_used_hours: float,
    leg1_miles: float,
    leg2_miles: float,
) -> dict:
    """
    Simulate the full trip and return structured logbook data.

    leg1 = current_location -> pickup
    leg2 = pickup -> dropoff
    """
    events: list[dict] = []
    current_time = 0.0  # hours elapsed since trip start

    # --- Mutable state (use a dict so nested helpers can mutate) ---
    state = {
        "cycle_hours": current_cycle_used_hours,  # rolling 70-hr cycle
        "shift_drive": 0.0,  # driving hours this shift (max 11)
        "shift_on_duty": 0.0,  # on-duty hours this shift (max 14 window)
        "shift_start": None,  # absolute hour when this shift started
        "drive_since_break": 0.0,  # driving since last 30-min break (max 8)
        "miles_since_fuel": 0.0,
        "num_fuel_stops": 0,
        "num_rest_stops": 0,
    }

    # Average speed across entire trip (for mile-tracking within timed legs)
    if (leg1_hours + leg2_hours) > 0:
        avg_speed = total_distance_miles / (leg1_hours + leg2_hours)
    else:
        avg_speed = 55.0  # fallback

    # ------------------------------------------------------------------ helpers

    def add_event(status: str, duration: float, label: str, location: str = "") -> None:
        nonlocal current_time
        if duration <= 0:
            return
        events.append(
            {
                "status": status,
                "start_hour": round(current_time, 4),
                "end_hour": round(current_time + duration, 4),
                "duration_hours": round(duration, 4),
                "label": label,
                "location": location,
            }
        )
        current_time += duration

    def start_shift_if_needed() -> None:
        """Record shift start time when first going on-duty."""
        if state["shift_start"] is None:
            state["shift_start"] = current_time

    def on_duty_elapsed() -> float:
        """Hours elapsed in current on-duty window."""
        if state["shift_start"] is None:
            return 0.0
        return current_time - state["shift_start"]

    def remaining_window() -> float:
        """Hours left in 14-hr on-duty window."""
        return max(0.0, MAX_WINDOW_PER_SHIFT - on_duty_elapsed())

    def remaining_drive() -> float:
        """Hours of driving left this shift."""
        return max(0.0, MAX_DRIVE_PER_SHIFT - state["shift_drive"])

    def remaining_break_drive() -> float:
        """Hours of driving before mandatory 30-min break."""
        return max(0.0, BREAK_DRIVE_THRESHOLD - state["drive_since_break"])

    def remaining_cycle() -> float:
        """Hours left in 70-hr cycle."""
        return max(0.0, MAX_CYCLE_HOURS - state["cycle_hours"])

    def do_rest(label: str = "Rest (10-hr Reset)") -> None:
        """Insert a 10-hour sleeper-berth rest and reset shift counters."""
        add_event("SLEEPER_BERTH", REST_DURATION, label)
        state["shift_drive"] = 0.0
        state["shift_on_duty"] = 0.0
        state["shift_start"] = None
        state["drive_since_break"] = 0.0
        state["num_rest_stops"] += 1

    def do_break() -> None:
        """Insert a mandatory 30-minute off-duty break."""
        add_event("OFF_DUTY", BREAK_DURATION, "30-min Break")
        state["drive_since_break"] = 0.0
        # The 14-hr window keeps running; shift_on_duty accumulates implicitly
        # (break counts against the window but not against driving hours)

    def do_fuel(label: str = "Fuel Stop") -> None:
        """Insert a 30-minute on-duty fuel stop."""
        start_shift_if_needed()
        add_event("ON_DUTY_ND", FUEL_STOP_HOURS, label)
        state["shift_on_duty"] += FUEL_STOP_HOURS
        state["cycle_hours"] += FUEL_STOP_HOURS
        state["miles_since_fuel"] = 0.0
        state["num_fuel_stops"] += 1

    def drive_segment(hours: float, miles: float, label: str) -> None:
        """
        Drive a segment, breaking it into compliant chunks and inserting
        mandatory breaks, rests, and fuel stops as needed.
        """
        remaining_hours = hours
        remaining_miles = miles

        while remaining_hours > 0.001:
            # --- Check if rest is immediately required ---
            if (
                state["cycle_hours"] >= MAX_CYCLE_HOURS
                or remaining_drive() <= 0.001
                or remaining_window() <= 0.001
            ):
                do_rest()
                continue

            # --- How much can we drive before hitting a limit? ---
            # Candidate caps (all in hours)
            cap_drive = remaining_drive()
            cap_window = remaining_window()
            cap_break = remaining_break_drive()
            cap_cycle = remaining_cycle()
            # Miles-to-fuel in hours at current speed
            miles_to_fuel = max(0.0, FUEL_INTERVAL_MILES - state["miles_since_fuel"])
            cap_fuel_hours = (
                miles_to_fuel / avg_speed if avg_speed > 0 else float("inf")
            )

            # Smallest binding cap
            chunk_hours = min(
                remaining_hours,
                cap_drive,
                cap_window,
                cap_break,
                cap_cycle,
                cap_fuel_hours,
            )
            chunk_hours = max(chunk_hours, 0.0)

            if chunk_hours <= 0.001:
                # Determine why we're stuck and resolve
                if remaining_break_drive() <= 0.001:
                    do_break()
                elif (
                    remaining_drive() <= 0.001
                    or remaining_window() <= 0.001
                    or remaining_cycle() <= 0.001
                ):
                    do_rest()
                else:
                    # Fuel stop needed before we can continue
                    do_fuel()
                continue

            chunk_miles = (
                (chunk_hours / remaining_hours) * remaining_miles
                if remaining_hours > 0
                else 0.0
            )

            # --- Drive the chunk ---
            start_shift_if_needed()
            add_event("DRIVING", chunk_hours, label)
            state["shift_drive"] += chunk_hours
            state["shift_on_duty"] += chunk_hours
            state["drive_since_break"] += chunk_hours
            state["cycle_hours"] += chunk_hours
            state["miles_since_fuel"] += chunk_miles

            remaining_hours -= chunk_hours
            remaining_miles -= chunk_miles

            # --- Post-chunk checks ---
            # Fuel stop if we've hit 1,000 miles and still have more driving
            if (
                state["miles_since_fuel"] >= FUEL_INTERVAL_MILES - 0.001
                and remaining_hours > 0.001
            ):
                do_fuel()

            # Mandatory break if 8 hrs driving reached and still more to drive
            if (
                state["drive_since_break"] >= BREAK_DRIVE_THRESHOLD - 0.001
                and remaining_hours > 0.001
            ):
                do_break()

    def do_on_duty_nd(duration: float, label: str, location: str = "") -> None:
        """On-Duty Not Driving activity (pickup, dropoff, fuel)."""
        start_shift_if_needed()
        # Check if rest needed first
        if remaining_window() < duration or remaining_cycle() < duration:
            do_rest()
            start_shift_if_needed()
        add_event("ON_DUTY_ND", duration, label, location)
        state["shift_on_duty"] += duration
        state["cycle_hours"] += duration

    # ------------------------------------------------------------------ simulate

    # Leg 1: Current location -> Pickup
    drive_segment(leg1_hours, leg1_miles, "Driving to Pickup")

    # Pickup activity
    do_on_duty_nd(PICKUP_HOURS, "Pickup", "Pickup Location")

    # Leg 2: Pickup -> Dropoff
    drive_segment(leg2_hours, leg2_miles, "Driving to Dropoff")

    # Dropoff activity
    do_on_duty_nd(DROPOFF_HOURS, "Dropoff", "Dropoff Location")

    # ------------------------------------------------------------------ group by day

    total_trip_hours = current_time
    num_days = int(total_trip_hours / 24) + 1

    logbook_days = []
    total_driving_hours = 0.0

    for day in range(num_days):
        day_start = day * 24.0
        day_end = day_start + 24.0

        day_events = []
        day_drive = 0.0
        day_on_duty = 0.0

        for ev in events:
            # Clip event to this 24-hour window
            seg_start = max(ev["start_hour"], day_start)
            seg_end = min(ev["end_hour"], day_end)
            if seg_end <= seg_start:
                continue

            clipped = {
                "status": ev["status"],
                "start_hour": round(seg_start - day_start, 4),
                "end_hour": round(seg_end - day_start, 4),
                "duration_hours": round(seg_end - seg_start, 4),
                "label": ev["label"],
                "location": ev.get("location", ""),
            }
            day_events.append(clipped)

            if ev["status"] == "DRIVING":
                day_drive += seg_end - seg_start
            if ev["status"] in ("DRIVING", "ON_DUTY_ND"):
                day_on_duty += seg_end - seg_start

        # Fill gaps with OFF_DUTY
        day_events_filled = []
        cursor = 0.0
        for ev in sorted(day_events, key=lambda e: e["start_hour"]):
            if ev["start_hour"] > cursor + 0.001:
                day_events_filled.append(
                    {
                        "status": "OFF_DUTY",
                        "start_hour": round(cursor, 4),
                        "end_hour": round(ev["start_hour"], 4),
                        "duration_hours": round(ev["start_hour"] - cursor, 4),
                        "label": "Off Duty",
                        "location": "",
                    }
                )
            day_events_filled.append(ev)
            cursor = ev["end_hour"]

        if cursor < 24.0 - 0.001:
            day_events_filled.append(
                {
                    "status": "OFF_DUTY",
                    "start_hour": round(cursor, 4),
                    "end_hour": 24.0,
                    "duration_hours": round(24.0 - cursor, 4),
                    "label": "Off Duty",
                    "location": "",
                }
            )

        total_driving_hours += day_drive

        logbook_days.append(
            {
                "day": day,
                "date_offset": day,
                "events": day_events_filled,
                "total_driving_hours": round(day_drive, 2),
                "total_on_duty_hours": round(day_on_duty, 2),
            }
        )

    return {
        "logbook_days": logbook_days,
        "total_trip_hours": round(total_trip_hours, 2),
        "total_driving_hours": round(total_driving_hours, 2),
        "num_fuel_stops": state["num_fuel_stops"],
        "num_rest_stops": state["num_rest_stops"],
    }
