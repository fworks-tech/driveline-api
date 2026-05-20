# Testing Quick Start Guide

## Backend Tests (API)

### One-liner to Run Everything
```bash
pytest trips/tests/ -v --cov=trips --cov-report=html && start htmlcov/index.html
```

### Common Commands
```bash
# All tests with coverage
pytest trips/tests/ -v --cov=trips --cov-report=html

# Watch mode (auto-rerun on changes)
pytest trips/tests/ -v --watch

# Specific test
pytest trips/tests/test_integration.py::TestTripPlanningIntegration::test_successful_route_planning_end_to_end -v

# Only integration tests
pytest trips/tests/test_integration.py -v -m integration

# Only unit tests
pytest trips/tests/ -v -m unit

# With detailed output
pytest trips/tests/ -vv -s
```

### Expected Output
```
===== 18 passed in 8.97s =====
Coverage: 87%
```

---

## Frontend Tests (React)

### One-liner to Run E2E Tests
```bash
npm run test:e2e
```

### Common Commands
```bash
# Unit tests (Jest)
npm test

# Unit tests in watch mode
npm test:watch

# Unit tests with coverage
npm run test:coverage

# E2E tests (requires backend on :8000)
npm run test:e2e

# E2E tests interactive UI
npm run test:e2e:ui

# E2E tests debug mode
npm run test:e2e:debug

# Single E2E test
npm run test:e2e -- trip-planning.spec.ts -g "should successfully plan"
```

### Expected Output
```
11 passed (46.0s)
```

---

## Full Stack Testing (Backend + Frontend)

### Terminal 1: Start Backend
```bash
cd spotter-eld-logging-api
python manage.py runserver 0.0.0.0:8000
```

### Terminal 2: Start Frontend Dev Server
```bash
cd spotter-eld-logging-app
npm run dev
```

### Terminal 3: Run E2E Tests
```bash
npm run test:e2e
```

---

## View Test Reports

### Backend Coverage Report
```bash
# Windows
start htmlcov/index.html

# macOS/Linux
open htmlcov/index.html
```

### Frontend E2E Report
```bash
npx playwright show-report
```

---

## CI/CD Status

### Check GitHub Actions
- Backend tests: `.github/workflows/tests.yml`
- Frontend tests: `.github/workflows/e2e-tests.yml`
- View at: https://github.com/fworks-tech/spotter-eld-logging-api/actions
- View at: https://github.com/fworks-tech/spotter-eld-logging-app/actions

---

## Coverage Targets

| Component | Target | Current | Status |
|-----------|--------|---------|--------|
| Backend | 70%+ | 87% | ✅ |
| Frontend E2E | Critical paths | 11 scenarios | ✅ |

---

## Troubleshooting

### Backend: "ModuleNotFoundError"
```bash
# Activate venv and reinstall
venv\Scripts\activate
pip install -r requirements.txt
pytest trips/tests/ -v
```

### Frontend: "Backend not responding"
```bash
# Ensure backend is running
cd spotter-eld-logging-api
python manage.py runserver 0.0.0.0:8000
```

### Frontend: "Timeout waiting for selector"
```bash
# Increase timeout in test:
await expect(element).toBeVisible({ timeout: 15000 })
```

---

## For More Details

- **Backend Testing:** [docs/TESTING.md](docs/TESTING.md)
- **Frontend Testing:** [../spotter-eld-logging-app/docs/TESTING.md](../spotter-eld-logging-app/docs/TESTING.md)
- **Test Report Template:** [docs/TEST_REPORT_TEMPLATE.md](docs/TEST_REPORT_TEMPLATE.md)
- **Summary:** [docs/AUTOMATION_AND_TESTING_SUMMARY.md](docs/AUTOMATION_AND_TESTING_SUMMARY.md)

---

## TL;DR

```bash
# Backend tests
pytest trips/tests/ -v --cov=trips

# Frontend tests  
npm run test:e2e

# Full local stack (3 terminals)
# Terminal 1: python manage.py runserver 0.0.0.0:8000
# Terminal 2: npm run dev
# Terminal 3: npm run test:e2e
```
