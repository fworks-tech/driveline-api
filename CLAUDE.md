# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Workflow Standards

### Commits & Pull Requests
- **Commits must be smart, granular, and follow Conventional Commits** — one logical change per commit
- **Branch per GitHub issue** — format: `feat/issue-123-name` or `fix/issue-456-name`
- **One PR per issue** — 1:1:1 mapping (issue → branch → PR)
- **Close issues after merge** — manually verify closure; do not leave follow-up issues open
- **Automated PR Configuration** — Labels, assignee, milestones, and project status are automatically applied when PRs open (see [PR_AUTOMATION.md](docs/PR_AUTOMATION.md))

### Issue Tracking
- GitHub Issues = tickets; always create one before starting work
- Required metadata per issue: milestone (v1.0.0, v1.1.0, etc.) + labels (bug, feature, docs, infra, etc.)

---

## Commands

### Setup
```bash
python -m venv venv
venv\Scripts\activate                 # Windows
source venv/bin/activate              # macOS/Linux

pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

### Development
```bash
python manage.py runserver            # Start dev server
python manage.py shell                # Interactive shell

# API endpoints
http://localhost:8000/api/docs/       # Swagger UI
http://localhost:8000/api/schema/     # OpenAPI JSON
```

### Testing
```bash
# All tests with coverage (must pass 70% threshold)
pytest trips/tests/ -v --cov=trips --cov-report=html

# Open coverage report
start htmlcov/index.html              # Windows
open htmlcov/index.html               # macOS/Linux

# Filtered runs
pytest trips/tests/test_integration.py -v -m integration
pytest trips/tests/ -v -m unit
pytest trips/tests/test_hos_engine.py::test_fuel_stop_insertion -v
```

### Code Quality
```bash
black .
isort .
flake8 . --exclude migrations/ --max-line-length=120
python manage.py check
```

### Database
```bash
python manage.py makemigrations
python manage.py migrate

# Reset (dev only)
python manage.py migrate zero trips
python manage.py migrate
```

---

## Architecture

Single POST endpoint: `POST /api/plan-route/`

Flow: **validate input → geocode 3 locations → get route → HOS simulate → serialize response**

Key modules:
- `trips/views.py` — `PlanRouteView`, orchestrates the pipeline
- `trips/serializers.py` — `TripInputSerializer` (validates), `TripOutputSerializer` (builds response)
- `trips/routing.py` — `geocode()` (Nominatim), `get_route()` (OSRM)
- `trips/hos_engine.py` — `simulate_trip()` enforces FMCSA rules (11h drive, 14h window, 70h cycle, 30-min break after 8h, fuel stops every 1,000 mi)

Full request flow and directory structure: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
FMCSA rules deep dive: [docs/HOS_ENGINE.md](docs/HOS_ENGINE.md)

---

## Testing

Coverage minimum: **70%** (enforced by `pytest.ini`). Current: ~87%.

Test types: unit (mocked, fast), integration (`@pytest.mark.integration`), API endpoint (HTTP validation).

See [docs/TESTING.md](docs/TESTING.md) for patterns, examples, and debugging tips.

---

## Git Hooks

Install once from repo root:
```bash
cp docs/hooks/* .git/hooks/
chmod +x .git/hooks/pre-*
```

**Pre-commit:** runs `black`, `isort`, `flake8`, auto-stages formatted files — aborts on failure.

**Pre-push:** runs `test_api_endpoint.py` + `test_hos_engine.py` — aborts on failure.

Bypass (exceptional cases only): `git commit --no-verify` / `git push --no-verify`

---

## Environment

```bash
# .env.example variables
DEBUG=True
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@host/db
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

External APIs: **Nominatim** (geocoding, ~1 req/sec limit) + **OSRM** (routing).

---

## Dependencies

Key packages: `django 4.2`, `djangorestframework 3.15`, `drf-spectacular 0.27`, `django-cors-headers`, `requests`, `python-dotenv`, `pytest`, `pytest-django`, `pytest-cov`.

Adding a dependency: edit `requirements.txt` → `pip install -r requirements.txt` → commit as `chore(deps): add <package>`.

---

## CI/CD

Workflows in `.github/workflows/`:
- **tests.yml** — push/PR to main/develop; runs pytest + coverage check
- **openapi-validation.yml** — validates OpenAPI spec matches code
- **release.yml** — deployment pipeline (on tag)

PR merge requirements: tests pass (70%+ coverage), OpenAPI spec valid, linting passes, Conventional Commits. See [docs/PR_AUTOMATION.md](docs/PR_AUTOMATION.md).
