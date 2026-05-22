from django.urls import path

from .views import HealthCheckView, PlanRouteView, TokenObtainView, UserRegistrationView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("plan-route/", PlanRouteView.as_view(), name="plan-route"),
    path("auth/token/", TokenObtainView.as_view(), name="token-obtain"),
    path("auth/register/", UserRegistrationView.as_view(), name="user-register"),
]
