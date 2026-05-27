# Driveline ELD & Route Planner — Django Backend API

**Status:** v1.6.0 Released (May 2026) | **Frontend:** [driveline-app](https://github.com/fworks-tech/driveline-app)

Production-ready Django REST Framework API handling geocoding, route planning, and FMCSA Hours of Service (HOS) compliance calculations.

## Quick Start

```bash
# Clone and start (Docker required)
git clone https://github.com/fworks-tech/driveline-api.git
cd driveline-api
.\scripts\bootstrap_backend.ps1   # Windows — or: docker compose up --build
```

API: `http://localhost:8000` | Swagger UI: `http://localhost:8000/api/docs/`

For non-Docker local setup or frontend integration, see [CLAUDE.md](CLAUDE.md).

## Tech Stack

- Django 4.2 + Django REST Framework 3.15
- PostgreSQL (Docker Compose locally, Railway in production)
- Nominatim (geocoding) + OSRM (routing)
- pytest — 87% coverage

## Docs Index

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](CLAUDE.md) | Commands, workflow standards, architecture overview |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Request flow, directory structure, component layers |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Request/response schemas, validation rules |
| [docs/HOS_ENGINE.md](docs/HOS_ENGINE.md) | FMCSA rules reference, HOS simulation algorithm |
| [docs/TESTING.md](docs/TESTING.md) | Test patterns, coverage, writing new tests |
| [docs/PR_AUTOMATION.md](docs/PR_AUTOMATION.md) | PR labels/milestones automation + CI/CD workflows |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Railway deployment guide |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Release history |
| [docs/openapi.yaml](docs/openapi.yaml) | Machine-readable OpenAPI spec |

## Troubleshooting

**Docker not starting** — Start Docker Desktop (Windows: ensure Linux engine is active), then re-run `docker compose up --build`.

**Port 8000/5432/6379 in use** — Stop the conflicting service or run `docker compose down -v` to wipe and restart.

**Stale containers** — `docker compose down -v && docker compose up --build`

**Missing `.env`** — `cp .env.example .env` then restart.

**"No module named trips"** (non-Docker) — Activate venv: `venv\Scripts\activate && pip install -r requirements.txt`

**CORS errors** — Add your frontend URL to `CORS_ALLOWED_ORIGINS` in `.env`.

## Contributing

Follow [Conventional Commits](https://www.conventionalcommits.org/), maintain 70%+ test coverage, and open one PR per GitHub issue. See [CLAUDE.md](CLAUDE.md) for full workflow standards.

## License

MIT License — see [LICENSE](LICENSE)
