from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CourseViewSet, ResourceViewSet, TestViewSet, StatisticsViewSet, CategoryViewSet, LessonViewSet, LessonResourceViewSet, TestResultViewSet, CourseEnrollmentViewSet, StudentCourseProgressView

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"lessons", LessonViewSet, basename="lesson")
router.register(r"lesson-resources", LessonResourceViewSet, basename="lesson-resource")
router.register(r"resources", ResourceViewSet, basename="resource")
router.register(r"tests", TestViewSet, basename="test")
router.register(r"test-results", TestResultViewSet, basename="test-result")
router.register(r"enrollments", CourseEnrollmentViewSet, basename="enrollment")
router.register(r"statistics", StatisticsViewSet, basename="statistics")

urlpatterns = [
    path("", include(router.urls)),
    path("student-course-progress/", StudentCourseProgressView.as_view(), name="student-course-progress"),
]

