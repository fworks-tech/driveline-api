from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import (
    PlanRouteView,
    TokenObtainView,
    TripViewSet,
    UserRegistrationView,
)

router = SimpleRouter()
router.register(r"trips", TripViewSet, basename="trip")

urlpatterns = [
    path("plan-route/", PlanRouteView.as_view(), name="plan-route"),
    path("auth/token/", TokenObtainView.as_view(), name="token-obtain"),
    path("auth/register/", UserRegistrationView.as_view(), name="user-register"),
    path("", include(router.urls)),
]
