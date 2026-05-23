# Backend Architecture — Spotter AI ELD & Route Planner

**Purpose:** Source of truth for backend system design  
**Audience:** Developers, architects  
**Last Updated:** 2026-05-20

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────┐
│              Frontend (React 19)                     │
│         POST /api/plan-route/                        │
└────────────────────┬─────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────┐
│         Django 4.2 REST API Server                   │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │  trips/views.py (PlanRouteView)            │    │
│  │  - Request validation (TripInputSerializer)│    │
│  │  - Response generation                     │    │
│  │  - Error handling                          │    │
│  └────────────────┬───────────────────────────┘    │
│                   │                                │
│  ┌────────────────▼──────────┐  ┌──────────────┐  │
│  │ trips/routing.py          │  │ trips/       │  │
│  │ - geocode()               │  │ hos_engine.py│  │
│  │ - get_route()             │  │ - simulate_  │  │
│  │                           │  │   trip()     │  │
│  └────────────┬──────────────┘  └───────┬──────┘  │
│               │                         │         │
│  ┌────────────▼──────────┐  ┌──────────▼──────┐  │
│  │ Nominatim             │  │ OSRM             │  │
│  │ (Geocoding)           │  │ (Routing)        │  │
│  └───────────────────────┘  └──────────────────┘  │
│                                                    │
│  Database: PostgreSQL (Railway in production)      │
└────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
spotter-eld-logging-api/
├── spotter/
│   ├── settings.py              # Django configuration
│   ├── urls.py                  # Root URL routing
│   └── wsgi.py                  # WSGI entry point
│
├── trips/
│   ├── migrations/              # Database schema versions
│   ├── tests/
│   │   ├── conftest.py          # Shared pytest fixtures
│   │   ├── test_integration.py  # End-to-end flow tests
│   │   ├── test_api_endpoint.py # HTTP request/response tests
│   │   ├── test_routing.py      # Geocoding + OSRM tests
│   │   └── test_hos_engine.py   # HOS rule validation tests
│   ├── views.py                 # API endpoint handler
│   ├── serializers.py           # Request/response validation
│   ├── routing.py               # External API integration
│   ├── hos_engine.py            # FMCSA HOS simulation
│   ├── models.py                # (Future) Trip persistence
│   └── urls.py                  # Trip routes
│
├── manage.py
├── pytest.ini                   # Pytest config (70% coverage required)
├── requirements.txt
├── .env.example
└── docs/
    ├── ARCHITECTURE.md          # This file
    ├── API_CONTRACT.md          # Request/response schemas (canonical)
    ├── HOS_ENGINE.md            # FMCSA rules reference (canonical)
    ├── TESTING.md               # Test patterns and coverage
    ├── PR_AUTOMATION.md         # PR automation + CI/CD workflows
    ├── DEPLOYMENT.md            # Production deployment guide
    ├── CHANGELOG.md             # Release history
    └── openapi.yaml             # Machine-readable API spec
```

---

## Request Flow: POST /api/plan-route/

```
1. REQUEST RECEIVED
   └─ Body: {current_location, pickup_location, dropoff_location, cycle_hours_used}

2. VALIDATION (TripInputSerializer)
   └─ location strings non-empty, cycle_hours_used in [0, 69.5]
   └─ Returns 400 if invalid

3. GEOCODING (Nominatim API × 3)
   └─ geocode(each_location) → (lat, lon)
   └─ Returns 400 if address not found

4. ROUTE CALCULATION (OSRM API × 2)
   └─ get_route(current → pickup) + get_route(pickup → dropoff)
   └─ Returns: coordinates, distance_miles, duration_hours per leg

5. HOS SIMULATION (hos_engine.simulate_trip)
   └─ Enforces 5 FMCSA rules — see docs/HOS_ENGINE.md
   └─ Returns: logbook_days + trip_summary

6. RESPONSE (TripOutputSerializer)
   └─ route_coordinates, markers, logbook_days, trip_summary
   └─ Full schema in docs/API_CONTRACT.md
```

---

## Application Layers

```
┌─────────────────────────────────────────────┐
│           API Layer (views.py)              │
├─────────────────────────────────────────────┤
│      Validation Layer (serializers.py)      │
├─────────────────────────────────────────────┤
│     Business Logic Layer (hos_engine.py)    │
├─────────────────────────────────────────────┤
│   Integration Layer (routing.py)            │
│   External: Nominatim, OSRM                 │
├─────────────────────────────────────────────┤
│      Data Layer (models.py — future)        │
└─────────────────────────────────────────────┘
```

| Module | Responsibility |
|--------|----------------|
| `trips/views.py` | HTTP request/response handling, orchestrates pipeline |
| `trips/serializers.py` | Input validation + output serialization |
| `trips/routing.py` | Nominatim geocoding + OSRM route calculation |
| `trips/hos_engine.py` | FMCSA HOS rule simulation |
| `trips/models.py` | Trip persistence (future) |

---

## External APIs

### Nominatim (Geocoding)

```
GET https://nominatim.openstreetmap.org/search?q=Chicago,IL&format=json
→ [{lat, lon, display_name}]
```

- Rate limit: ~1 req/sec
- Timeout: 5 seconds
- Returns `None` on failure (triggers 400)

### OSRM (Routing)

```
GET https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}
→ {routes: [{geometry: {coordinates: [[lon,lat],...]}, distance, duration}]}
```

- Timeout: 10 seconds
- `distance` in meters → converted to miles; `duration` in seconds → converted to hours
- Returns `None` on failure (triggers 400)

**Coordinate note:** OSRM uses `[lon, lat]` (GeoJSON order). The `route_coordinates` in the response preserves this order. Markers use standard `{lat, lon}` fields.

---

## Input Validation

```python
class TripInputSerializer(serializers.Serializer):
    current_location  = serializers.CharField(min_length=2, max_length=500)
    pickup_location   = serializers.CharField(min_length=2, max_length=500)
    dropoff_location  = serializers.CharField(min_length=2, max_length=500)
    cycle_hours_used  = serializers.FloatField(min_value=0.0, max_value=69.5)
```

---

## Security

- All user input validated via DRF serializers before any processing
- No secrets hardcoded — all config via `.env` (never committed)
- CORS: `CORS_ALLOW_ALL_ORIGINS = True` in dev; explicit whitelist in production
- External API calls have explicit timeouts; errors return generic 400/500 messages
- Django ORM used exclusively (parameterized queries, no SQL injection risk)

---

## Performance

| Operation | Typical time |
|-----------|-------------|
| Geocoding × 3 (sequential) | 3–6 sec |
| Routing × 2 (sequential) | 2–4 sec |
| HOS simulation | <500 ms |
| **Total request** | **2–5 sec** |

Primary bottleneck is external API latency. Future: parallel geocoding via `asyncio.gather`, Redis caching for repeat city pairs.

---

## Future Enhancements

- **Database persistence** — trip history, user auth (JWT), trip retrieval API
- **Redis caching** — geocoding + routing results cached 24h
- **Parallel API calls** — geocode 3 locations simultaneously (est. 3–5× speedup)
- **Rate limiting** — DRF throttle classes (60/hour anon, 1000/hour auth)
- **Advanced HOS** — personal conveyance, sleeper berth splits

---

## References

- [FMCSA HOS Rules](https://www.fmcsa.dot.gov/regulations/hours-service) — regulation source
- [Nominatim API docs](https://nominatim.org/release-docs/latest/api/Overview/)
- [OSRM API docs](http://project-osrm.org/docs/v5.25.1/api/overview)
- [Django REST Framework](https://www.django-rest-framework.org/)
