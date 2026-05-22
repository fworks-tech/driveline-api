from django.test import Client, TestCase


class TestRequestLoggingMiddleware(TestCase):
    """Test structured HTTP request logging middleware."""

    def setUp(self):
        """Initialize test client."""
        self.client = Client()

    def test_request_is_logged_with_required_fields(self):
        """Test that requests are logged with method, path, status, elapsed_ms."""
        with self.assertLogs("trips.middleware", level="INFO") as log_ctx:
            self.client.get("/health/")

        records = log_ctx.records
        self.assertTrue(
            any(
                hasattr(r, "method")
                and r.method == "GET"
                and hasattr(r, "path")
                and r.path == "/health/"
                and hasattr(r, "status_code")
                and r.status_code == 200
                and hasattr(r, "elapsed_ms")
                for r in records
            ),
            "Request log missing required fields (method, path, status_code, elapsed_ms)",
        )

    def test_elapsed_ms_is_positive_number(self):
        """Test that elapsed_ms is a positive number."""
        with self.assertLogs("trips.middleware", level="INFO") as log_ctx:
            self.client.get("/health/")

        record = next(
            (r for r in log_ctx.records if hasattr(r, "elapsed_ms")),
            None,
        )
        self.assertIsNotNone(record, "No log record with elapsed_ms found")
        self.assertGreaterEqual(record.elapsed_ms, 0)
        self.assertIsInstance(record.elapsed_ms, float)

    def test_404_is_logged_with_correct_status(self):
        """Test that 404 responses are logged with correct status code."""
        with self.assertLogs("trips.middleware", level="INFO") as log_ctx:
            self.client.get("/nonexistent-path/")

        record = next(
            (
                r
                for r in log_ctx.records
                if hasattr(r, "status_code") and r.status_code == 404
            ),
            None,
        )
        self.assertIsNotNone(record, "No 404 log record found")
        self.assertEqual(record.status_code, 404)

    def test_post_request_is_logged(self):
        """Test that POST requests are logged correctly."""
        with self.assertLogs("trips.middleware", level="INFO") as log_ctx:
            self.client.post(
                "/api/auth/register/",
                data="{}",
                content_type="application/json",
            )

        record = next(
            (r for r in log_ctx.records if hasattr(r, "method") and r.method == "POST"),
            None,
        )
        self.assertIsNotNone(record, "No POST log record found")
        self.assertEqual(record.method, "POST")
        self.assertTrue(record.path.startswith("/api"))


class TestSentryIntegration(TestCase):
    """Test Sentry error tracking integration."""

    def test_sentry_init_skipped_without_dsn(self):
        """Test that Sentry initialization gracefully handles missing DSN."""
        import sentry_sdk

        try:
            sentry_sdk.capture_exception(Exception("test"))
        except Exception as e:
            self.fail(f"capture_exception raised unexpectedly without DSN: {e}")

    def test_sentry_doesnt_crash_on_init(self):
        """Test that Sentry is initialized without errors in settings."""
        import sentry_sdk

        client = sentry_sdk.get_client()
        self.assertIsNotNone(client)
