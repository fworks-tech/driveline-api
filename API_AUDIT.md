# Spotter ELD API Audit

**Date:** 2026-05-21  
**Coverage:** Core API endpoints, security, performance, and code quality

---

## Executive Summary

The Spotter ELD API is a well-architected Django REST framework application with strong error handling, caching, and infrastructure. Key strengths include circuit breakers for external APIs, structured logging, and rate limiting. However, several security and configuration hardening issues require attention before production.

**Risk Level:** Medium (non-critical, but should be addressed)

---

## 1. Security Issues

### 1.1 ⚠️ ALLOWED_HOSTS = ["*"] (Critical in Production)
**File:** `spotter/settings.py:31`  
**Severity:** High  
**Issue:** Accepts requests to any Host header, vulnerable to Host Header Injection attacks.

**Current:**
```python
ALLOWED_HOSTS = ["*"]
```

**Recommendation:**
```python
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
```

**Why:** Prevents attackers from poisoning caches or generating password reset links for arbitrary domains.

---

### 1.2 ⚠️ CSRF Exemptions on Auth Endpoints
**File:** `trips/views.py:254, 298`  
**Severity:** Medium  
**Issue:** `@csrf_exempt` on `TokenObtainView` and `UserRegistrationView` disables CSRF protection.

**Current:**
```python
@method_decorator(csrf_exempt, name="dispatch")
class TokenObtainView(APIView):
    ...

@method_decorator(csrf_exempt, name="dispatch")
class UserRegistrationView(APIView):
```

**Context:** CSRF exemptions are justified for stateless JWT APIs where cookies aren't used for auth. However, this should be documented or removed since JWT doesn't rely on CSRF tokens.

**Recommendation:**
- **Remove the decorators** — DRF APIView already handles CSRF properly for JSON requests
- If keeping them, add comments explaining why (stateless JWT auth doesn't need CSRF)

**Why:** APIView + rest_framework default behavior handles CSRF for both form and JSON payloads; explicit exemption is redundant and confusing.

---

### 1.3 ⚠️ Overly Permissive Error Messages
**File:** `trips/views.py:178, 191, 199`  
**Severity:** Low  
**Issue:** Exception details leaked to clients in error responses.

**Current:**
```python
except ValueError as exc:
    return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

except RequestException as exc:
    return Response({
        "error": "upstream_error",
        "detail": f"External API error: {str(exc)}. Please try again later.",
    }, status=status.HTTP_502_BAD_GATEWAY)

except Exception as exc:
    return Response({
        "error": "internal_error",
        "detail": f"An unexpected error occurred: {str(exc)}",
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**Problem:** Exposes internal implementation details and stack-trace-like info.

**Recommendation:**
```python
except ValueError:
    return Response(
        {"error": "invalid_input", "detail": "Request validation failed."},
        status=status.HTTP_400_BAD_REQUEST
    )

except RequestException:
    return Response({
        "error": "upstream_error",
        "detail": "External service error. Please try again later."
    }, status=status.HTTP_502_BAD_GATEWAY)

except Exception:
    # Log the actual exception server-side (already done in ErrorHandlingMiddleware)
    return Response({
        "error": "internal_error",
        "detail": "An unexpected error occurred. Please try again later."
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

**Why:** Prevents information disclosure; Sentry/logs capture full details server-side.

---

### 1.4 ⚠️ Hardcoded External API URLs
**File:** `trips/routing.py:17-18`  
**Severity:** Low  
**Issue:** Nominatim and OSRM URLs are hardcoded; no fallback or alternative endpoint support.

**Current:**
```python
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
```

**Recommendation:**
```python
NOMINATIM_URL = os.environ.get(
    "NOMINATIM_URL",
    "https://nominatim.openstreetmap.org/search"
)
OSRM_URL = os.environ.get(
    "OSRM_URL",
    "https://router.project-osrm.org/route/v1/driving"
)
```

**Why:** Enables easy switching to self-hosted instances or backups without code changes.

---

## 2. Configuration & Environment

### 2.1 ✅ Good: Conditional Sentry Initialization
**File:** `spotter/settings.py:11-20`  
**Status:** Best practice  
Gracefully skips Sentry when `SENTRY_DSN` is absent. No-op in dev/CI.

---

### 2.2 ✅ Good: Environment-Aware Logging Format
**File:** `spotter/settings.py:159-195`  
**Status:** Best practice  
JSON output in production, human-readable in dev.

---

### 2.3 ⚠️ Missing: DATABASE_URL Fallback
**File:** `spotter/settings.py:109-110`  
**Severity:** Low  
**Issue:** SQLite fallback is fine for dev, but production expects explicit DATABASE_URL.

**Recommendation:** Add validation in settings.py:
```python
if not os.environ.get("DATABASE_URL") and not DEBUG:
    raise ValueError(
        "DATABASE_URL environment variable is required in production (DEBUG=False)"
    )
```

**Why:** Prevents silent failures if production DATABASE_URL is forgotten.

---

## 3. API Design & Contract

### 3.1 ✅ Good: Versioned API Endpoints
**File:** `spotter/urls.py:8`  
All endpoints prefixed with `/api/v1/`. Easy to support v2 later.

---

### 3.2 ✅ Good: Structured Error Responses
**File:** `trips/error_handler.py`  
Consistent error envelope with `error` type, `detail`, and optional `request_id`.

---

### 3.3 ⚠️ Missing: Response Consistency in Auth Endpoints
**File:** `trips/views.py:293`  
**Severity:** Low  
**Issue:** TokenObtain returns 401 for validation errors; should be 400.

**Current:**
```python
if not serializer.is_valid():
    return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
```

**Problem:** 401 means "authentication required"; 400 means "bad request".

**Recommendation:**
```python
if not serializer.is_valid():
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

**Why:** Correct HTTP semantics; clients can distinguish between missing credentials vs. malformed request.

---

### 3.4 ✅ Good: OpenAPI Schema
**File:** `spotter/settings.py:208-214`  
Configured with drf-spectacular. Swagger UI available at `/api/docs/`.

---

## 4. Rate Limiting & Throttling

### 4.1 ✅ Good: Per-Endpoint Rate Limiting
- `PlanRouteThrottle`: 60 req/min
- `AuthThrottle`: 30 req/min
- Health check exempt

**Files:** `trips/throttles.py`, `trips/views.py`

---

### 4.2 ⚠️ Missing: Rate Limit Headers Documentation
**Severity:** Low  
DRF includes `Retry-After` header, but not documented in OpenAPI schema.

**Recommendation:** Add to `@extend_schema` docstrings:
```python
responses={
    429: {
        "description": "Rate limit exceeded",
        "headers": {
            "Retry-After": {
                "schema": {"type": "integer"},
                "description": "Seconds until rate limit resets"
            }
        }
    }
}
```

---

## 5. Caching

### 5.1 ✅ Good: Strategic Cache Keys
**File:** `trips/routing.py:30-38`  
MD5 hash of function args prevents collisions. Cache TTLs:
- Geocoding: 24 hours
- Routes: 48 hours

---

### 5.2 ✅ Good: Cache Backend Flexibility
**File:** `spotter/settings.py:130-140`  
Falls back to in-memory cache if Redis unavailable.

---

## 6. Error Handling

### 6.1 ✅ Good: Circuit Breaker Pattern
**File:** `trips/error_handler.py`  
Protects against cascading failures when Nominatim/OSRM are down.

---

### 6.2 ✅ Good: Structured Logging Integration
**File:** `trips/middleware.py`  
RequestLoggingMiddleware captures method, path, status, elapsed_ms.

---

### 6.3 ⚠️ Missing: Timeout Configuration in Settings
**Severity:** Low  
Timeouts are hardcoded in routing.py (10s geocode, 30s routing).

**Recommendation:**
```python
# spotter/settings.py
API_TIMEOUTS = {
    "NOMINATIM_TIMEOUT": int(os.environ.get("NOMINATIM_TIMEOUT", "10")),
    "OSRM_TIMEOUT": int(os.environ.get("OSRM_TIMEOUT", "30")),
}
```

**Why:** Enables tuning without code changes.

---

## 7. Authentication & Authorization

### 7.1 ✅ Good: JWT-Based Authentication
- Access token lifetime: 1 hour
- Refresh token lifetime: 7 days
- Token rotation enabled

**File:** `spotter/settings.py:197-206`

---

### 7.2 ✅ Good: HS256 Algorithm
HMAC-SHA256 with Django secret key. Sufficient for internal APIs.

---

### 7.3 ⚠️ Consideration: AllowAny on PlanRouteView
**File:** `trips/views.py:38`  
**Context:** Plan route is public (no auth required). This is intentional.

**Recommendation:** Document why in docstring or add comment explaining business requirement.

---

## 8. Input Validation

### 8.1 ✅ Good: Serializer Validation
**File:** `trips/serializers.py`

- Location strings: 2-500 characters
- cycle_hours_used: 0-70 float
- Email validation on registration
- Password min-length: 8 characters

---

### 8.2 ⚠️ Consider: Username/Email Constraints
**File:** `trips/serializers.py:64-78`  
Django User model defaults are used (max 150 chars for username).

**Recommendation:** Make explicit in serializer:
```python
class UserRegistrationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150, min_length=3)
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    email = serializers.EmailField(max_length=254)
```

---

## 9. Logging & Monitoring

### 9.1 ✅ Good: Structured Logging
- JSON output in production
- Request timing captured
- Sentry integration for errors

---

### 9.2 ✅ Good: Error Tracking Graceful Degradation
Sentry DSN is optional; no crashes if missing.

---

### 9.3 ⚠️ Missing: Request ID Propagation
**Severity:** Low  
ErrorHandlingMiddleware generates request_id, but it's not logged in RequestLoggingMiddleware.

**Recommendation:**
```python
class RequestLoggingMiddleware:
    def __call__(self, request: HttpRequest):
        start = time.monotonic()
        response = self.get_response(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)
        
        # Try to get request_id from error handler if set
        request_id = getattr(request, "request_id", None)
        
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "request_id": request_id,  # Add this
            },
        )
        return response
```

---

## 10. Performance

### 10.1 ✅ Good: Caching Strategy
Geocoding and routing results cached aggressively (24-48 hrs).

---

### 10.2 ✅ Good: Async-Ready Architecture
No blocking I/O in views; all external API calls are `requests` library (can be easily wrapped with httpx/aiohttp later).

---

### 10.3 ⚠️ Consider: N+1 Query Prevention
Not currently applicable (no database models in use yet), but be mindful when adding Trip persistence in Issue #8.

---

## 11. CORS & Cross-Origin

### 11.1 ✅ Good: Configurable CORS Origins
**File:** `spotter/settings.py:121-127`  
Respects `CORS_ALLOWED_ORIGINS` env var; defaults to all origins if not set.

---

### 11.2 ⚠️ Production CORS Hardening Needed
**Current (dev):**
```python
CORS_ALLOWED_ORIGINS = [...]  # or empty → allow all
CORS_ALLOW_ALL_ORIGINS = not CORS_ALLOWED_ORIGINS  # Allow all if list empty
```

**Recommendation for production deployment checklist:**
```
[ ] Set CORS_ALLOWED_ORIGINS to frontend domain(s) only
[ ] Ensure CORS_ALLOW_ALL_ORIGINS = False in production
[ ] Test with curl -H "Origin: evil.com" ...
```

---

## Summary Table

| Category | Status | Priority |
|----------|--------|----------|
| **Security** | ⚠️ 3 issues | High |
| **Config** | ✅ Mostly good | Low |
| **API Design** | ✅ Mostly good | Low |
| **Caching** | ✅ Best practice | — |
| **Error Handling** | ✅ Strong | — |
| **Auth** | ✅ Good | — |
| **Input Validation** | ✅ Good | — |
| **Logging** | ✅ Strong + 1 enhancement | Low |
| **Performance** | ✅ Good | — |
| **CORS** | ⚠️ Needs production config | High |

---

## Action Items (Prioritized)

### Immediate (Before Production)
1. **Remove `ALLOWED_HOSTS = ["*"]`** → Use env var with specific hosts
2. **Harden CORS** → Lock `CORS_ALLOWED_ORIGINS` to frontend domain
3. **Review error messages** → Don't expose exception details to clients
4. **Remove CSRF exemptions** → DRF handles it automatically

### Short-Term (v1.2.1 or v1.3.0)
5. Add env vars for external API URLs (Nominatim, OSRM)
6. Add env vars for timeout configuration
7. Fix TokenObtain 401 → 400 for validation errors
8. Add request_id to RequestLoggingMiddleware
9. Add DATABASE_URL validation in production mode

### Documentation
10. Document why PlanRouteView is AllowAny in OpenAPI
11. Document rate limit headers in OpenAPI schema
12. Add production deployment checklist comments

---

## Testing Coverage

**Current:** 95.84% (87 passed, 3 skipped)

### Gaps (All Low Priority)
- ErrorHandlingMiddleware exception paths (lines 51-76 have partial coverage)
- Edge cases in hos_engine (some scenarios skipped)

**Recommendation:** Fine as-is. Test suite is robust. Focus on integration tests for database persistence (#8).

---

## Conclusion

The Spotter ELD API is production-ready with **minor hardening** needed. Core architecture (error handling, caching, rate limiting, logging) is solid. Main action items are configuration (ALLOWED_HOSTS, CORS, env vars) and error message sanitization.

**Estimated effort to production-ready:** 2-3 hours.
