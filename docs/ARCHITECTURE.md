# Backend Architecture — Spotter AI ELD & Route Planner

**Document Purpose:** Source of truth for backend system design  
**Audience:** Developers, architects, AI agents  
**Last Updated:** 2026-05-20

---

## 🏗️ High-Level Architecture

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
│  │ trips/routing.py          │  │ trips/hos_   │  │
│  │ - geocode()               │  │ engine.py    │  │
│  │ - get_route()             │  │ - simulate_  │  │
│  │                           │  │   trip()     │  │
│  └────────────┬──────────────┘  └───────┬──────┘  │
│               │                         │         │
│  ┌────────────▼──────────┐  ┌──────────▼──────┐  │
│  │ Nominatim             │  │ OSRM             │  │
│  │ (Geocoding)           │  │ (Routing)        │  │
│  └───────────────────────┘  └──────────────────┘  │
│                                                    │
│  Database: PostgreSQL (external Railway)         │
└──────────────────────────────────────────────────┘
```

---

## 📦 Directory Structure

```
spotter-eld-logging-api/
├── spotter/
│   ├── __init__.py
│   ├── settings.py              # Django configuration
│   ├── urls.py                  # Root URL routing
│   └── wsgi.py                  # WSGI entry point
│
├── trips/
│   ├── migrations/              # Database schema versions
│   ├── tests/
│   │   ├── test_routing.py      # Geocoding & routing tests
│   │   ├── test_hos_engine.py   # HOS rule validation tests
│   │   └── test_api_endpoint.py # API integration tests
│   │
│   ├── __init__.py
│   ├── admin.py                 # Django admin interface
│   ├── apps.py                  # App configuration
│   ├── models.py                # (Future) Trip persistence
│   ├── views.py                 # API endpoint handler
│   ├── serializers.py           # Request/response validation
│   ├── urls.py                  # Trip routes
│   ├── routing.py               # External API integration
│   └── hos_engine.py            # FMCSA HOS simulation
│
├── manage.py                    # Django CLI
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── README.md                    # API documentation
└── docs/
    ├── ARCHITECTURE.md          # This file
    ├── API_CONTRACT.md          # API contract reference
    ├── HOS_ENGINE.md            # HOS engine reference
    ├── CHANGELOG.md
    ├── openapi.yaml
    └── OPENAPI_VALIDATION.md
```

---

## 🔄 Request Flow Architecture

### POST /api/plan-route/ Flow

```
1. REQUEST RECEIVED (HTTP POST)
   ├─ Content-Type: application/json
   ├─ Body: {current_location, pickup_location, dropoff_location, cycle_hours_used}
   └─ CORS header validation
   ↓
2. DESERIALIZATION & VALIDATION
   ├─ TripInputSerializer.is_valid()
   ├─ Field validation (location strings, cycle_hours 0-70)
   └─ Return 400 if invalid
   ↓
3. GEOCODING (Nominatim API)
   ├─ geocode(current_location) → (lat, lon)
   ├─ geocode(pickup_location) → (lat, lon)
   ├─ geocode(dropoff_location) → (lat, lon)
   └─ Return 400 if address not found
   ↓
4. ROUTE CALCULATION (OSRM API)
   ├─ get_route(current, pickup) → coordinates, distance, duration
   ├─ get_route(pickup, dropoff) → coordinates, distance, duration
   ├─ Combine into polyline coordinates
   └─ Return 400 if route unreachable
   ↓
5. HOS ENGINE SIMULATION
   ├─ hos_engine.simulate_trip()
   ├─ Input: total_distance, cycle_hours_used
   ├─ Apply 5 FMCSA rules
   ├─ Generate logbook days
   ├─ Calculate fuel/rest stops
   └─ Output: PlanRouteResponse
   ↓
6. RESPONSE GENERATION
   ├─ Extract route_coordinates from OSRM
   ├─ Generate markers (start, pickup, dropoff, fuel, rest)
   ├─ Format logbook_days with events
   ├─ Create trip_summary with statistics
   └─ TripSummarySerializer.data
   ↓
7. RESPONSE SENT (HTTP 200)
   ├─ Content-Type: application/json
   ├─ Body: {route_coordinates, markers, logbook_days, trip_summary}
   └─ CORS headers included
```

---

## 📊 Component Architecture

### Application Layers

```
┌─────────────────────────────────────────────┐
│           API Layer (views.py)              │
│         ↓ request, ↓ response                │
├─────────────────────────────────────────────┤
│      Validation Layer (serializers.py)      │
│   Input: TripInputSerializer                │
│   Output: TripSummarySerializer             │
├─────────────────────────────────────────────┤
│     Business Logic Layer (hos_engine.py)    │
│   Core: FMCSA HOS rule simulation           │
├─────────────────────────────────────────────┤
│   Integration Layer (routing.py)            │
│   External: Nominatim, OSRM                 │
├─────────────────────────────────────────────┤
│      Data Layer (models.py - future)        │
│   Persistence: Trip records                 │
└─────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | Responsibility |
|--------|-----------------|
| **views.py** | HTTP request/response handling |
| **serializers.py** | Data validation & transformation |
| **routing.py** | External API integration |
| **hos_engine.py** | HOS rule simulation logic |
| **models.py** | Database models (future) |
| **urls.py** | URL routing |

---

## 🧭 FMCSA HOS Engine Architecture

### Five FMCSA Rules

```
1. ON-DUTY AT PICKUP/DROPOFF
   └─ 1-hour minimum on-duty time at each location
   └─ Status: ON_DUTY_ND (on-duty, not driving)

2. FUEL STOP RULE
   └─ Mandatory fuel stop every 1,000 miles
   └─ Duration: 30 minutes (included in on-duty)
   └─ Status: ON_DUTY_ND (on-duty, not driving)

3. 11-HOUR DRIVING LIMIT
   └─ Maximum 11 hours of driving per 14-hour window
   └─ Must take 10-hour rest after
   └─ Status: DRIVING time is capped

4. 14-HOUR WINDOW
   └─ Maximum 14 hours on-duty + driving per day
   └─ Resets after 10-hour off-duty period
   └─ Status: DRIVING + ON_DUTY_ND counted

5. 30-MINUTE BREAK
   └─ Mandatory 30-minute break after 8 hours driving
   └─ Can be off-duty or sleeper berth
   └─ Status: OFF_DUTY or SLEEPER
```

### HOS Engine Algorithm

```python
# Simplified pseudocode
def simulate_trip(total_miles, cycle_hours_used):
    remaining_miles = total_miles
    remaining_cycle_hours = 70 - cycle_hours_used
    events = []
    
    while remaining_miles > 0:
        # Calculate driving limit for this segment
        max_drive_hours = min(
            11,                          # Rule 3: 11-hour limit
            remaining_cycle_hours,       # Rule 4: 70-hour cycle
            (1000 - miles_since_fuel),   # Rule 2: Fuel every 1000 miles
            (8 - hours_since_break)      # Rule 5: 30-min break after 8 hours
        )
        
        # Drive this segment
        segment_miles = min(
            remaining_miles,
            max_drive_hours * avg_speed  # ~60 mph average
        )
        events.append(DrivingEvent(segment_miles, segment_time))
        
        # Insert breaks/stops as needed
        if hours_since_break >= 8:
            events.append(BreakEvent(30_minutes))
        if miles_since_fuel >= 1000:
            events.append(FuelStopEvent(30_minutes))
        if hours_since_shift >= 11:
            events.append(RestEvent(10_hours))
        
        remaining_miles -= segment_miles
    
    return format_as_logbook_days(events)
```

### Duty Status Enum

```python
class DutyStatus(Enum):
    OFF_DUTY = "OFF_DUTY"           # Not working (sleep, meal, etc)
    SLEEPER = "SLEEPER"             # In sleeper berth
    DRIVING = "DRIVING"             # Actively driving
    ON_DUTY_ND = "ON_DUTY_ND"       # On-duty not driving (pickup, fuel, etc)
```

---

## 🔗 External API Integration

### Nominatim (OpenStreetMap Geocoding)

**Endpoint:** `https://nominatim.openstreetmap.org/search`

**Request:**
```
GET /search?q=Chicago,IL&format=json
```

**Response:**
```json
[
  {
    "lat": "41.8781",
    "lon": "-87.6298",
    "display_name": "Chicago, Illinois, United States"
  }
]
```

**Integration (routing.py):**
```python
def geocode(address: str) -> tuple[float, float] | None:
    """Convert address to coordinates. Returns (lat, lon) or None."""
    response = requests.get(
        'https://nominatim.openstreetmap.org/search',
        params={'q': address, 'format': 'json'},
        timeout=5
    )
    if response.json():
        data = response.json()[0]
        return float(data['lat']), float(data['lon'])
    return None
```

**Error Handling:**
- Address not found → Return None
- Timeout (5 sec) → Return None
- Rate limit → Backoff & retry

### OSRM (Open Source Routing Machine)

**Endpoint:** `https://router.project-osrm.org/route/v1/driving`

**Request:**
```
GET /route/v1/driving/-87.6298,41.8781;-86.1581,39.7684
```

**Response:**
```json
{
  "code": "Ok",
  "routes": [
    {
      "geometry": {
        "coordinates": [[-87.6298, 41.8781], ..., [-86.1581, 39.7684]]
      },
      "distance": 479000,  // meters
      "duration": 17280    // seconds
    }
  ]
}
```

**Integration (routing.py):**
```python
def get_route(origin, waypoint, destination):
    """Get route coordinates and duration."""
    coords = f"{origin[1]},{origin[0]};{waypoint[1]},{waypoint[0]};{destination[1]},{destination[0]}"
    response = requests.get(
        f'https://router.project-osrm.org/route/v1/driving/{coords}',
        timeout=10
    )
    if response.json()['code'] == 'Ok':
        route = response.json()['routes'][0]
        return {
            'coordinates': route['geometry']['coordinates'],
            'distance_miles': route['distance'] / 1609.34,
            'duration_hours': route['duration'] / 3600,
        }
    return None
```

**Caching Strategy:**
- Distance caching (same city pairs)
- Avoid repeated calls for identical routes

---

## ✅ Input Validation

### Serializer Structure

```python
# serializers.py
class TripInputSerializer(serializers.Serializer):
    current_location = serializers.CharField(
        min_length=2,
        max_length=500,
        help_text="Starting location (e.g., Chicago, IL)"
    )
    pickup_location = serializers.CharField(
        min_length=2,
        max_length=500,
        help_text="Pickup location"
    )
    dropoff_location = serializers.CharField(
        min_length=2,
        max_length=500,
        help_text="Dropoff/destination location"
    )
    cycle_hours_used = serializers.FloatField(
        min_value=0.0,
        max_value=70.0,
        help_text="Hours already used in current 8-day cycle (0.0-70.0)"
    )
```

### Validation Rules

| Field | Rule | Example |
|-------|------|---------|
| **current_location** | 2-500 chars | "Chicago, IL" |
| **pickup_location** | 2-500 chars | "Indianapolis, IN" |
| **dropoff_location** | 2-500 chars | "Dallas, TX" |
| **cycle_hours_used** | 0.0-70.0 (float) | 30.5 |

---

## 📤 Response Format

### TripSummarySerializer

```python
class TripSummarySerializer(serializers.Serializer):
    route_coordinates = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text="Route polyline as [lon, lat] pairs (GeoJSON / OSRM order)"
    )
    markers = serializers.ListField(
        child=MarkerSerializer(),
        help_text="Route markers: start, pickup, dropoff, fuel, rest"
    )
    logbook_days = serializers.ListField(
        child=LogbookDaySerializer(),
        help_text="Multi-day logbook breakdown"
    )
    trip_summary = serializers.JSONField(
        help_text="Trip statistics: distance, hours, stops"
    )
```

---

## 🗄️ Database Schema (Future)

### Current State
- ✅ Stateless API (no database required)
- ✅ All calculations ephemeral

### Future Enhancement
```sql
CREATE TABLE trips (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    current_location VARCHAR(255),
    pickup_location VARCHAR(255),
    dropoff_location VARCHAR(255),
    cycle_hours_used INT,
    
    -- Response data
    route_coordinates JSONB,
    markers JSONB,
    logbook_days JSONB,
    trip_summary JSONB,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT cycle_hours_valid CHECK (cycle_hours_used >= 0 AND cycle_hours_used <= 70)
);

CREATE INDEX idx_trips_user_id ON trips(user_id);
CREATE INDEX idx_trips_created_at ON trips(created_at);
```

---

## 🔐 Security Architecture

### CORS Configuration

```python
# settings.py
CORS_ALLOW_ALL_ORIGINS = True  # Development
# Production:
# CORS_ALLOWED_ORIGINS = [
#     "https://spotter-eld.app",
#     "https://staging-spotter.vercel.app"
# ]
```

### Input Validation Defense

```
Layer 1: DRF Serializer (type checking)
    ↓
Layer 2: Validation rules (length, range)
    ↓
Layer 3: External API error handling
    ↓
Layer 4: Response validation
```

### Error Response Format

```json
{
  "error": "error_code",
  "detail": "Human-readable error message",
  "status_code": 400
}
```

---

## 🧪 Testing Strategy

### Test Coverage

| Module | Test File | Coverage |
|--------|-----------|----------|
| **routing.py** | test_routing.py | 90%+ |
| **hos_engine.py** | test_hos_engine.py | 85%+ |
| **views.py** | test_api_endpoint.py | 80%+ |

### Test Execution

```bash
pytest                     # Run all tests
pytest --cov=trips       # With coverage
pytest -k "test_rule"    # Specific tests
pytest -v --tb=short     # Verbose output
```

### Mocking External APIs

```python
# test_routing.py
@patch('trips.routing.requests.get')
def test_geocode_valid_address(self, mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {'lat': '41.8781', 'lon': '-87.6298'}
    ]
    mock_get.return_value = mock_response
    
    result = geocode('Chicago, IL')
    assert result == (41.8781, -87.6298)
```

---

## 🚀 Deployment Architecture

### Development Environment
```
Database: SQLite (db.sqlite3)
API: http://localhost:8000
Server: python manage.py runserver
```

### Production Environment (Railway)
```
Database: PostgreSQL (managed by Railway)
API: https://api.spotter-eld.app
Server: Gunicorn
    gunicorn spotter.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4
```

### Environment Variables

```bash
DEBUG=False                    # Disable debug mode
DJANGO_SECRET_KEY=...         # Random 50+ char key
DATABASE_URL=postgresql://... # Railway postgres
ALLOWED_HOSTS=api.spotter-eld.app,staging-api.railway.app
CORS_ALLOWED_ORIGINS=https://spotter-eld.app,https://staging-spotter.vercel.app
```

---

## 📊 Performance Considerations

### Request-Response Time

| Operation | Time | Limit |
|-----------|------|-------|
| Geocoding × 3 | ~1-2s | 5s timeout |
| Routing × 2 | ~1-2s | 10s timeout |
| HOS simulation | <500ms | Inline |
| Total request | ~2-5s | 30s timeout |

### Optimization

1. **Caching**
   - Geocoding: Same addresses cached (in-memory, per-request)
   - Routing: Same coordinate pairs cached

2. **Parallel Processing** (Future)
   - Geocode 3 locations in parallel
   - Route calculations in parallel

3. **Connection Pooling**
   - Reuse HTTP connections
   - Nominatim & OSRM connection pool

---

## 🔮 Future Enhancements

### Short Term
1. **Database Persistence**
   - Save trip history per user
   - User authentication (JWT)
   - Trip retrieval API

2. **Advanced Caching**
   - Redis cache layer
   - Geocoding result caching
   - Routing cache

3. **Monitoring**
   - Error tracking (Sentry)
   - Performance monitoring (New Relic)
   - API usage analytics

### Long Term
1. **Machine Learning**
   - Driver behavior prediction
   - Optimal rest stop suggestions
   - Real-time traffic integration

2. **Real-Time Updates**
   - WebSocket for live updates
   - Push notifications for delays

3. **Advanced HOS Rules**
   - Personal conveyance time
   - Yard move rules
   - Sleeper berth splits

---

## 📚 References

### Official Docs
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [FMCSA HOS Rules](https://www.fmcsa.dot.gov/regulations/hours-service)

### External APIs
- [Nominatim API](https://nominatim.org/release-docs/latest/api/Overview/)
- [OSRM API](http://project-osrm.org/docs/v5.25.1/api/overview)

### Design Patterns
- Layered architecture (Views → Business Logic → Data)
- Request/Response serialization pattern
- Stateless API design

---

**Architecture Source of Truth:** This document (docs/ARCHITECTURE.md)  
**Last Review:** 2026-05-20  
**Maintained by:** Backend team  
**AI Agent Reference:** ✅ Approved for agent automation
