from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    StudentCourseProgressViewSet,
    NotificationViewSet,
    AIMessageViewSet,
    StudentProgressView,
    BadgesView,
)

router = DefaultRouter()
router.register(r"progress", StudentCourseProgressViewSet, basename="progress")
router.register(r"notifications", NotificationViewSet, basename="notification")
router.register(r"ai-messages", AIMessageViewSet, basename="ai-message")

urlpatterns = [
    path("", include(router.urls)),
    path("student-progress/", StudentProgressView.as_view(), name="student-progress"),
    path("badges/", BadgesView.as_view(), name="badges"),
]

