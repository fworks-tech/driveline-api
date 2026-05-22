# Spotter AI ELD & Route Planner — Django Backend API

**Status:** ✅ **v1.0.0 Released** (May 20, 2026)  
**Backend Repository:** `spotter-eld-logging-api`  
**Frontend Repository:** [`spotter-eld-logging-app`](https://github.com/fworks-tech/spotter-eld-logging-app)

Production-ready Django REST Framework API for the Spotter AI ELD & Route Planner application. Handles geocoding, route planning, and FMCSA Hours of Service (HOS) compliance calculations.

> **v1.0.0 Released:** Core API functionality stable and production-ready. See [CHANGELOG.md](docs/CHANGELOG.md) and [Release Notes](https://github.com/fworks-tech/spotter-eld-logging-api/releases/tag/v1.0.0) for details.

## Quick Start

### Prerequisites
- Docker Desktop or Docker Engine with the Compose plugin
- Node.js 18+ only if you also want to run the frontend

### Backend Setup
```powershell
.\scripts\bootstrap_backend.ps1
```

This copies `.env.example` to `.env` if needed, builds the image, runs migrations, and starts PostgreSQL, Redis, and the Django API.

If you prefer the raw compose command:

```bash
docker compose up --build
```

API available at `http://localhost:8000`  
Swagger UI: `http://localhost:8000/api/docs/`

The backend runs at `http://localhost:8000`, the health check is at `http://localhost:8000/health/`, and PostgreSQL/Redis run as sibling services inside the Compose network.

## Technology Stack

- **Framework:** Django 4.2 + Django REST Framework 3.15.1
- **Database:** PostgreSQL via Docker Compose for local development
- **APIs:** Nominatim (geocoding) + OSRM (routing)
- **Caching:** Redis (optional) with Django's cache framework
- **Testing:** pytest with 87% coverage
- **Deployment:** Railway + Gunicorn

---

## HOS Algorithm Deep-Dive

The **Hours of Service Engine** (`trips/hos_engine.py`) simulates a multi-leg trucking trip while enforcing all FMCSA property-carrying regulations.

### Core Rules Enforced
1. **11-hour driving limit per shift** — Cannot drive > 11 hours before a 10-hr rest
2. **14-hour on-duty window per shift** — Once on-duty starts, clock runs continuously; window cannot reset on breaks
3. **30-minute mandatory break** — Required after 8 cumulative driving hours within a shift
4. **10-hour rest reset** — Off-duty or sleeper-berth time that resets shift counters
5. **70-hour / 8-day rolling cycle** — Cannot accumulate > 70 hours of driving + on-duty in any 8-day period
6. **Fuel stops every 1,000 miles** — 30-minute on-duty stop inserted automatically
7. **Pickup/Dropoff** — 1 hour of on-duty time added at each location

### Segment-by-Segment Simulation

The engine uses a **greedy approach** that drives in the smallest chunks necessary:

1. **Calculate competing caps** for the next chunk:
   - Remaining 11-hour driving limit in shift
   - Remaining 14-hour on-duty window
   - Remaining hours until mandatory 8-hour break needed
   - Remaining cycle hours (70-hr limit)
   - Miles to next fuel stop (converted to hours at avg speed)

2. **Drive the minimum chunk** (smallest of all caps)
3. **Apply post-chunk logic:**
   - If fuel threshold reached → insert 30-min fuel stop
   - If 8 hours driving reached → insert 30-min break
   - If any limit hit → insert 10-hr rest + reset shift counters

4. **Repeat** until all driving complete, then add pickup/dropoff

### Example Walkthrough

Trip: Chicago → Denver → Los Angeles (1,500 mi leg 1, 1,500 mi leg 2, ~50 hrs raw driving)

```
Hour 0:    Start Leg 1 (Denver bound)
Hour 11:   Hit 11-hr driving limit → 10-hr rest (break shifts)
Hour 21:   Resume Leg 1
Hour 29:   Hit 8 driving hrs (in new shift) → 30-min break
Hour 29.5: Resume
Hour 40.5: Fuel stop (1,000 mi reached) → 30-min on-duty
Hour 41:   Resume
Hour 50:   Leg 1 complete, but only 18 driving hrs (< 11 + 8)
Hour 50:   Pickup location → 1 hr on-duty
Hour 51:   Start Leg 2
Hour 62:   Hit 11-hr driving limit → 10-hr rest
Hour 72:   Resume Leg 2
Hour 80:   Hit 8 driving hrs → 30-min break
Hour 80.5: Resume
Hour 91:   Fuel stop (2,000 mi reached) → 30-min
Hour 91.5: Resume
Hour 99:   Leg 2 complete → Dropoff 1 hr on-duty
Hour 100:  Trip complete
```

Results: 3 days, ~47 driving hours, 2 fuel stops, 2 rest periods, trip summary displayed.

### Caveats & Simplifications

- **Rolling 70-hr window:** Currently implemented as a monotonic counter from the provided `cycle_hours_used` seed. Does not subtract hours from days falling off the back of the 8-day window during the trip. For most single-trip use cases this is accurate; for multi-week tracking, a true sliding window would be needed.
- **Average speed calculation:** Uses total distance ÷ total leg hours to estimate fuel stops mid-leg. Actual speed variation not modeled.
- **No individual driver preferences:** Does not account for personal break preferences or scheduled stops beyond fuel/mandatory breaks.

## Architecture

### Request Flow

```
POST /api/v1/plan-route/ (TripCreateSerializer)
    ↓
[Cache Check: hos_simulation_{params_hash}]
    ↓
Geocode 3 locations (Nominatim) → lat/lon coordinates
    ├── [Cache: geocode_{address_hash}] 24 hours
    └── If cached, skip HTTP call
    ↓
Fetch OSRM route (current → pickup → dropoff)
    ├── [Cache: route_{coords_hash}] 48 hours
    └── Get distance, duration, polyline
    ↓
Run HOS Simulation (hos_engine.simulate_trip)
    ├── Enforce all FMCSA rules
    ├── Return logbook_days[] with events
    └── [Cache result] 24 hours
    ↓
Build stop markers (interpolate fuel/rest stops on polyline)
    ↓
Transform logbook (float hours → "HH:MM" format)
    ↓
Save Trip instance (PostgreSQL)
    ↓
Return TripOutputSerializer (route + markers + logbook + summary)
```

### Caching Strategy

Three-layer caching reduces external API calls:

| Layer | Target | TTL | Key Pattern |
|-------|--------|-----|-------------|
| Geocoding | Nominatim results | 24 hours | `geocode_{MD5(address)}` |
| Routing | OSRM route polyline + stats | 48 hours | `route_{MD5(coords)}` |
| HOS Simulation | Full logbook output | 24 hours | `hos_simulation_{MD5(params)}` |

Backend can use Redis (production) or Django's LocMemCache (development). Set `REDIS_URL` in `.env` to enable Redis.

### Circuit Breaker for Upstream APIs

If Nominatim or OSRM fail repeatedly:
- After 5 failures → circuit opens
- Requests fail fast (no retry) for 60 seconds
- Half-open state allows 1 test request
- On success → circuit closes, normal operation resumes

Circuit state stored in cache (shared across Django workers if using Redis).

---

## Documentation

- **Getting Started**
  - [Local Development Setup](docs/LOCAL_DEVELOPMENT.md) — Backend + frontend setup
  - [PR Review Checklist](docs/PR_REVIEW_CHECKLIST.md) — Reviewer guidance for new pull requests
  - [API Contract](docs/API_CONTRACT.md) — Request/response schemas
  - [Deployment Strategy](../DEVOPS_STRATEGY.md) — Production setup

- **Technical Guides**
  - [Architecture](docs/ARCHITECTURE.md) — System design and request flow
  - [HOS Engine Reference](docs/HOS_ENGINE.md) — FMCSA compliance engine
  - [Frontend Integration](docs/FRONTEND_INTEGRATION.md) — API integration guide
  - [Testing Guide](docs/TESTING.md) — Test suites and CI/CD

- **Quality & Validation**
  - [OpenAPI Validation](docs/OPENAPI_VALIDATION.md) — Spec validation in CI/CD
  - [Test Report Template](docs/TEST_REPORT_TEMPLATE.md) — Test metrics

- **Reference**
  - [OpenAPI Spec](docs/openapi.yaml) — Machine-readable schema
  - [CHANGELOG](docs/CHANGELOG.md) — Release history
  - [Onboarding Guide](../ONBOARDING.md) — Team onboarding

## Local Development

### Setup
```powershell
# Bootstrap: builds Docker image, runs migrations, starts Compose services
.\scripts\bootstrap_backend.ps1

# Or raw compose (if .env exists)
docker compose up --build
```

### Services
- **Django API:** `http://localhost:8000`
- **Swagger UI:** `http://localhost:8000/api/docs/`
- **PostgreSQL:** `localhost:5432` (postgres/postgres)
- **Redis:** `localhost:6379`

### Testing & Quality
```bash
# Run all tests with coverage
pytest trips/tests/ -v --cov=trips --cov-report=term-missing

# Run specific test class
pytest trips/tests/test_hos_engine.py::TestHOSEdgeCases -v

# Lint
flake8 trips/

# Type checking
mypy trips/
```

### Environment Variables
Create `.env` at project root:
```
DEBUG=True
SECRET_KEY=dev-key-change-in-production
DATABASE_URL=postgres://postgres:postgres@db:5432/spotter
REDIS_URL=redis://redis:6379/0
OSRM_URL=https://router.project-osrm.org/route/v1/driving
NOMINATIM_URL=https://nominatim.openstreetmap.org/search
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

---

## Production Deployment

### Render / Railway Setup

**Environment Variables (set in deployment platform):**
- `DEBUG=False`
- `SECRET_KEY=<generate-random>`
- `DATABASE_URL=<postgresql-connection-string>`
- `REDIS_URL=<redis-connection-string>`
- `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
- `CORS_ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app`

**Build Command:**
```bash
pip install -r requirements.txt && python manage.py migrate
```

**Start Command:**
```bash
gunicorn spotter.wsgi:application --bind 0.0.0.0:$PORT
```

**Health Check:** `GET /health/` (should return 200 OK)

---

## Contributing

- Follow [Conventional Commits](https://www.conventionalcommits.org/)
- Write tests (maintain 70%+ coverage)
- Run `pytest trips/tests/ -v --cov=trips`
- Create PR with test results

## Support

- **Issues:** [GitHub Issues](https://github.com/fworks-tech/spotter-eld-logging-api/issues)
- **Email:** support@spotter-eld.app
- **Frontend:** [spotter-eld-logging-app](https://github.com/fworks-tech/spotter-eld-logging-app)

## License

MIT License - See [LICENSE](LICENSE) file
