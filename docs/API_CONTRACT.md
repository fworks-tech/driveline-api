# API Contract — Spotter AI ELD & Route Planner

**Version:** 1.0.0  
**Status:** ✅ Alpha (stable core, implementation details may change)  
**Last Updated:** 2026-05-20

This document defines the definitive API contract for the Spotter ELD & Route Planner backend. Use this as the authoritative reference for request/response formats, validation rules, and error handling.

---

## Overview

### Base URLs

| Environment | URL |
|---|---|
| **Development** | `http://localhost:8000` |
| **Production** | `https://api.spotter-eld.app` |
| **Staging** | `https://staging-api.railway.app` |

### Authentication

**Current (v1.0.0-alpha):** None required.  
**Planned (v1.0.0-api):** JWT Bearer token in `Authorization: Bearer <token>` header.

### Content Type

All requests must have:
```
Content-Type: application/json
```

All responses are:
```
Content-Type: application/json
```

### Rate Limiting

**Current (v1.0.0-alpha):** Not enforced.  
**Planned (v1.0.0-beta):** 60 requests per minute per IP address.

### CORS

**Development:** All origins allowed.  
**Production:** Only configured frontend domains allowed.

---

## Endpoints

### POST /api/plan-route/

Plan a complete trip with route calculation, HOS compliance checking, and ELD logbook generation.

#### Purpose

Given a driver's current location, a pickup location, and a dropoff location, calculate an optimal route that:
- Respects all 5 FMCSA Hours of Service rules
- Schedules mandatory rest breaks and fuel stops
- Generates a multi-day logbook with duty status transitions
- Returns waypoints, markers, and trip statistics

#### Request Schema

```json
{
  "current_location": "string",
  "pickup_location": "string",
  "dropoff_location": "string",
  "cycle_hours_used": 30.5
}
```

| Field | Type | Constraints | Required | Description |
|-------|------|-------------|----------|-------------|
| `current_location` | string | 2-500 chars | Yes | Current driver location (city, state, or full address) |
| `pickup_location` | string | 2-500 chars | Yes | Pickup/origin location |
| `dropoff_location` | string | 2-500 chars | Yes | Final destination/dropoff location |
| `cycle_hours_used` | float | 0.0–70.0 | Yes | Hours already used in the current 8-day rolling FMCSA cycle |

#### Validation Rules

| Field | Rule | Error (400) |
|-------|------|------------|
| `current_location` | 2-500 characters | `"current_location: Ensure this field has at least 2 characters."` |
| `pickup_location` | 2-500 characters | `"pickup_location: This field is required."` |
| `dropoff_location` | 2-500 characters | `"dropoff_location: Ensure this value has at most 500 characters."` |
| `cycle_hours_used` | Float, 0.0 ≤ value ≤ 70.0 | `"cycle_hours_used: Ensure this value is less than or equal to 70.0."` |
| Address validity | Must be geocodable by Nominatim | `"current_location: Address not found (Chicago, XYZ)"` |

#### Response Schema (200 OK)

```json
{
  "route_coordinates": [[lon, lat], [lon, lat], ...],
  "markers": [
    {"type": "start", "lat": 41.88, "lon": -87.63, "label": "Start: Chicago, IL"},
    {"type": "pickup", "lat": 39.77, "lon": -86.16, "label": "Pickup: Indianapolis, IN"},
    {"type": "fuel", "lat": 35.5, "lon": -90.0, "label": "Fuel Stop #1"},
    {"type": "rest", "lat": 33.0, "lon": -93.5, "label": "Rest (10-hr)"},
    {"type": "dropoff", "lat": 32.78, "lon": -96.80, "label": "Dropoff: Dallas, TX"}
  ],
  "logbook_days": [
    {
      "day": 1,
      "events": [
        {"status": "DRIVING", "start_minute": 0, "duration_minutes": 660, "label": "Driving"},
        {"status": "ON_DUTY_NOT_DRIVING", "start_minute": 660, "duration_minutes": 60, "label": "On-duty (Pickup)"},
        {"status": "DRIVING", "start_minute": 720, "duration_minutes": 300, "label": "Driving"},
        {"status": "OFF_DUTY", "start_minute": 1020, "duration_minutes": 420, "label": "Off-duty (Rest)"}
      ]
    },
    {
      "day": 2,
      "events": [
        {"status": "SLEEPER_BERTH", "start_minute": 0, "duration_minutes": 600, "label": "Sleeper berth (10-hr)"},
        {"status": "ON_DUTY_NOT_DRIVING", "start_minute": 600, "duration_minutes": 60, "label": "On-duty (Dropoff)"},
        {"status": "OFF_DUTY", "start_minute": 660, "duration_minutes": 780, "label": "Off-duty (Remaining)"}
      ]
    }
  ],
  "trip_summary": {
    "total_distance_miles": 850.5,
    "total_trip_hours": 13.5,
    "total_drive_hours": 11.0,
    "fuel_stops": 1,
    "rest_stops": 1,
    "legs": 2
  }
}
```

#### Response Field Definitions

**route_coordinates** (array of `[longitude, latitude]` pairs)
- Format: GeoJSON coordinate order (longitude first, latitude second)
- Represents the full polyline from start → pickup → dropoff
- Note: This is **different** from the `markers` format below which uses separate `lat`/`lon` fields

**markers** (array of marker objects)
- `type`: `"start"` | `"pickup"` | `"dropoff"` | `"fuel"` | `"rest"`
- `lat`: Latitude (-90 to 90)
- `lon`: Longitude (-180 to 180)
- `label`: Human-readable label (e.g., "Chicago, IL", "Fuel Stop #1")

**logbook_days** (array of day objects)
- `day`: Day number (1-indexed)
- `events`: Chronological list of duty status transitions for that day

**logbook events** (array of event objects, each with):
- `status`: One of the valid FMCSA duty statuses
- `start_minute`: Start time in minutes since midnight (0–1440)
- `duration_minutes`: Duration in minutes
- `label`: Human-readable description (e.g., "Driving", "Fuel Stop", "30-min Break")

**Valid `status` values** (FMCSA classifications):

| Status | Meaning | Used by Engine |
|--------|---------|----------------|
| `OFF_DUTY` | Not working (sleep, meals, personal) | Yes |
| `SLEEPER` | In sleeper berth (reserved for split-berth provision) | No (currently unused) |
| `SLEEPER_BERTH` | Mandatory 10-hour rest reset in sleeper berth | Yes |
| `DRIVING` | Actively driving vehicle | Yes |
| `ON_DUTY_NOT_DRIVING` | On-duty but not driving (pickup, fuel, rest stops) | Yes |

**trip_summary** (object)
- `total_distance_miles`: Total trip distance in miles (float)
- `total_trip_hours`: Total elapsed time from start to finish in hours (float) — includes rest
- `total_drive_hours`: Total actual driving time in hours (float) — capped at 11 per shift per FMCSA rule
- `fuel_stops`: Number of mandatory fuel stops (integer) — one every 1,000 miles
- `rest_stops`: Number of mandatory rest breaks (integer) — typically 10-hour resets between shifts
- `legs`: Number of driving legs (integer) — always 2 (current → pickup, pickup → dropoff)

---

## Error Responses

### 400 Bad Request

**Format:**
```json
{
  "error": "validation_error",
  "detail": "Human-readable error message",
  "status_code": 400
}
```

**Common causes:**
- Missing required field
- Field value out of range
- Location cannot be geocoded
- Invalid address format

**Example:**
```json
{
  "error": "validation_error",
  "detail": "cycle_hours_used: Ensure this value is less than or equal to 70.0.",
  "status_code": 400
}
```

### 500 Server Error

**Format:**
```json
{
  "error": "server_error",
  "detail": "An unexpected error occurred. Please try again.",
  "status_code": 500
}
```

**Common causes:**
- OSRM (routing engine) unreachable
- Nominatim (geocoding service) unreachable
- Unexpected server error (check server logs)

---

## ⚠️ Critical: Coordinate System Distinction

**This is a common source of frontend bugs.** Pay close attention:

### route_coordinates: [lon, lat] — GeoJSON Order

The `route_coordinates` array uses **GeoJSON standard order**: `[longitude, latitude]`.

```json
{
  "route_coordinates": [
    [-87.6298, 41.8781],    // Chicago: [lon, lat]
    [-86.1581, 39.7684],    // Indianapolis: [lon, lat]
    [-96.797, 32.7767]      // Dallas: [lon, lat]
  ]
}
```

**Why GeoJSON?** The OSRM routing engine (which calculates the polyline) returns coordinates in GeoJSON order, and the API passes them through directly without reordering.

### markers: separate lat/lon fields — Normal Order

The `markers` array uses **normal latitude/longitude order** (same as what you see in Google Maps):

```json
{
  "markers": [
    {
      "type": "start",
      "lat": 41.8781,        // Latitude first
      "lon": -87.6298,       // Longitude second
      "label": "Chicago, IL"
    }
  ]
}
```

### Frontend: Don't Mix These Up!

- ❌ **Wrong:** Passing `route_coordinates` directly to a map that expects `[lat, lon]`
- ❌ **Wrong:** Assuming both coordinate formats are the same
- ✅ **Right:** Explicitly document the format; add comments to your map initialization code
- ✅ **Right:** Consider reordering `route_coordinates` to `[lat, lon]` on the frontend if your map library expects that

---

## Known Limitations (v1.0.0-alpha)

### API Behavior

- ❌ No authentication — all requests are public
- ❌ No rate limiting — subject to abuse (will be added in beta)
- ❌ No database persistence — trip plans are calculated but not saved
- ❌ Single fixed route structure — always 2 legs (current → pickup → dropoff)
- ❌ No circuit breakers — external API failures will timeout requests

### External Dependencies

- **Nominatim (OpenStreetMap geocoding):** Uses public API; expects ~1 request per second maximum
- **OSRM (Open Source Routing Machine):** Uses public API; typical response time 1-2 seconds

### HOS Engine Scope

- ✅ Enforces all 5 FMCSA property-carrying (commercial) rules
- ❌ Does not model personal conveyance or yard moves
- ❌ Does not support split sleeper berth (8+2 provision) — planned for v1.0.0-api
- ❌ Does not track cycle history across multiple trips

---

## Performance

**Typical response time:** 2–5 seconds  
**Timeout:** 30 seconds

The delay is primarily from:
1. Nominatim geocoding (~1–2 sec per address × 3)
2. OSRM routing (~1–2 sec × 2 route segments)
3. HOS engine simulation (<500 ms)

---

## Change History

### v1.0.0-alpha-api (2026-05-20)
- Initial contract definition
- Fixed coordinate order documentation ([lon, lat] in route_coordinates)
- Fixed cycle_hours_used type (float, not integer)
- Added SLEEPER_BERTH to valid status enum
- Documented 2-leg structure and trip_summary.legs = 2 always

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) — System design and component layers
- [HOS Engine Reference](HOS_ENGINE.md) — Deep dive into FMCSA HOS rule implementation
- [OpenAPI Specification](openapi.yaml) — Machine-readable API schema

