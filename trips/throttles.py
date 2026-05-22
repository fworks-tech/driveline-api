from rest_framework.throttling import AnonRateThrottle


class PlanRouteThrottle(AnonRateThrottle):
    """Rate limit for plan-route endpoint (per IP, 60 req/min)."""

    scope = "plan_route"


class AuthThrottle(AnonRateThrottle):
    """Rate limit for authentication endpoints (per IP, 10 req/min)."""

    scope = "auth"
