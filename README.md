# Spotter AI ELD & Route Planner — Django Backend API

**Backend Repository:** `spotter-eld-logging-api`  
**Frontend Repository:** [`spotter-eld-logging-app`](https://github.com/fworks-tech/spotter-eld-logging-app)

Production-ready Django REST Framework API for the Spotter AI ELD & Route Planner application. Handles geocoding, route planning, and FMCSA Hours of Service (HOS) compliance calculations.

## Technology Stack

- **Framework:** Django 4.2 + Django REST Framework 3.15.1
- **Database:** PostgreSQL (production) / SQLite (development)
- **External APIs:**
  - Nominatim (OpenStreetMap geocoding)
  - OSRM (Open Source Routing Machine)
- **Testing:** pytest, unittest.mock, coverage
- **Deployment:** Railway, Gunicorn

## Quick Start

### Prerequisites

- Python 3.11+
- pip
- PostgreSQL (production) or SQLite (development)

### Installation

```bash
# Clone repo
git clone https://github.com/fworks-tech/spotter-eld-logging-api.git
cd spotter-eld-logging-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

API will be available at `http://localhost:8000`

## API Endpoints

### POST /api/plan-route/

Plan a complete trip with route, fuel stops, and HOS compliance.

**Request:**
```json
{
  "current_location": "Chicago, IL",
  "pickup_location": "Indianapolis, IN",
  "dropoff_location": "Dallas, TX",
  "cycle_hours_used": 30
}
```

**Response:**
```json
{
  "route_coordinates": [[lat, lon], ...],
  "markers": [
    {"type": "start", "lat": 41.88, "lon": -87.63, "label": "Start"},
    {"type": "pickup", "lat": 39.77, "lon": -86.16, "label": "Pickup"},
    ...
  ],
  "logbook_days": [
    {
      "day": 1,
      "events": [
        {"status": "OFF_DUTY", "start_minute": 0, "duration_minutes": 60},
        {"status": "DRIVING", "start_minute": 60, "duration_minutes": 300},
        ...
      ]
    }
  ],
  "trip_summary": {
    "total_distance_miles": 850,
    "total_trip_hours": 13.5,
    "total_drive_hours": 11,
    "fuel_stops": 1,
    "rest_stops": 1,
    "number_of_legs": 3
  }
}
```

## Architecture

### Core Modules

- **trips.views** — API endpoint (PlanRouteView)
- **trips.serializers** — Request/response validation
- **trips.routing** — Geocoding (Nominatim) + routing (OSRM)
- **trips.hos_engine** — FMCSA HOS compliance engine

### FMCSA Rules Implementation

1. **1-Hour On-Duty Rule** — 1-hour on-duty period at pickup/dropoff locations
2. **Fuel Stop Rule** — Mandatory fuel stop every 1,000 miles
3. **11-Hour Driving Limit** — Maximum 11 hours driving per 14-hour window
4. **30-Minute Break Rule** — Mandatory 30-minute break after 8 hours of driving
5. **70-Hour / 8-Day Cycle** — Rolling 70-hour limit across 8 consecutive days

## Configuration

Create `.env` file (use `.env.example` as template):

```bash
DEBUG=False
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/spotter_db
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://spotter-eld.app
```

## Testing

```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test trips
coverage report
coverage html  # Generate HTML report

# Run specific test file
python manage.py test trips.tests.test_hos_engine
```

**Coverage Targets:**
- Unit tests: 70%+
- Integration tests: 60%+

## Deployment

### Local Development

```bash
python manage.py runserver
```

### Production (Railway)

```bash
# Build
pip install gunicorn
pip install -r requirements.txt

# Run
gunicorn spotter.wsgi:application --bind 0.0.0.0:8000
```

**Railway Environment Variables:**
- `DEBUG` → `False`
- `DATABASE_URL` → PostgreSQL connection string
- `DJANGO_SECRET_KEY` → Strong random key
- `CORS_ALLOWED_ORIGINS` → Frontend domain

## Development Workflow

1. **Create feature branch:** `git checkout -b feat/feature-name`
2. **Write tests first** (TDD approach)
3. **Implement feature**
4. **Run tests locally:** `coverage run --source='.' manage.py test trips`
5. **Format code:** `black . && isort .`
6. **Lint:** `flake8 . --exclude migrations/`
7. **Push to GitHub** — CI/CD runs automatically
8. **Create PR** with test results + coverage

## Troubleshooting

### Port Already in Use

```bash
# On Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# On macOS/Linux
lsof -i :8000
kill -9 <PID>
```

### Database Connection Error

- Check `.env` DATABASE_URL
- Ensure PostgreSQL is running (production)
- SQLite should work automatically (development)

### Geocoding Error

- Verify Nominatim API accessibility
- Check address format (city, state/country)
- Nominatim has rate limits: ~1 req/sec recommended

### Routing Error

- Verify OSRM service is accessible
- Check route feasibility (waypoints must be reachable)
- Some routes may timeout (very long distances)

## Contributing

- Follow [Conventional Commits](https://www.conventionalcommits.org/)
- Write tests for new features
- Maintain 70%+ test coverage
- Run linters before pushing
- Create PR with detailed description

## Documentation

- [API Contract](docs/API_CONTRACT.md)
- [HOS Engine Details](docs/HOS_ENGINE.md)
- [Deployment Strategy](../DEVOPS_STRATEGY.md)
- [Onboarding Guide](../ONBOARDING.md)

## License

MIT License - See [LICENSE](LICENSE) file

## Support

- **Issues:** [GitHub Issues](https://github.com/fworks-tech/spotter-eld-logging-api/issues)
- **Email:** support@spotter-eld.app
- **Frontend Repo:** [spotter-eld-logging-app](https://github.com/fworks-tech/spotter-eld-logging-app)
