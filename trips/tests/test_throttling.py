import json

from django.core.cache import cache
from django.test import Client, TestCase


class TestPlanRouteThrottling(TestCase):
    """Test rate limiting on plan-route endpoint."""

    def setUp(self):
        """Initialize test client and clear cache."""
        self.client = Client()
        self.endpoint = "/api/v1/plan-route/"
        cache.clear()

    def test_plan_route_allows_60_requests_per_minute(self):
        """Test that 60 requests succeed within the rate limit."""
        for i in range(60):
            response = self.client.post(
                self.endpoint,
                data=json.dumps({}),
                content_type="application/json",
            )
            self.assertNotEqual(
                response.status_code,
                429,
                f"Request {i + 1} was throttled before limit reached",
            )

    def test_plan_route_throttle_triggers_429_on_61st_request(self):
        """Test that 61st request within minute returns 429."""
        for _ in range(60):
            self.client.post(
                self.endpoint,
                data=json.dumps({}),
                content_type="application/json",
            )

        response = self.client.post(
            self.endpoint,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 429)

    def test_plan_route_429_includes_retry_after_header(self):
        """Test that 429 response includes Retry-After header."""
        for _ in range(60):
            self.client.post(
                self.endpoint,
                data=json.dumps({}),
                content_type="application/json",
            )

        response = self.client.post(
            self.endpoint,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertIn("Retry-After", response)
        retry_after = response.get("Retry-After")
        self.assertTrue(int(retry_after) > 0)

    def test_plan_route_429_response_is_json(self):
        """Test that 429 response has expected error format."""
        for _ in range(60):
            self.client.post(
                self.endpoint,
                data=json.dumps({}),
                content_type="application/json",
            )

        response = self.client.post(
            self.endpoint,
            data=json.dumps({}),
            content_type="application/json",
        )
        data = response.json()
        self.assertIn("detail", data)


class TestAuthThrottling(TestCase):
    """Test rate limiting on authentication endpoints."""

    def setUp(self):
        """Initialize test client and clear cache."""
        self.client = Client()
        self.token_endpoint = "/api/v1/auth/token/"
        self.register_endpoint = "/api/v1/auth/register/"
        cache.clear()

    def test_token_endpoint_throttle_configured(self):
        """Test that token endpoint has throttle configured (scope='auth')."""
        from trips.views import TokenObtainView

        self.assertTrue(hasattr(TokenObtainView, "throttle_classes"))
        self.assertTrue(len(TokenObtainView.throttle_classes) > 0)

    def test_register_endpoint_throttle_configured(self):
        """Test that register endpoint has throttle configured (scope='auth')."""
        from trips.views import UserRegistrationView

        self.assertTrue(hasattr(UserRegistrationView, "throttle_classes"))
        self.assertTrue(len(UserRegistrationView.throttle_classes) > 0)

    def test_token_endpoint_returns_429_when_throttled(self):
        """Test that token endpoint returns 429 when rate limit exceeded."""
        throttle_limit = 30
        for _ in range(throttle_limit):
            self.client.post(
                self.token_endpoint,
                data=json.dumps({}),
                content_type="application/json",
            )

        response = self.client.post(
            self.token_endpoint,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 429)

    def test_register_endpoint_returns_429_when_throttled(self):
        """Test that register endpoint returns 429 when rate limit exceeded."""
        throttle_limit = 30
        for _ in range(throttle_limit):
            self.client.post(
                self.register_endpoint,
                data=json.dumps({}),
                content_type="application/json",
            )

        response = self.client.post(
            self.register_endpoint,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 429)


class TestHealthCheckExemptFromThrottling(TestCase):
    """Test that health check is exempt from throttling."""

    def setUp(self):
        """Initialize test client and clear cache."""
        self.client = Client()
        self.health_endpoint = "/health/"
        cache.clear()

    def test_health_check_never_throttled(self):
        """Test that health check endpoint is never throttled."""
        for i in range(100):
            response = self.client.get(self.health_endpoint)
            self.assertEqual(
                response.status_code,
                200,
                f"Health check request {i + 1} returned {response.status_code}",
            )
            self.assertNotEqual(response.status_code, 429)
