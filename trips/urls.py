from django.urls import path

from .views import HealthCheckView, PlanRouteView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("plan-route/", PlanRouteView.as_view(), name="plan-route"),
]
