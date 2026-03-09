from django.urls import path

from .views import RegisterView, LoginView, MeView, StudentsListView, InstructorStudentsView, StudentStatsView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("students/", StudentsListView.as_view(), name="students-list"),
    path("instructor-students/", InstructorStudentsView.as_view(), name="instructor-students"),
    path("instructor-students-stats/", StudentStatsView.as_view(), name="instructor-students-stats"),
]

