# Spotter AI ELD & Route Planner — Django Backend API

**Status:** ✅ **v1.0.0 Released** (May 20, 2026)  
**Backend Repository:** `spotter-eld-logging-api`  
**Frontend Repository:** [`spotter-eld-logging-app`](https://github.com/fworks-tech/spotter-eld-logging-app)

Production-ready Django REST Framework API for the Spotter AI ELD & Route Planner application. Handles geocoding, route planning, and FMCSA Hours of Service (HOS) compliance calculations.

> **v1.0.0 Released:** Core API functionality stable and production-ready. See [CHANGELOG.md](docs/CHANGELOG.md) and [Release Notes](https://github.com/fworks-tech/spotter-eld-logging-api/releases/tag/v1.0.0) for details.

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (production) or SQLite (development)

### Installation
```bash
git clone https://github.com/fworks-tech/spotter-eld-logging-api.git
cd spotter-eld-logging-api

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

API available at `http://localhost:8000`  
Swagger UI: `http://localhost:8000/api/docs/`

### Docker Compose Local Development
```bash
docker compose up --build
```

The backend runs at `http://localhost:8000`, the health check is at `http://localhost:8000/health/`, and PostgreSQL/Redis run as sibling services inside the Compose network.

## Technology Stack

- **Framework:** Django 4.2 + Django REST Framework 3.15.1
- **Database:** PostgreSQL (production) / SQLite (development)
- **APIs:** Nominatim (geocoding) + OSRM (routing)
- **Testing:** pytest with 87% coverage
- **Deployment:** Railway + Gunicorn

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
