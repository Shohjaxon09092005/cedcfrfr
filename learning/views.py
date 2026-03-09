from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import StudentCourseProgress, Notification, AIMessage, VideoProgress
from .serializers import (
    StudentCourseProgressSerializer,
    NotificationSerializer,
    AIMessageSerializer,
    VideoProgressSerializer,
)


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if getattr(user, "role", None) == "admin":
            return True
        # obj da user yoki student maydoni bo'lishi mumkin
        owner = getattr(obj, "user", None) or getattr(obj, "student", None)
        return owner == user


@extend_schema_view(
    list=extend_schema(summary="Progress ro'yxati", description="Talaba kurs bo'yicha progress (o'zingiz yoki admin uchun hammasi)."),
    create=extend_schema(summary="Progress yozish"),
    retrieve=extend_schema(summary="Progress detali"),
    update=extend_schema(summary="Progressni yangilash"),
    partial_update=extend_schema(summary="Progressni qisman yangilash"),
    destroy=extend_schema(summary="Progressni o'chirish"),
)
class StudentCourseProgressViewSet(viewsets.ModelViewSet):
    serializer_class = StudentCourseProgressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return StudentCourseProgress.objects.select_related("student", "course").all()
        return StudentCourseProgress.objects.select_related("student", "course").filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


@extend_schema_view(
    list=extend_schema(summary="Bildirishnomalar", description="Foydalanuvchiga tegishli bildirishnomalar."),
    create=extend_schema(summary="Bildirishnoma yaratish"),
    retrieve=extend_schema(summary="Bildirishnoma detali"),
    update=extend_schema(summary="Bildirishnonani yangilash"),
    partial_update=extend_schema(summary="Bildirishnonani qisman yangilash (masalan read=True)"),
    destroy=extend_schema(summary="Bildirishnonani o'chirish"),
)
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return Notification.objects.select_related("user").all()
        return Notification.objects.select_related("user").filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(summary="AI xabarlar", description="AI tutor bilan suhbat tarixi."),
    create=extend_schema(summary="AI xabar yozish"),
    retrieve=extend_schema(summary="AI xabar detali"),
    update=extend_schema(summary="AI xabarni yangilash"),
    partial_update=extend_schema(summary="AI xabarni qisman yangilash"),
    destroy=extend_schema(summary="AI xabarni o'chirish"),
)
class AIMessageViewSet(viewsets.ModelViewSet):
    serializer_class = AIMessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return AIMessage.objects.select_related("user").all()
        return AIMessage.objects.select_related("user").filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(summary="Video ko'rish progressi", description="Talabaning video darsni ko'rish progressi."),
    create=extend_schema(summary="Video progress yozish"),
    retrieve=extend_schema(summary="Video progress detali"),
    update=extend_schema(summary="Video progressni yangilash"),
    partial_update=extend_schema(summary="Video progressni qisman yangilash"),
)
class VideoProgressViewSet(viewsets.ModelViewSet):
    """Video watching progress tracking"""
    serializer_class = VideoProgressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    
    def get_queryset(self):
        user = self.request.user
        if getattr(user, "role", None) == "admin":
            return VideoProgress.objects.select_related("student", "lesson_resource").all()
        return VideoProgress.objects.select_related("student", "lesson_resource").filter(student=user)
    
    def perform_create(self, serializer):
        """Auto-mark completed if watched percentage >= 80%"""
        instance = serializer.save(student=self.request.user)
        if instance.total_seconds > 0:
            progress_percent = (instance.watched_seconds / instance.total_seconds) * 100
            if progress_percent >= 80:
                instance.completed = True
                instance.save(update_fields=['completed'])


class StudentProgressView(APIView):
    """
    GET /api/learning/student-progress/
    Returns: level, xp, xp_to_next_level, total_courses, completed_lessons
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Talaba o'quv progressi")
    def get(self, request):
        from courses.models import TestResult, CourseEnrollment, LessonResource
        from django.db.models import Q
        
        user = request.user
        
        # Calculate XP from test results
        test_results = TestResult.objects.filter(student=user)
        total_xp = 0
        for result in test_results:
            # 10 points per test + score bonus
            total_xp += 10 + (result.score / 10)
        
        # Calculate level
        level = int(total_xp / 500) + 1
        xp_for_level = (level - 1) * 500
        xp_to_next_level = level * 500
        xp_current = total_xp - xp_for_level
        
        # Get course statistics
        enrollments = CourseEnrollment.objects.filter(student=user)
        total_courses = enrollments.count()
        
        # Get completed lessons count
        completed_lessons = LessonResource.objects.filter(
            lesson__course__courseenrollment__student=user,
            processing_status='ready'
        ).count()
        
        return Response({
            "level": level,
            "xp": int(total_xp),
            "xp_to_next_level": xp_to_next_level - xp_for_level,
            "total_courses": total_courses,
            "completed_lessons": completed_lessons,
            "tests_taken": test_results.count(),
            "avg_score": round(sum(r.score for r in test_results) / max(test_results.count(), 1), 1),
        })


class BadgesView(APIView):
    """
    GET /api/learning/badges/
    Returns list of student's earned badges
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Talaba badgelari")
    def get(self, request):
        from courses.models import TestResult
        
        user = request.user
        badges = []
        
        # Badge definitions
        test_results = TestResult.objects.filter(student=user)
        test_count = test_results.count()
        
        # Badge 1: Birinchi qadam (first test)
        if test_count >= 1:
            badges.append({
                "id": "1",
                "name": "Birinchi qadam",
                "description": "Birinchi testni topshiring",
                "icon": "star",
                "tier": "bronze",
                "earnedAt": test_results.first().created_at.isoformat(),
            })
        
        # Badge 2: Test ustasi (90%+ on 3 tests)
        high_score_tests = test_results.filter(score__gte=90)
        if high_score_tests.count() >= 3:
            badges.append({
                "id": "2",
                "name": "Test ustasi",
                "description": "3 ta testdan 90%+ ball oling",
                "icon": "trophy",
                "tier": "gold",
                "earnedAt": high_score_tests[2].created_at.isoformat(),
            })
        
        # Badge 3: Bilim izlovchi (10 tests)
        if test_count >= 10:
            badges.append({
                "id": "3",
                "name": "Bilim izlovchi",
                "description": "10 ta testni topshiring",
                "icon": "book",
                "tier": "silver",
                "earnedAt": test_results[9].created_at.isoformat(),
            })
        
        # Badge 4: Maqsadga erishuvchi (20 tests)
        if test_count >= 20:
            badges.append({
                "id": "4",
                "name": "Maqsadga erishuvchi",
                "description": "20 ta testni yakunlang",
                "icon": "target",
                "tier": "gold",
                "earnedAt": test_results[19].created_at.isoformat(),
            })
        
        return Response(badges)