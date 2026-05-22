# HOS Engine Reference — FMCSA Hours of Service Simulator

**Source File:** `trips/hos_engine.py`  
**Audience:** Backend developers maintaining the engine, compliance reviewers  
**Last Updated:** 2026-05-20

This document provides a deep reference for the FMCSA Hours of Service (HOS) simulation engine. It covers rule implementation, algorithm logic, state management, and known behaviors.

---

## Overview

### Purpose

The HOS engine simulates a complete trip while enforcing all 5 FMCSA Hours of Service rules for property-carrying (commercial) vehicles. It accepts trip parameters (distance, time, current cycle hours used) and returns a multi-day logbook with duty status transitions that comply with all federal regulations.

### Entry Point

```python
def simulate_trip(
    total_distance_miles: float,
    leg1_hours: float,
    leg2_hours: float,
    current_cycle_used_hours: float,
    leg1_miles: float,
    leg2_miles: float,
) -> dict
```

**Inputs:**
- `total_distance_miles`: Sum of leg1_miles + leg2_miles
- `leg1_hours`: Time (hours) for first route segment (current → pickup)
- `leg2_hours`: Time (hours) for second route segment (pickup → dropoff)
- `current_cycle_used_hours`: Hours already used in the driver's current 8-day cycle
- `leg1_miles`: Distance (miles) for first segment
- `leg2_miles`: Distance (miles) for second segment

**Output:** Dictionary containing:
```python
{
    'logbook_days': [day1_dict, day2_dict, ...],
    'total_trip_hours': float,
    'total_driving_hours': float,
    'num_fuel_stops': int,
    'num_rest_stops': int,
}
```

---

## FMCSA Rules Enforced

### Rule 1: 11-Hour Driving Limit Per Shift

**FMCSA Citation:** 49 CFR 395.8(a)  
**Engine Constant:** `MAX_DRIVE_PER_SHIFT = 11.0`

A driver may not drive more than 11 hours in a single shift. After 11 hours of driving, a 10-hour rest reset is mandatory.

**Enforcement in Engine:**
- Each driving segment is capped at 11 hours
- Once 11 hours accumulated, shift ends and 10-hour rest begins
- Tracked via `shift_drive` accumulator

### Rule 2: 14-Hour On-Duty Window

**FMCSA Citation:** 49 CFR 395.8(a)  
**Engine Constant:** `MAX_WINDOW_PER_SHIFT = 14.0`

A driver may not be on-duty (driving + on-duty-not-driving) for more than 14 consecutive hours. The window resets after a 10-hour off-duty/sleeper berth period.

**Enforcement in Engine:**
- `shift_on_duty` tracks total on-duty time in current shift
- Includes driving time + fuel stops + pickup/dropoff duties
- Does not include off-duty time or sleeper berth time

### Rule 3: 30-Minute Break After 8 Hours Driving

**FMCSA Citation:** 49 CFR 395.8(a)(3)(ii)  
**Engine Constants:** `BREAK_DRIVE_THRESHOLD = 8.0`, `BREAK_DURATION = 0.5`

After 8 hours of driving, a mandatory 30-minute break (off-duty or sleeper berth) is required before resuming.

**Enforcement in Engine:**
- `drive_since_break` accumulator tracks driving since last break
- When >= 8 hours, OFF_DUTY break is inserted
- Break event: status=OFF_DUTY, duration=30 minutes

### Rule 4: 70-Hour / 8-Day Cycle

**FMCSA Citation:** 49 CFR 395.8(a)  
**Engine Constant:** `MAX_CYCLE_HOURS = 70.0`

A driver may not work more than 70 hours in any rolling 8-day period. The cycle resets after 34+ consecutive off-duty hours.

**Enforcement in Engine:**
- `cycle_hours` accumulator tracks hours worked (driving + on-duty)
- Input `current_cycle_used_hours` is subtracted from 70
- When remaining cycle hours <= 0, 34-hour reset inserted (modeled as 10-hour SLEEPER_BERTH + 24-hour OFF_DUTY)
- Excess hours are carried into next 8-day cycle

### Rule 5: 1-Hour On-Duty At Pickup and Dropoff

**Engine Constants:** `PICKUP_HOURS = 1.0`, `DROPOFF_HOURS = 1.0`

A driver must spend at least 1 hour on-duty (not driving) at each pickup and dropoff location (loading/unloading, inspections, etc.). This is not explicitly codified by FMCSA but is a reasonable operational assumption.

**Enforcement in Engine:**
- ON_DUTY_ND event inserted at pickup location for 1 hour
- ON_DUTY_ND event inserted at dropoff location for 1 hour

### Additional Rule: Fuel Stop Every 1,000 Miles

**Not FMCSA-mandated** but is an operational best practice.  
**Engine Constants:** `FUEL_INTERVAL_MILES = 1000.0`, `FUEL_STOP_HOURS = 0.5`

A fuel stop (30 minutes on-duty) is inserted every 1,000 miles of driving.

**Enforcement in Engine:**
- `miles_since_fuel` accumulator
- When >= 1,000 miles, 30-minute ON_DUTY_ND fuel stop inserted
- Resets counter

---

## Algorithm Walkthrough

### Trip Structure

All trips have a fixed 2-leg structure:
1. **Leg 1:** Current location → Pickup location
2. **Leg 2:** Pickup location → Dropoff location

The engine processes:
```
drive_segment(leg1_miles, leg1_hours)
  ↓
1-hour pickup duties (ON_DUTY_ND)
  ↓
drive_segment(leg2_miles, leg2_hours)
  ↓
1-hour dropoff duties (ON_DUTY_ND)
```

### drive_segment() Loop Logic

For each leg, the engine repeats this loop until all miles are consumed:

```python
while remaining_miles > 0:
    # 1. Calculate the minimum cap across ALL constraints
    max_drive_hours = min(
        (MAX_DRIVE_PER_SHIFT - shift_drive),        # Rule 1: 11-hr limit
        (MAX_WINDOW_PER_SHIFT - shift_on_duty),     # Rule 2: 14-hr window
        (remaining_cycle_hours),                    # Rule 4: 70-hr cycle
        (8 - drive_since_break),                    # Rule 3: 8-hr before break (if applicable)
        (1000 - miles_since_fuel) / avg_speed,      # Fuel rule: 1,000 mile intervals
    )
    
    # 2. Cap by average speed to miles available
    segment_miles = min(remaining_miles, max_drive_hours * avg_speed)
    segment_hours = segment_miles / avg_speed
    
    # 3. Emit driving event
    add_event("DRIVING", segment_hours, label=f"Driving ({segment_miles:.0f} mi)")
    
    # 4. Update state
    shift_drive += segment_hours
    shift_on_duty += segment_hours
    drive_since_break += segment_hours
    miles_since_fuel += segment_miles
    cycle_hours += segment_hours
    remaining_miles -= segment_miles
    
    # 5. Check if breaks/stops are needed
    if drive_since_break >= 8:
        add_event("OFF_DUTY", 0.5, label="30-min Break")
        drive_since_break = 0
    
    if miles_since_fuel >= 1000:
        add_event("ON_DUTY_ND", 0.5, label="Fuel Stop")
        miles_since_fuel = 0
    
    if shift_drive >= 11:
        add_event("SLEEPER_BERTH", 10, label="10-hr Rest Reset")
        shift_drive = 0
        shift_on_duty = 0
        miles_since_break = 0
        new_shift()
```

### Average Speed Calculation

```python
avg_speed = total_distance_miles / (leg1_hours + leg2_hours)
```

If both legs have 0 duration (degenerate case), defaults to 55 mph.

**Used for:**
- Converting hour caps into distance caps
- Calculating segment time from segment distance

---

## Duty Status Values

The engine emits the following status strings. Note: only a subset are actually used in current implementation.

| Status | FMCSA Class | Emitted by Engine | Meaning |
|--------|-------------|-------------------|---------|
| `DRIVING` | Driving | ✅ Yes | Actively operating the vehicle |
| `ON_DUTY_ND` | On-duty not driving | ✅ Yes | Pickup, dropoff, fuel stop, other on-duty non-driving |
| `OFF_DUTY` | Off-duty | ✅ Yes | 30-minute mandatory break after 8 hours driving |
| `SLEEPER_BERTH` | Sleeper berth | ✅ Yes | 10-hour mandatory rest reset; after 11 hrs driving or 14-hr window |
| `SLEEPER` | Sleeper berth | ❌ No | Reserved for future split sleeper berth (8+2 provision) |

---

## Return Value Structure

### Top-Level Dictionary

```python
{
    'logbook_days': [day1, day2, day3, ...],
    'total_trip_hours': float,
    'total_driving_hours': float,
    'num_fuel_stops': int,
    'num_rest_stops': int,
}
```

### Logbook Day Object

```python
{
    'day': 1,                                  # 1-indexed day number
    'date_offset': 0,                          # Days since trip start (0 = first day)
    'total_driving_hours': 11.0,               # Total DRIVING time on this day
    'total_on_duty_hours': 13.5,               # Total on-duty time (DRIVING + ON_DUTY_ND)
    'events': [event1, event2, ...]            # Chronological list of events
}
```

### Logbook Event Object

```python
{
    'status': 'DRIVING',                       # Duty status
    'start_hour': 0.5,                         # Start time in fractional hours since midnight
    'end_hour': 11.5,                          # End time in fractional hours since midnight
    'label': 'Driving to Pickup',              # Human-readable label
}
```

**Important:** Event objects use `start_hour`/`end_hour` (floats, representing fractional hours). The API view (`trips/views.py`) transforms these to `start_minute`/`duration_minutes` (integers, for the JSON response).

---

## State Variables

The engine maintains these accumulators during simulation:

| Variable | Type | Reset Condition | Purpose |
|----------|------|-----------------|---------|
| `shift_drive` | float | Every 11 hrs driven | Hours driven in current shift (Rule 1) |
| `shift_on_duty` | float | After 10-hr rest | Total on-duty time in current shift (Rule 2) |
| `shift_start` | datetime-like | After 10-hr rest | When current shift began |
| `drive_since_break` | float | Every 30-min break | Hours driven since last mandatory break (Rule 3) |
| `miles_since_fuel` | float | Every fuel stop | Miles driven since last fuel stop |
| `cycle_hours` | float | After 34-hr reset or on 8-day boundary | Hours worked in current 8-day cycle (Rule 4) |
| `num_fuel_stops` | int | Never (accumulated) | Total fuel stops for trip |
| `num_rest_stops` | int | Never (accumulated) | Total 10-hour rest resets for trip |

---

## Known Behaviors and Edge Cases

### Very Short Trips (< 1,000 miles)

- No fuel stop is inserted
- May be a single logbook day if total hours < 14
- Example: 500-mile trip driving at 60 mph = 8.33 hours → no breaks needed

### Trips with Cycle Hours Near 70

- If `current_cycle_used_hours` = 65 and remaining cycle = 5 hours
- Engine caps driving to 5 hours, forces rest reset
- 34-hour reset inserted (modeled as 10-hour SLEEPER_BERTH + 24-hour OFF_DUTY)
- Trip resumes in fresh 8-day cycle

### Fixed 2-Leg Structure

- The engine always assumes exactly 2 driving legs
- No support for more complex routing (stops between pickup and dropoff, return trips, etc.)
- This is a fundamental limitation of the current architecture
- Future versions may support N-leg trips

### Pickup and Dropoff Duties

- 1-hour ON_DUTY_ND is mandatory at each location
- Not configurable per location
- May push trip over 14-hour window, forcing rest reset before dropoff duties

### Rest Reset Modeling

- 10-hour SLEEPER_BERTH status
- Followed by transition to next day/shift
- Does not model split-berth provision (8 sleeper + 2 off-duty = 10-hour reset)

---

## Testing

### Test File

`trips/tests/test_hos_engine.py`

### Run Tests

```bash
# Run all HOS engine tests
pytest trips/tests/test_hos_engine.py -v

# Run specific test
pytest trips/tests/test_hos_engine.py::test_simulate_trip_basic -v

# Run with coverage
pytest trips/tests/test_hos_engine.py --cov=trips.hos_engine --cov-report=term-missing
```

### Key Test Cases

- **Basic long-haul (850 miles):** Validates all 5 rules, rest resets, fuel stops
- **Short trip (< 1,000 miles):** No fuel stop, single day
- **High cycle hours (65 hours used):** Tests cycle reset logic
- **Exact 11-hour cap:** Tests boundary condition
- **8-hour break threshold:** Tests mandatory break insertion

---

## Future Enhancements

### Split Sleeper Berth (8+2 Provision)

**Regulation:** Drivers may accumulate sleeper berth time in two segments (8 hours + 2 hours) to total 10 hours, with the segments separated by at least 2 hours of on-duty or off-duty time.

**Current:** Not implemented. SLEEPER status is reserved for this.

**Implementation:** Would require tracking separate sleeper berth segments and allowing drive resumption after 8-hour segment if 2-hour break follows.

### Personal Conveyance Time

**Regulation:** Time driving a vehicle for personal use (not under dispatch) may be reported as off-duty even though the vehicle is in motion.

**Current:** Not tracked.

**Implementation:** Would require annotation of leg segments and time allocation rules.

### Yard Move Rules

**Regulation:** Short movements of vehicles within a facility for maintenance, fueling, or staging may not count toward driving hours.

**Current:** Not tracked.

**Implementation:** Would require distance threshold and on-property flag.

### Database-Backed Cycle Tracking

**Current State:** Cycle hours are passed as input (`current_cycle_used_hours`). The engine doesn't track history.

**Planned (v1.0.0-beta):** Store completed trips in database and automatically calculate current cycle hours for next trip.

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) — System design and request flow
- [API Contract](API_CONTRACT.md) — Request/response schemas and coordinate system note
- [OpenAPI Specification](openapi.yaml) — Machine-readable schema
