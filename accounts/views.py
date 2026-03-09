from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, extend_schema_view

from .serializers import UserSerializer, RegisterSerializer, LoginSerializer

User = get_user_model()


def _get_tokens_for_user(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@extend_schema(
    summary="Ro'yxatdan o'tish",
    description="Yangi foydalanuvchi ro'yxatdan o'tadi. Rol: admin, instructor (domla), student (talaba).",
    request=RegisterSerializer,
    responses={201: None},
)
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = _get_tokens_for_user(user)
        return Response(
            {
                "message": "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="Kirish",
    description="Email va parol bilan tizimga kirish. JWT access va refresh token qaytariladi.",
    request=LoginSerializer,
    responses={200: None},
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = _get_tokens_for_user(user)
        return Response(
            {
                "message": "Kirish muvaffaqiyatli.",
                "user": UserSerializer(user).data,
                "tokens": tokens,
            }
        )


@extend_schema(
    summary="Joriy foydalanuvchi",
    description="Bearer token orqali kirilgan foydalanuvchi ma'lumotlarini qaytaradi.",
    responses={200: UserSerializer},
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(UserSerializer(request.user).data)


@extend_schema(
    summary="Barcha talabalar ro'yxati",
    description="Tizimda ro'yxatdan o'tgan barcha talabalarni qaytaradi (Admin uchun).",
    responses={200: None},
)
class StudentsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Only admins can see all students
        if getattr(request.user, 'role', None) != 'admin':
            return Response(
                {"detail": "Faqat adminlar barcha talabalarni ko'rishi mumkin"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        students = User.objects.filter(role='student').values(
            'id', 'first_name', 'last_name', 'email', 'level', 'xp', 'date_joined'
        ).order_by('-xp')
        
        students_list = []
        for student in students:
            students_list.append({
                'id': str(student['id']),
                'name': f"{student['first_name']} {student['last_name']}".strip() or student['email'],
                'email': student['email'],
                'level': student['level'],
                'xp': student['xp'],
                'joinedDate': student['date_joined'].isoformat() if student['date_joined'] else None,
            })
        
        return Response(students_list)


@extend_schema(
    summary="Domla uchun talabalar ro'yxati",
    description="Domlaning o'rgatayotgan kurslariga yozilgan talabalarni qaytaradi.",
    responses={200: None},
)
class InstructorStudentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from courses.models import CourseEnrollment, TestResult
        from django.db.models import Avg, Count, Q
        
        # Only instructors can see their students
        if getattr(request.user, 'role', None) != 'instructor':
            return Response(
                {"detail": "Faqat domlar o'z talabalarini ko'rishi mumkin"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get students enrolled in courses taught by this instructor
        students = User.objects.filter(
            role='student',
            courseenrollment__course__instructor=request.user
        ).distinct().values(
            'id', 'first_name', 'last_name', 'email', 'level', 'xp', 'date_joined'
        )
        
        students_list = []
        for student in students:
            student_id = student['id']
            
            # Calculate progress and score from test results
            test_results = TestResult.objects.filter(student_id=student_id)
            avg_score = test_results.aggregate(Avg('score'))['score__avg'] or 0
            tests_count = test_results.count()
            progress = min(int((tests_count / max(tests_count, 5)) * 100), 100)
            
            # Get enrollment info
            enrollments = CourseEnrollment.objects.filter(
                student_id=student_id,
                course__instructor=request.user
            )
            last_enrollment = enrollments.latest('enrolled_at') if enrollments.exists() else None
            
            students_list.append({
                'id': str(student_id),
                'name': f"{student['first_name']} {student['last_name']}".strip() or student['email'],
                'email': student['email'],
                'level': student['level'],
                'xp': student['xp'],
                'progress': progress,
                'score': round(avg_score, 1),
                'testsCount': tests_count,
                'enrolledDate': last_enrollment.enrolled_at.isoformat() if last_enrollment else None,
            })
        
        # Sort by XP descending
        students_list.sort(key=lambda x: x['xp'], reverse=True)
        
        return Response(students_list)


@extend_schema(
    summary="Talabalar statistikasi",
    description="Domla uchun talabalar kesida statistika: jami, faol, faol emas, yuqori o'rtacha.",
    responses={200: None},
)
class StudentStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from courses.models import CourseEnrollment
        from django.utils import timezone
        from datetime import timedelta
        
        # Only instructors can see stats
        if getattr(request.user, 'role', None) != 'instructor':
            return Response(
                {"detail": "Faqat domlar statistikani ko'rishi mumkin"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get students enrolled in courses taught by this instructor
        students = User.objects.filter(
            role='student',
            courseenrollment__course__instructor=request.user
        ).distinct()
        
        total = students.count()
        
        # Check active (enrolled less than 30 days ago or with recent activity)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_students = CourseEnrollment.objects.filter(
            course__instructor=request.user,
            student__in=students
        ).filter(
            Q(enrolled_at__gte=thirty_days_ago) | Q(updated_at__gte=thirty_days_ago)
        ).values_list('student_id', flat=True).distinct().count()
        
        inactive = total - active_students
        
        # Top performers (level >= 5)
        top_performers = students.filter(level__gte=5).count()
        
        return Response({
            'total': total,
            'active': active_students,
            'inactive': inactive,
            'topPerformers': top_performers,
        })

