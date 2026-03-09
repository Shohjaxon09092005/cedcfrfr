from django.urls import path
from . import views

urlpatterns = [
    path("teacher/dashboard/", views.TeacherDashboardView.as_view(), name="teacher-dashboard"),
    path("student/dashboard/", views.StudentDashboardView.as_view(), name="student-dashboard"),
    path("course/<int:course_id>/", views.CourseAnalyticsView.as_view(), name="course-analytics"),
    path("leaderboard/", views.LeaderboardView.as_view(), name="leaderboard"),
]
