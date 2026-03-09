from rest_framework import serializers

from .models import StudentCourseProgress, Notification, AIMessage, VideoProgress


class StudentCourseProgressSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = StudentCourseProgress
        fields = [
            "id",
            "student",
            "course",
            "course_title",
            "completed_lessons",
            "total_lessons",
            "progress",
        ]
        read_only_fields = ["id", "progress"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "user", "title", "message", "type", "read", "created_at"]
        read_only_fields = ["id", "created_at"]


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = ["id", "user", "role", "content", "timestamp", "confidence", "sources"]
        read_only_fields = ["id", "timestamp"]


class VideoProgressSerializer(serializers.ModelSerializer):
    """Video ko'rish progressi serializer"""
    student_email = serializers.CharField(source="student.email", read_only=True)
    lesson_resource_title = serializers.CharField(source="lesson_resource.title", read_only=True)
    progress_percent = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoProgress
        fields = [
            "id",
            "student",
            "student_email",
            "lesson_resource",
            "lesson_resource_title",
            "watched_seconds",
            "total_seconds",
            "progress_percent",
            "completed",
            "last_watched",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "last_watched"]
    
    def get_progress_percent(self, obj):
        if obj.total_seconds > 0:
            return (obj.watched_seconds / obj.total_seconds) * 100
        return 0
