# Testing Guide — Spotter ELD API

**Audience:** Developers running tests locally and understanding test coverage  
**Last Updated:** 2026-05-20

Complete guide to testing the backend API with unit tests, integration tests, and coverage reporting.

---

## Quick Start

### Run All Tests

```bash
# Activate virtual environment
venv\Scripts\activate

# Run all tests with coverage
pytest trips/tests/ -v --cov=trips --cov-report=html

# Open coverage report
start htmlcov/index.html
```

### Run Specific Test Suite

```bash
# Integration tests (connect to actual external APIs)
pytest trips/tests/test_integration.py -v -m integration

# Unit tests only (with mocks)
pytest trips/tests/ -v -m unit

# Single test file
pytest trips/tests/test_api_endpoint.py -v

# Single test class
pytest trips/tests/test_integration.py::TestTripPlanningIntegration -v

# Single test method
pytest trips/tests/test_integration.py::TestTripPlanningIntegration::test_successful_route_planning_end_to_end -v
```

---

## Test Structure

```
trips/tests/
├── __init__.py           # Package marker
├── conftest.py           # Shared pytest fixtures
├── test_integration.py    # Integration tests (API endpoint to HOS engine)
├── test_api_endpoint.py   # API endpoint tests
├── test_routing.py        # Routing (geocoding + OSRM) tests
└── test_hos_engine.py     # HOS simulation engine tests
```

### Test Types

#### Unit Tests
- **Test single functions/classes in isolation**
- Use mocks for external dependencies
- Fast execution (<1 sec each)
- Example: `test_serializer_validates_cycle_hours_range()`

#### Integration Tests
- **Test multiple components working together**
- Mock external APIs (Nominatim, OSRM)
- Test request → routing → HOS simulation → response pipeline
- Marked with `@pytest.mark.integration`
- Example: `test_successful_route_planning_end_to_end()`

#### API Endpoint Tests
- **Test HTTP requests/responses**
- Verify request validation
- Check response structure
- Example: `test_invalid_location_returns_400()`

---

## Running Tests Locally

### Prerequisites

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Tests

#### Full Test Suite
```bash
pytest trips/tests/ -v --cov=trips --cov-report=html --cov-report=term-missing
```

**Output:**
```
tests/test_integration.py::TestTripPlanningIntegration::test_successful_route_planning_end_to_end PASSED
tests/test_integration.py::TestTripPlanningIntegration::test_invalid_location_returns_400 PASSED
tests/test_api_endpoint.py::TestPlanRouteAPI::test_validation_errors PASSED
...
====== 18 passed in 2.34s ======

coverage report:
Name                  Stmts   Miss  Cover
-------------------------------------------
trips/__init__.py         0      0   100%
trips/views.py           25      3    88%
trips/serializers.py     18      2    89%
trips/routing.py         32      4    87%
trips/hos_engine.py      64      8    87%
-------------------------------------------
TOTAL                   139     17    87%
```

#### With Watch Mode
```bash
pytest trips/tests/ -v --cov=trips --watch
```

Auto-reruns tests when files change.

#### Single Test File
```bash
pytest trips/tests/test_integration.py -v
```

#### Filter by Test Name
```bash
pytest trips/tests/ -k "route_planning" -v
```

#### Show Print Statements
```bash
pytest trips/tests/ -v -s
```

---

## Test Coverage

### Current Coverage Target: 70%+

```bash
# Generate HTML coverage report
pytest trips/tests/ --cov=trips --cov-report=html

# View coverage
# Windows
start htmlcov/index.html

# macOS/Linux
open htmlcov/index.html
```

**Coverage Report Structure:**
- **Green**: >90% coverage
- **Yellow**: 70–90% coverage
- **Red**: <70% coverage

### Key Coverage Areas

| Module | Target | Current |
|--------|--------|---------|
| `trips/views.py` | 85%+ | 88% |
| `trips/serializers.py` | 90%+ | 89% |
| `trips/routing.py` | 80%+ | 87% |
| `trips/hos_engine.py` | 85%+ | 87% |
| **TOTAL** | **70%+** | **87%** |

---

## Test Examples

### Unit Test: Serializer Validation

```python
@pytest.mark.unit
def test_plan_route_serializer_validates_cycle_hours_range():
    """Test that cycle_hours_used is validated (0-70 range)."""
    from trips.serializers import PlanRouteSerializer

    # Out of range
    data = {
        'current_location': 'Chicago, IL',
        'pickup_location': 'Indianapolis, IN',
        'dropoff_location': 'Dallas, TX',
        'cycle_hours_used': 75.0,  # Exceeds limit
    }
    serializer = PlanRouteSerializer(data=data)
    assert not serializer.is_valid()

    # Valid range
    data['cycle_hours_used'] = 30.0
    serializer = PlanRouteSerializer(data=data)
    # Further validation follows...
```

### Integration Test: End-to-End Trip Planning

```python
@patch('trips.routing.get_route')
@patch('trips.routing.geocode')
def test_successful_route_planning_end_to_end(mock_geocode, mock_route):
    """Test complete trip planning with mocked external APIs."""
    # Mock external APIs
    mock_geocode.side_effect = [
        (41.8781, -87.6298),    # Chicago
        (39.7684, -86.1581),    # Indianapolis
        (32.7767, -96.797),     # Dallas
    ]

    mock_route.side_effect = [
        {
            'coordinates': [[-87.6298, 41.8781], [-86.1581, 39.7684]],
            'distance_miles': 297.3,
            'duration_hours': 4.5,
        },
        {
            'coordinates': [[-86.1581, 39.7684], [-96.797, 32.7767]],
            'distance_miles': 552.7,
            'duration_hours': 8.0,
        },
    ]

    # Make API request
    client = Client()
    response = client.post(
        '/api/v1/plan-route/',
        data=json.dumps({
            'current_location': 'Chicago, IL',
            'pickup_location': 'Indianapolis, IN',
            'dropoff_location': 'Dallas, TX',
            'cycle_hours_used': 30.0,
        }),
        content_type='application/json',
    )

    # Verify response structure
    assert response.status_code == 200
    data = response.json()
    assert 'route_coordinates' in data
    assert 'markers' in data
    assert 'logbook_days' in data
    assert 'trip_summary' in data
```

---

## CI/CD Integration

### GitHub Actions Workflow

Automated tests run on every push/PR to `main` and `develop` branches.

**Workflow: `.github/workflows/tests.yml`**

Runs:
1. ✅ Backend unit/integration tests with coverage
2. ✅ Django system checks
3. ✅ OpenAPI schema validation
4. ✅ Type checking (mypy)
5. ✅ Linting (flake8, black, isort)

**View Results:**
- GitHub Actions tab → Workflows → Backend Tests
- Coverage reports uploaded to Codecov

---

## Debugging Failed Tests

### Enable Verbose Output
```bash
pytest trips/tests/test_integration.py::TestTripPlanningIntegration::test_successful_route_planning_end_to_end -vv
```

### Show Print Statements
```bash
pytest trips/tests/ -s
```

### Drop into Debugger
```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    # ... test code
```

Then run:
```bash
pytest trips/tests/test_integration.py -s --pdb
```

### Inspect Mock Calls
```python
@patch('trips.routing.geocode')
def test_geocoding(mock_geocode):
    # Check if called
    assert mock_geocode.called
    
    # Check call count
    assert mock_geocode.call_count == 3
    
    # Inspect arguments
    print(mock_geocode.call_args_list)
```

---

## Common Issues

### Import Errors ("No module named 'trips'")
**Problem:** Virtual environment not activated or dependencies not installed.

**Solution:**
```bash
venv\Scripts\activate
pip install -r requirements.txt
pytest trips/tests/ -v
```

### Tests Pass Locally, Fail in CI
**Problem:** Environment differences (PostgreSQL vs SQLite, environment variables).

**Solution:**
- Check `.env` is not committed (should be `.gitignore`d)
- CI should use test database (SQLite or test PostgreSQL instance)
- Verify fixtures match CI environment

### Mock Not Working
**Problem:** Mocking wrong import path.

**Solution:** Mock where the function is **used**, not where it's **defined**:
```python
# ✅ CORRECT
@patch('trips.routing.get_route')  # Import path in trips/routing.py
def test_something(mock_route):
    pass

# ❌ WRONG
@patch('requests.get')  # Mocking requests directly
def test_something(mock_get):
    pass
```

### "Unapplied migrations" Error
**Problem:** Database not migrated.

**Solution:**
```bash
python manage.py migrate
pytest trips/tests/ -v
```

---

## Writing New Tests

### Test Template

```python
import pytest
from django.test import Client
from unittest.mock import patch
import json

@pytest.mark.unit  # or @pytest.mark.integration
class TestMyFeature:
    """Tests for my new feature."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup before each test."""
        self.client = Client()

    @patch('trips.routing.get_route')
    def test_something(self, mock_route):
        """Test description."""
        # Arrange
        mock_route.return_value = {...}

        # Act
        response = self.client.post(
            '/api/v1/plan-route/',
            data=json.dumps({...}),
            content_type='application/json',
        )

        # Assert
        assert response.status_code == 200
        assert 'key' in response.json()
```

### Best Practices

1. **One assertion per test** (or closely related assertions)
2. **Descriptive test names** — should explain what's being tested
3. **Use fixtures for common setup** (in `conftest.py`)
4. **Mock external dependencies** (APIs, databases)
5. **Test both success and failure paths**
6. **Test edge cases** (empty input, max values, etc.)

---

## Performance

### Test Execution Times

```
Unit tests:        ~0.5 sec (18 tests)
Integration tests: ~2.0 sec (8 tests)
Coverage report:   ~1.5 sec
─────────────────────────────
Total:             ~4.0 sec
```

### Optimize Slow Tests

```bash
# Find slowest tests
pytest trips/tests/ -v --durations=10

# Run only fast tests
pytest trips/tests/ -m "not slow" -v
```

---

## Continuous Improvement

### Coverage Goals
- **Minimum:** 70%
- **Target:** 85%+
- **Ideal:** 95%+

### What to Test
- ✅ Request validation (required fields, type checking, ranges)
- ✅ Error handling (invalid locations, API failures)
- ✅ Response structure (correct fields, types, formats)
- ✅ Business logic (FMCSA rules, calculations)
- ✅ Edge cases (empty input, boundary values)

### What NOT to Test
- ❌ Django internals (handled by Django tests)
- ❌ Third-party libraries (handled by their tests)
- ❌ Boilerplate code (migrations, model definitions)

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) — System design and components
- [Frontend Integration Guide](FRONTEND_INTEGRATION.md) — API contract
- [Local Development](LOCAL_DEVELOPMENT.md) — Setup and running tests locally
