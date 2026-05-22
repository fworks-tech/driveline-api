import json

from django.contrib.auth.models import User
from django.test import Client, TestCase
from rest_framework_simplejwt.tokens import RefreshToken

from trips.models import Trip


class TestTripListEndpoint(TestCase):
    """Tests for GET /api/trips/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.endpoint = "/api/trips/"
        self.user1 = User.objects.create_user(
            username="driver1", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="driver2", password="testpass123"
        )

        # Create test trips
        self.trip1 = Trip.objects.create(
            user=self.user1,
            current_location="Chicago, IL",
            pickup_location="Denver, CO",
            dropoff_location="Los Angeles, CA",
            cycle_hours_used=20,
            status="completed",
        )
        self.trip2 = Trip.objects.create(
            user=self.user1,
            current_location="New York, NY",
            pickup_location="Miami, FL",
            dropoff_location="Atlanta, GA",
            cycle_hours_used=30,
            status="draft",
        )
        self.trip3 = Trip.objects.create(
            user=self.user2,
            current_location="Seattle, WA",
            pickup_location="Portland, OR",
            dropoff_location="San Francisco, CA",
            cycle_hours_used=15,
            status="completed",
        )

    def test_list_requires_authentication(self):
        """Test that unauthenticated requests to list trips return 401."""
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_list_returns_user_trips_only(self):
        """Test that user sees only their own trips."""
        refresh = RefreshToken.for_user(self.user1)
        access_token = str(refresh.access_token)

        response = self.client.get(
            self.endpoint,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)  # Non-paginated list
        trip_ids = {trip["id"] for trip in data}
        self.assertIn(self.trip1.id, trip_ids)
        self.assertIn(self.trip2.id, trip_ids)
        self.assertNotIn(self.trip3.id, trip_ids)

    def test_list_response_structure(self):
        """Test that list response has correct lightweight fields."""
        refresh = RefreshToken.for_user(self.user1)
        access_token = str(refresh.access_token)

        response = self.client.get(
            self.endpoint,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        trip = data[0]

        # Verify only list fields are included
        self.assertIn("id", trip)
        self.assertIn("current_location", trip)
        self.assertIn("pickup_location", trip)
        self.assertIn("dropoff_location", trip)
        self.assertIn("cycle_hours_used", trip)
        self.assertIn("status", trip)
        self.assertIn("created_at", trip)

        # Verify full data fields are NOT included
        self.assertNotIn("route_coordinates", trip)
        self.assertNotIn("markers", trip)
        self.assertNotIn("logbook_days", trip)
        self.assertNotIn("trip_summary", trip)


class TestTripCreateEndpoint(TestCase):
    """Tests for POST /api/trips/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.endpoint = "/api/trips/"
        self.user = User.objects.create_user(username="driver", password="testpass123")
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)

    def test_create_requires_authentication(self):
        """Test that unauthenticated requests return 401."""
        payload = {
            "current_location": "Chicago, IL",
            "pickup_location": "Denver, CO",
            "dropoff_location": "Los Angeles, CA",
            "cycle_hours_used": 20,
        }
        response = self.client.post(
            self.endpoint,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_create_missing_required_field(self):
        """Test that missing required fields return 400."""
        payload = {
            "current_location": "Chicago, IL",
            "pickup_location": "Denver, CO",
            # missing dropoff_location
            "cycle_hours_used": 20,
        }
        response = self.client.post(
            self.endpoint,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_invalid_cycle_hours(self):
        """Test that cycle_hours > 70 returns 400."""
        payload = {
            "current_location": "Chicago, IL",
            "pickup_location": "Denver, CO",
            "dropoff_location": "Los Angeles, CA",
            "cycle_hours_used": 71,
        }
        response = self.client.post(
            self.endpoint,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_associates_trip_with_user(self):
        """Test that created trip is associated with the authenticated user."""
        payload = {
            "current_location": "Chicago, IL",
            "pickup_location": "Denver, CO",
            "dropoff_location": "Los Angeles, CA",
            "cycle_hours_used": 20,
        }
        response = self.client.post(
            self.endpoint,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )

        self.assertEqual(response.status_code, 201)
        trip = Trip.objects.get(current_location="Chicago, IL")
        self.assertEqual(trip.user, self.user)

    def test_create_returns_full_trip_data(self):
        """Test that create response includes full calculated trip data."""
        payload = {
            "current_location": "Chicago, IL",
            "pickup_location": "Denver, CO",
            "dropoff_location": "Los Angeles, CA",
            "cycle_hours_used": 20,
        }
        response = self.client.post(
            self.endpoint,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()

        # Verify full trip data is included in response
        self.assertIn("id", data)
        self.assertIn("route_coordinates", data)
        self.assertIn("markers", data)
        self.assertIn("logbook_days", data)
        self.assertIn("trip_summary", data)
        self.assertIn("status", data)
        self.assertEqual(data["status"], "completed")


class TestTripRetrieveEndpoint(TestCase):
    """Tests for GET /api/trips/{id}/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="driver1", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="driver2", password="testpass123"
        )

        self.trip = Trip.objects.create(
            user=self.user1,
            current_location="Chicago, IL",
            pickup_location="Denver, CO",
            dropoff_location="Los Angeles, CA",
            cycle_hours_used=20,
            status="completed",
        )
        self.endpoint = f"/api/trips/{self.trip.id}/"

        self.refresh1 = RefreshToken.for_user(self.user1)
        self.access_token1 = str(self.refresh1.access_token)

        self.refresh2 = RefreshToken.for_user(self.user2)
        self.access_token2 = str(self.refresh2.access_token)

    def test_retrieve_requires_authentication(self):
        """Test that unauthenticated requests return 401."""
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_retrieve_own_trip(self):
        """Test that user can retrieve their own trip."""
        response = self.client.get(
            self.endpoint,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token1}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.trip.id)

    def test_retrieve_other_user_trip_forbidden(self):
        """Test that user cannot retrieve another user's trip."""
        response = self.client.get(
            self.endpoint,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token2}",
        )
        self.assertEqual(response.status_code, 404)

    def test_retrieve_nonexistent_trip(self):
        """Test that nonexistent trip returns 404."""
        response = self.client.get(
            "/api/trips/99999/",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token1}",
        )
        self.assertEqual(response.status_code, 404)


class TestTripUpdateEndpoint(TestCase):
    """Tests for PUT /api/trips/{id}/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="driver1", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="driver2", password="testpass123"
        )

        self.trip = Trip.objects.create(
            user=self.user1,
            current_location="Chicago, IL",
            pickup_location="Denver, CO",
            dropoff_location="Los Angeles, CA",
            cycle_hours_used=20,
            status="draft",
        )
        self.endpoint = f"/api/trips/{self.trip.id}/"

        self.refresh1 = RefreshToken.for_user(self.user1)
        self.access_token1 = str(self.refresh1.access_token)

        self.refresh2 = RefreshToken.for_user(self.user2)
        self.access_token2 = str(self.refresh2.access_token)

    def test_update_requires_authentication(self):
        """Test that unauthenticated requests return 401."""
        payload = {"status": "completed"}
        response = self.client.put(
            self.endpoint,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_update_own_trip_status(self):
        """Test that user can update their own trip."""
        payload = {
            "current_location": "Chicago, IL",
            "pickup_location": "Denver, CO",
            "dropoff_location": "Los Angeles, CA",
            "cycle_hours_used": 20,
            "status": "completed",
        }
        response = self.client.put(
            self.endpoint,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token1}",
        )
        self.assertEqual(response.status_code, 200)

        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "completed")

    def test_update_other_user_trip_forbidden(self):
        """Test that user cannot update another user's trip."""
        payload = {"status": "completed"}
        response = self.client.put(
            self.endpoint,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token2}",
        )
        self.assertEqual(response.status_code, 404)


class TestTripDeleteEndpoint(TestCase):
    """Tests for DELETE /api/trips/{id}/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="driver1", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="driver2", password="testpass123"
        )

        self.trip = Trip.objects.create(
            user=self.user1,
            current_location="Chicago, IL",
            pickup_location="Denver, CO",
            dropoff_location="Los Angeles, CA",
            cycle_hours_used=20,
            status="draft",
        )
        self.endpoint = f"/api/trips/{self.trip.id}/"

        self.refresh1 = RefreshToken.for_user(self.user1)
        self.access_token1 = str(self.refresh1.access_token)

        self.refresh2 = RefreshToken.for_user(self.user2)
        self.access_token2 = str(self.refresh2.access_token)

    def test_delete_requires_authentication(self):
        """Test that unauthenticated requests return 401."""
        response = self.client.delete(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_delete_own_trip(self):
        """Test that user can delete (archive) their own trip."""
        response = self.client.delete(
            self.endpoint,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token1}",
        )
        self.assertEqual(response.status_code, 204)

        # Verify trip is archived
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "archived")

    def test_delete_other_user_trip_forbidden(self):
        """Test that user cannot delete another user's trip."""
        response = self.client.delete(
            self.endpoint,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token2}",
        )
        self.assertEqual(response.status_code, 404)

    def test_trip_still_exists_after_delete(self):
        """Test that delete archives trip instead of hard-deleting."""
        self.client.delete(
            self.endpoint,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token1}",
        )

        # Trip should still exist in database (archived)
        self.assertTrue(Trip.objects.filter(id=self.trip.id).exists())
        self.trip.refresh_from_db()
        self.assertEqual(self.trip.status, "archived")


class TestTripPermissions(TestCase):
    """Tests for trip-level permission checks."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="driver1", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="driver2", password="testpass123"
        )

        self.trip = Trip.objects.create(
            user=self.user1,
            current_location="Chicago, IL",
            pickup_location="Denver, CO",
            dropoff_location="Los Angeles, CA",
            cycle_hours_used=20,
        )

        self.refresh1 = RefreshToken.for_user(self.user1)
        self.access_token1 = str(self.refresh1.access_token)

        self.refresh2 = RefreshToken.for_user(self.user2)
        self.access_token2 = str(self.refresh2.access_token)

    def test_user_can_only_list_own_trips(self):
        """Test that user's trip list only includes their trips."""
        response = self.client.get(
            "/api/trips/",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token1}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)

        response = self.client.get(
            "/api/trips/",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token2}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 0)

    def test_user_cannot_access_other_user_trip_endpoints(self):
        """Test that all trip endpoints enforce user isolation."""
        endpoint = f"/api/trips/{self.trip.id}/"

        # Retrieve
        response = self.client.get(
            endpoint,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token2}",
        )
        self.assertEqual(response.status_code, 404)

        # Update
        response = self.client.put(
            endpoint,
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token2}",
        )
        self.assertEqual(response.status_code, 404)

        # Delete
        response = self.client.delete(
            endpoint,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token2}",
        )
        self.assertEqual(response.status_code, 404)
