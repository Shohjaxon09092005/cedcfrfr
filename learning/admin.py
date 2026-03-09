from django.contrib import admin

from .models import StudentCourseProgress, Notification, AIMessage


@admin.register(StudentCourseProgress)
class StudentCourseProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "course", "completed_lessons", "total_lessons", "progress")
    list_filter = ("course",)
    search_fields = ("student__first_name", "student__last_name", "student__email", "course__title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "type", "read", "created_at")
    list_filter = ("type", "read", "created_at")
    search_fields = ("title", "message", "user__email")


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "timestamp")
    list_filter = ("role", "timestamp")
    search_fields = ("content", "user__email")

