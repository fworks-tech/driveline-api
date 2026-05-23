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
- **Reference**
  - [OpenAPI Spec](docs/openapi.yaml) — Machine-readable schema
  - [CHANGELOG](docs/CHANGELOG.md) — Release history
  - [Onboarding Guide](../ONBOARDING.md) — Team onboarding

## Pull Request Automation

When a PR is opened, GitHub Actions automatically:

- **Labels** the PR based on the title prefix (`feat(` → `type/feature`, `fix(` → `type/bug`, etc.)
- **Assigns** the PR to the creator
- **Sets milestone** from the linked issue
- **Sets project board status** to "In Progress"

Override manually with `gh pr edit <number> --add-label "priority/high"` etc.

Required checks before merge: backend tests (70%+ coverage), lint (`black`/`isort`/`flake8`), OpenAPI validation.

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
