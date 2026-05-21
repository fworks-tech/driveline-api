# Frontend Integration Guide

**Audience:** Frontend developers (React/Vite team) integrating with the Spotter ELD API  
**Related Projects:** [`spotter-eld-logging-app`](https://github.com/fworks-tech/spotter-eld-logging-app) (React 19 + Vite)  
**Last Updated:** 2026-05-20

This document explains how the frontend connects to the backend API, the request/response contract, and common integration patterns.

---

## Quick Integration Overview

```
Frontend (React)              Backend (Django)
┌──────────────────┐         ┌──────────────────┐
│ http://3000      │         │ http://8000      │
│                  │ POST    │                  │
│ Trip Form ─────► /api/v1/plan-route/ ──► HOS Engine
│                  │         │   ↓              │
│ ◄─────────────── │◄────────│ Response         │
│ Route Map        │         │                  │
│ Logbook          │         └──────────────────┘
│ Summary          │
└──────────────────┘
```

### Single Endpoint

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/v1/plan-route/` | Plan a complete trip with HOS compliance |

---

## Request Contract

### Endpoint: `POST /api/v1/plan-route/`

```typescript
// Frontend TypeScript interface
interface TripFormValues {
  current_location: string;      // Max 500 chars, required
  pickup_location: string;       // Max 500 chars, required
  dropoff_location: string;      // Max 500 chars, required
  cycle_hours_used: number;      // 0.0–70.0, required
}
```

### Request Example (Axios)

```typescript
// From: frontend/src/lib/api.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',  // Relative path, proxied to backend by Vite
  headers: {
    'Content-Type': 'application/json',
  },
});

// Send request
const planRoute = async (data: TripFormValues) => {
  const response = await apiClient.post('/plan-route/', data);
  return response.data;
};
```

### Request Validation Rules (Backend Enforces)

| Field | Constraint | Error if Invalid |
|-------|-----------|------------------|
| `current_location` | 2–500 chars, must be geocodable | 400: "Address not found (Chicago, XYZ)" |
| `pickup_location` | 2–500 chars, must be geocodable | 400: "Address not found..." |
| `dropoff_location` | 2–500 chars, must be geocodable | 400: "Address not found..." |
| `cycle_hours_used` | Float, 0.0 ≤ value ≤ 70.0 | 400: "Ensure this value is less than or equal to 70.0" |
| All required | Must be present | 400: "This field is required" |

---

## Response Contract

### Success Response (200 OK)

```typescript
interface PlanRouteResponse {
  route_coordinates: Array<[number, number]>;  // [lon, lat] pairs (GeoJSON order!)
  markers: Marker[];
  logbook_days: LogbookDay[];
  trip_summary: TripSummary;
}

interface Marker {
  type: "start" | "pickup" | "dropoff" | "fuel" | "rest";
  lat: number;      // Latitude (-90 to 90)
  lon: number;      // Longitude (-180 to 180)
  label: string;    // Human-readable label
}

interface LogbookDay {
  day: number;          // 1-indexed day number
  events: LogbookEvent[];
}

interface LogbookEvent {
  status: "OFF_DUTY" | "SLEEPER" | "SLEEPER_BERTH" | "DRIVING" | "ON_DUTY_ND";
  start_minute: number;      // Minutes since midnight (0–1440)
  duration_minutes: number;  // Duration in minutes
  label: string;             // Human-readable description
}

interface TripSummary {
  total_distance_miles: number;
  total_trip_hours: number;
  total_drive_hours: number;
  fuel_stops: number;
  rest_stops: number;
  legs: number;  // Always 2 (current → pickup → dropoff)
}
```

### Response Example

```json
{
  "route_coordinates": [
    [-87.6298, 41.8781],
    [-87.5, 41.8],
    [-86.1581, 39.7684],
    [-96.797, 32.7767]
  ],
  "markers": [
    {
      "type": "start",
      "lat": 41.8781,
      "lon": -87.6298,
      "label": "Start: Chicago, IL"
    },
    {
      "type": "pickup",
      "lat": 39.7684,
      "lon": -86.1581,
      "label": "Pickup: Indianapolis, IN"
    },
    {
      "type": "fuel",
      "lat": 35.5,
      "lon": -90.0,
      "label": "Fuel Stop #1"
    },
    {
      "type": "rest",
      "lat": 33.0,
      "lon": -93.5,
      "label": "Rest (10-hr)"
    },
    {
      "type": "dropoff",
      "lat": 32.7767,
      "lon": -96.797,
      "label": "Dropoff: Dallas, TX"
    }
  ],
  "logbook_days": [
    {
      "day": 1,
      "events": [
        {
          "status": "DRIVING",
          "start_minute": 0,
          "duration_minutes": 660,
          "label": "Driving"
        },
        {
          "status": "ON_DUTY_ND",
          "start_minute": 660,
          "duration_minutes": 60,
          "label": "On-duty (Pickup)"
        },
        {
          "status": "DRIVING",
          "start_minute": 720,
          "duration_minutes": 300,
          "label": "Driving"
        },
        {
          "status": "OFF_DUTY",
          "start_minute": 1020,
          "duration_minutes": 420,
          "label": "Off-duty (Rest)"
        }
      ]
    },
    {
      "day": 2,
      "events": [
        {
          "status": "SLEEPER_BERTH",
          "start_minute": 0,
          "duration_minutes": 600,
          "label": "Sleeper berth (10-hr)"
        },
        {
          "status": "ON_DUTY_ND",
          "start_minute": 600,
          "duration_minutes": 60,
          "label": "On-duty (Dropoff)"
        },
        {
          "status": "OFF_DUTY",
          "start_minute": 660,
          "duration_minutes": 780,
          "label": "Off-duty (Remaining)"
        }
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

---

## ⚠️ Critical: Coordinate System Distinction

**This is the #1 source of frontend bugs.** Pay close attention:

### `route_coordinates`: [longitude, latitude] — GeoJSON Order

The `route_coordinates` array uses **GeoJSON standard**: `[longitude, latitude]`.

```typescript
// ✅ CORRECT
const coords = response.route_coordinates;  // [[lon, lat], [lon, lat], ...]

// When passing to Leaflet (common mapping library):
L.polyline(
  coords.map(([lon, lat]) => [lat, lon])  // FLIP to [lat, lon] for Leaflet
);
```

### `markers`: separate `lat`/`lon` fields — Normal Order

The `markers` array uses **normal latitude/longitude order**:

```typescript
// ✅ CORRECT
response.markers.forEach(marker => {
  const { lat, lon, type, label } = marker;
  // lat is latitude, lon is longitude (normal order)
  L.marker([lat, lon]).addTo(map);  // Leaflet expects [lat, lon]
});
```

### Why the difference?

- **`route_coordinates`** comes directly from OSRM (Open Source Routing Machine), which returns GeoJSON-formatted coordinates `[lon, lat]`
- **`markers`** are constructed by the backend API using separate fields, which are in normal geographic order `lat, lon`

**Frontend checklist:**
- ✅ Remember: `route_coordinates` is `[lon, lat]` — flip it for your map library
- ✅ Remember: `markers.lat` and `markers.lon` are normal order — use directly
- ✅ Add comments in your code: "// GeoJSON order from OSRM"
- ✅ Test with real coordinates (Chicago, Dallas) to verify order

---

## Error Handling

### Error Response Format

```typescript
interface ErrorResponse {
  error: string;           // Error category
  detail: string;          // Human-readable message
  status_code: number;     // HTTP status code
}
```

### Common Errors (400 Bad Request)

```typescript
// Invalid location (not found by Nominatim)
{
  "error": "validation_error",
  "detail": "current_location: Address not found (Chicago, XYZ)",
  "status_code": 400
}

// Cycle hours out of range
{
  "error": "validation_error",
  "detail": "cycle_hours_used: Ensure this value is less than or equal to 70.0.",
  "status_code": 400
}

// Missing field
{
  "error": "validation_error",
  "detail": "dropoff_location: This field is required.",
  "status_code": 400
}
```

### Server Errors (500 Internal Server Error)

```typescript
// External API unreachable (OSRM, Nominatim)
{
  "error": "server_error",
  "detail": "An unexpected error occurred. Please try again.",
  "status_code": 500
}
```

### Error Handling in Frontend

```typescript
try {
  const response = await apiClient.post('/plan-route/', formData);
  return response.data;  // Success
} catch (error) {
  if (error.response?.status === 400) {
    // Validation error — show to user
    const detail = error.response.data.detail;
    console.error("Validation failed:", detail);
    // Update UI with error message
  } else if (error.response?.status === 500) {
    // Server error — log and show generic message
    console.error("Server error:", error.response.data.detail);
    // Show "Please try again later"
  } else {
    // Network error or timeout
    console.error("Network error:", error.message);
  }
}
```

---

## Performance Considerations

### Expected Response Times

**Typical:** 2–5 seconds

Breakdown:
- **Nominatim geocoding** (3 addresses): ~1–2 sec per address × 3 = 3–6 sec
- **OSRM routing** (2 route segments): ~1–2 sec per segment = 2–4 sec
- **HOS engine simulation**: <500 ms
- **Total**: 2–5 seconds (dominated by external APIs)

### Optimization Tips

1. **Show loading state immediately** — Users expect slow response
2. **Timeout after 30 seconds** — If backend doesn't respond by then, show error
3. **Don't retry on timeout** — Backend likely already calculated; retrying wastes time
4. **Cache results** — If user submits same trip twice, use local cache
5. **Validate before submit** — Check locations are non-empty before sending to backend

---

## Local Development Setup

For complete step-by-step setup of backend + frontend together, see [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md).

**Quick start (assuming backend running on 8000):**

```bash
cd spotter-eld-logging-app/frontend

# Create .env.local
echo "VITE_API_URL=http://localhost:8000" > .env.local

# Install and run
npm install
npm run dev
```

Frontend will be available at `http://localhost:3000` with automatic proxy to `http://localhost:8000/api/`.

---

## Swagger/OpenAPI Documentation

Interactive API documentation available at:
- **Local:** http://localhost:8000/api/docs/ (Swagger UI)
- **Staging:** https://staging-api.railway.app/api/docs/
- **Production:** https://api.spotter-eld.app/api/docs/ (when available)

The Swagger UI allows you to:
- View the complete OpenAPI spec
- Try requests directly in the browser
- See example request/response bodies
- Understand all validation rules

---

## Related Documentation

- [API Contract](API_CONTRACT.md) — Authoritative request/response schemas
- [Local Development Guide](LOCAL_DEVELOPMENT.md) — Step-by-step setup
- [Architecture](ARCHITECTURE.md) — How the backend works internally
- [OpenAPI Spec](openapi.yaml) — Machine-readable schema
