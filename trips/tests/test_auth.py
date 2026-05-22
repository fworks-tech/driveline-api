import json

from django.contrib.auth.models import User
from django.test import Client, TestCase


class TestUserRegistration(TestCase):
    """Tests for POST /api/v1/auth/register/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.endpoint = "/api/v1/auth/register/"  # Root URL includes api/v1/ prefix

    def test_register_new_user_success(self):
        """Test successful user registration."""
        payload = {
            "username": "testdriver",
            "email": "driver@example.com",
            "password": "securepass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["username"], "testdriver")
        self.assertEqual(data["email"], "driver@example.com")
        self.assertIn("id", data)

        # Verify user was created
        user = User.objects.get(username="testdriver")
        self.assertEqual(user.email, "driver@example.com")

    def test_register_duplicate_username(self):
        """Test registration fails with duplicate username."""
        User.objects.create_user(username="duplicate", password="pass123")

        payload = {
            "username": "duplicate",
            "email": "new@example.com",
            "password": "securepass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        errors = response.json()
        self.assertIn("username", errors)

    def test_register_invalid_email(self):
        """Test registration fails with invalid email."""
        payload = {
            "username": "testuser",
            "email": "not-an-email",
            "password": "securepass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_register_short_password(self):
        """Test registration fails with password under 8 characters."""
        payload = {
            "username": "testuser",
            "email": "user@example.com",
            "password": "short",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        errors = response.json()
        self.assertIn("password", errors)

    def test_register_missing_email(self):
        """Test registration fails without email field."""
        payload = {
            "username": "testuser",
            "password": "securepass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        errors = response.json()
        self.assertIn("email", errors)

    def test_register_missing_password(self):
        """Test registration fails without password field."""
        payload = {
            "username": "testuser",
            "email": "user@example.com",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        errors = response.json()
        self.assertIn("password", errors)

    def test_register_response_excludes_password(self):
        """Test that response doesn't include password hash."""
        payload = {
            "username": "testdriver",
            "email": "driver@example.com",
            "password": "securepass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertNotIn("password", data)


class TestTokenObtain(TestCase):
    """Tests for POST /api/v1/auth/token/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.endpoint = "/api/v1/auth/token/"
        # Create a test user
        self.user = User.objects.create_user(
            username="testdriver", email="driver@example.com", password="testpass123"
        )

    def test_obtain_token_success(self):
        """Test successful token acquisition with valid credentials."""
        payload = {
            "username": "testdriver",
            "password": "testpass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)

        # Verify tokens are non-empty strings
        self.assertGreater(len(data["access"]), 0)
        self.assertGreater(len(data["refresh"]), 0)

    def test_obtain_token_includes_user_claims(self):
        """Test that JWT token includes username and email in claims."""
        from rest_framework_simplejwt.tokens import AccessToken

        payload = {
            "username": "testdriver",
            "password": "testpass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Decode the access token to verify claims
        token = AccessToken(data["access"])
        self.assertEqual(token["username"], "testdriver")
        self.assertEqual(token["email"], "driver@example.com")

    def test_obtain_token_invalid_password(self):
        """Test token request fails with wrong password."""
        payload = {
            "username": "testdriver",
            "password": "wrongpassword",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        # Request with invalid credentials is rejected
        self.assertIn(response.status_code, [401, 403])

    def test_obtain_token_nonexistent_user(self):
        """Test token request fails with nonexistent username."""
        payload = {
            "username": "nonexistent",
            "password": "testpass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        # Request with nonexistent user is rejected
        self.assertIn(response.status_code, [401, 403])

    def test_obtain_token_missing_username(self):
        """Test token request fails without username field."""
        payload = {
            "password": "testpass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        errors = response.json()
        self.assertIn("username", errors)

    def test_obtain_token_missing_password(self):
        """Test token request fails without password field."""
        payload = {
            "username": "testdriver",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        errors = response.json()
        self.assertIn("password", errors)

    def test_obtain_token_returns_refresh_token(self):
        """Test that response includes refresh token for token rotation."""
        payload = {
            "username": "testdriver",
            "password": "testpass123",
        }
        response = self.client.post(
            self.endpoint, data=json.dumps(payload), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Verify refresh token is included and different from access token
        self.assertIn("refresh", data)
        self.assertNotEqual(data["access"], data["refresh"])
