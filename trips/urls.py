from django.urls import path

from .views import PlanRouteView

urlpatterns = [
    path("plan-route/", PlanRouteView.as_view(), name="plan-route"),
]
