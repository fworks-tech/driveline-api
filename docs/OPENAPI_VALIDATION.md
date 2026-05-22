# OpenAPI Validation & Compliance

**Purpose:** Ensure 100% compliance between documented API spec and implementation  
**Status:** ✅ Active  
**Last Updated:** 2026-05-19

---

## Overview

This document describes how OpenAPI spec compliance is validated and enforced in the Spotter AI ELD backend.

### What is OpenAPI Validation?

OpenAPI validation ensures that:
- ✅ Every endpoint in the spec is actually implemented in code
- ✅ Every request/response schema in the spec matches the code
- ✅ No breaking changes are introduced without updating the spec
- ✅ The spec is the single source of truth for the API contract

---

## How Validation Works

### 1. Schema Generation (drf-spectacular)

When code is pushed, `drf-spectacular` automatically generates an OpenAPI schema from your Django code:

```bash
python manage.py spectacular --file schema.json
```

This reads all your DRF views and serializers and generates a complete schema.

### 2. Schema Comparison (validate_openapi.py)

The validation script compares two schemas:

```bash
python scripts/validate_openapi.py docs/openapi.yaml schema.json
```

**Checks performed:**
- ✅ All paths in spec are in generated schema
- ✅ All schemas in spec match generated schemas
- ✅ All required fields match
- ✅ All properties match

### 3. CI/CD Enforcement (.github/workflows/openapi-validation.yml)

On every push and PR to main/develop:
1. Install dependencies
2. Generate schema from code
3. Validate schema format
4. Compare generated vs documented
5. Fail if not compliant

**This is mandatory** — you cannot merge code that breaks the spec.

---

## Workflow: How to Keep Spec Compliant

### Scenario 1: Adding a New Endpoint

**If you add a new endpoint to the code:**

1. Push your code
2. CI generates schema from code
3. CI fails: "Endpoint not found in spec"
4. **Update `docs/openapi.yaml`** with the new endpoint
5. Commit with reference to issue: `Relates to #47`
6. CI passes
7. Merge

```bash
# Example
git add trips/views.py
git commit -m "feat: add new /api/estimate/ endpoint

Implements cost estimation for routes.

Relates to #47"

# You'll see CI fail: "Endpoint /api/estimate/ not in spec"

git add docs/openapi.yaml
git commit -m "docs: add /api/estimate/ to OpenAPI spec

Documents new cost estimation endpoint.

Relates to #47"

# CI passes now
```

### Scenario 2: Changing a Request Schema

**If you modify request validation in a serializer:**

1. Push your code
2. CI generates schema from code
3. CI fails: "Schema mismatch in PlanRouteRequest"
4. **Update `docs/openapi.yaml`** with the new schema
5. Commit: `docs: update PlanRouteRequest schema`
6. CI passes

### Scenario 3: Adding a New Field to Response

**If you add a field to a response serializer:**

1. Push your code
2. CI generates schema from code
3. CI fails: "Missing property in TripSummary"
4. **Update `docs/openapi.yaml`** with the new property
5. Commit with proper references
6. CI passes

---

## Using drf-spectacular

### Configuration (spotter/settings.py)

```python
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": r"/api/",
    "TITLE": "Spotter AI ELD & Route Planner API",
    "DESCRIPTION": "Production REST API...",
    "VERSION": "1.0.0",
}
```

### Generating Schema Locally

```bash
# Generate schema.json
python manage.py spectacular --file schema.json

# View as YAML
python manage.py spectacular --file schema.yaml
```

### Accessing Swagger UI

Once deployed, the Swagger UI is available at:
```
http://localhost:8000/api/docs/
```

This provides interactive API documentation that always matches your code.

---

## Using validate_openapi.py

### Basic Usage

```bash
# Validate that code matches documented spec
python scripts/validate_openapi.py docs/openapi.yaml schema.json
```

### Output

**Success:**
```
✅ OpenAPI spec is compliant!
```

**Failure:**
```
❌ ERRORS:
  - Endpoint not implemented: /api/estimate/
  - Schema {missing property in TripSummary: fuel_price}

❌ Validation failed with 2 error(s)
```

### What It Checks

1. **Endpoints Implemented**
   - Every path in spec must be in generated schema
   - Every method (GET, POST, etc.) must exist

2. **Schemas Match**
   - Every schema in spec must be in generated schema
   - Required fields must match
   - Properties must match

3. **Required Fields**
   - Top-level fields (openapi, info, paths)
   - Info fields (title, version)

---

## Automation Flow

```
Developer pushes code
         ↓
CI triggers openapi-validation.yml
         ↓
Step 1: Install dependencies
         ↓
Step 2: Generate schema from code (drf-spectacular)
         ↓
Step 3: Validate JSON format
         ↓
Step 4: Compare generated vs documented (validate_openapi.py)
         ↓
Step 5a: If mismatch → CI FAILS ❌
         └─ Developer fixes either code or spec
         └─ Updates and pushes again
         └─ CI retries
         
Step 5b: If match → CI PASSES ✅
         └─ Merge allowed
```

---

## Best Practices

### ✅ DO

- Keep `docs/openapi.yaml` up to date with every API change
- Review spec changes in PRs (treat like code changes)
- Use spec as source of truth for frontend integration
- Test examples in spec manually
- Run validation locally before pushing: `python scripts/validate_openapi.py docs/openapi.yaml schema.json`

### ❌ DON'T

- Push code changes without updating spec
- Manually edit spec without matching code
- Ignore CI validation failures
- Add fields to code without documenting them
- Remove endpoints without deprecation

---

## Common Issues

### Issue: "Endpoint not implemented: /api/v1/plan-route/"

**Cause:** Endpoint is in spec but not in code.

**Fix:**
```python
# trips/views.py
class PlanRouteView(APIView):
    def post(self, request):
        ...
```

Then register in `trips/urls.py`:
```python
urlpatterns = [
    path("plan-route/", PlanRouteView.as_view(), name="plan-route"),
]
```

### Issue: "Schema mismatch in TripRequest: missing property pickup_location"

**Cause:** Schema defined in spec but not in serializer.

**Fix:**
```python
# trips/serializers.py
class TripRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField()
    pickup_location = serializers.CharField()  # Add missing field
    dropoff_location = serializers.CharField()
    cycle_hours_used = serializers.IntegerField()
```

### Issue: "Required fields mismatch in TripResponse"

**Cause:** Spec says field is required but code doesn't mark it as required.

**Fix:**
```python
# trips/serializers.py
class TripResponseSerializer(serializers.Serializer):
    route_coordinates = serializers.ListField(required=True)
    markers = serializers.ListField(required=True)
    logbook_days = serializers.ListField(required=True)
    trip_summary = serializers.DictField(required=True)
```

---

## Testing

### Run Validation Tests

```bash
pytest scripts/test_validate_openapi.py -v
```

### Test Cases Covered

- ✅ Endpoints implemented validation
- ✅ Schemas match validation
- ✅ Required fields validation
- ✅ Full validation success path
- ✅ Full validation failure scenarios

---

## Integration with CI/CD

### GitHub Actions Workflow

The workflow `.github/workflows/openapi-validation.yml` runs on:
- Every push to main/develop
- Every PR to main/develop
- Changes to API code, spec, or scripts

### Status Checks

PR must pass before merge:
- ✅ openapi-validation workflow
- ✅ backend-test workflow
- ✅ code review approval

---

## Example: Complete Flow

```bash
# 1. Add new endpoint to code
# vim trips/views.py
git add trips/views.py

# 2. Commit
git commit -m "feat: add estimate endpoint

Calculate shipping cost for routes.

Relates to #47"

# 3. Push
git push origin feat/issue-47-openapi-validation

# 4. CI fails
# ❌ Endpoint /api/estimate/ not in spec

# 5. Update spec
# vim docs/openapi.yaml
git add docs/openapi.yaml

# 6. Commit
git commit -m "docs: add /api/estimate/ endpoint to spec

Documents new cost estimation endpoint.

Relates to #47"

# 7. Push
git push origin feat/issue-47-openapi-validation

# 8. CI passes ✅
# Create PR → Review → Merge
```

---

## References

- **drf-spectacular:** https://drf-spectacular.readthedocs.io/
- **OpenAPI 3.1.0:** https://spec.openapis.org/oas/v3.1.0
- **Validation Script:** `scripts/validate_openapi.py`
- **Workflow:** `.github/workflows/openapi-validation.yml`

---

**Document Status:** ✅ Active  
**Last Updated:** 2026-05-19  
**Maintained by:** Backend team
