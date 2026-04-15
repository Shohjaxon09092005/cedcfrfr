from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Course, Resource, Test, Category, Lesson, LessonResource, TestResult, CourseEnrollment
from .serializers import CourseSerializer, ResourceSerializer, TestSerializer, CategorySerializer, LessonSerializer, LessonResourceSerializer, TestResultSerializer, CourseEnrollmentSerializer

User = get_user_model()


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


@extend_schema_view(
    list=extend_schema(summary="Kategoriyalar ro'yxati", description="Barcha kategoriyalarni olish."),
    create=extend_schema(summary="Kategoriya yaratish", description="Yangi kategoriya qo'shish (admin)."),
    retrieve=extend_schema(summary="Kategoriya detali"),
    update=extend_schema(summary="Kategoriyani yangilash"),
    partial_update=extend_schema(summary="Kategoriyani qisman yangilash"),
    destroy=extend_schema(summary="Kategoriyani o'chirish"),
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema_view(
    list=extend_schema(summary="Kurslar ro'yxati", description="Barcha kurslarni olish yoki filtrlash."),
    create=extend_schema(summary="Kurs yaratish", description="Yangi kurs qo'shish (domla o'zini instructor qilib yozadi)."),
    retrieve=extend_schema(summary="Kurs detali", description="Bitta kurs ma'lumotini olish."),
    update=extend_schema(summary="Kursni yangilash"),
    partial_update=extend_schema(summary="Kursni qisman yangilash"),
    destroy=extend_schema(summary="Kursni o'chirish"),
)
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.prefetch_related("lessons__resources").select_related("instructor").all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    # allow multipart form data so thumbnail files can be uploaded
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        print("======= course create payload =======")
        print(request.data)
        print("FILES:", request.FILES)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Agar foydalanuvchi domla bo'lsa, o'zi instructor sifatida yoziladi
        instructor = self.request.user
        serializer.save(instructor=instructor)


@extend_schema_view(
    list=extend_schema(summary="Darslar ro'yxati", description="Kurs uchun darslar."),
    create=extend_schema(summary="Dars yaratish"),
    retrieve=extend_schema(summary="Dars detali"),
    update=extend_schema(summary="Darsni yangilash"),
    partial_update=extend_schema(summary="Darsni qisman yangilash"),
    destroy=extend_schema(summary="Darsni o'chirish"),
)
class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related("course").prefetch_related("resources").all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter lessons by course if provided"""
        queryset = super().get_queryset()
        course_id = self.request.query_params.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset


@extend_schema_view(
    list=extend_schema(summary="Dars resurslar ro'yxati", description="Dars uchun resurslar."),
    create=extend_schema(summary="Dars resurs yaratish"),
    retrieve=extend_schema(summary="Dars resurs detali"),
    update=extend_schema(summary="Dars resursni yangilash"),
    partial_update=extend_schema(summary="Dars resursni qisman yangilash"),
    destroy=extend_schema(summary="Dars resursni o'chirish"),
)
class LessonResourceViewSet(viewsets.ModelViewSet):
    queryset = LessonResource.objects.select_related("lesson").all()
    serializer_class = LessonResourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """Filter resources by lesson if provided"""
        queryset = super().get_queryset()
        lesson_id = self.request.query_params.get("lesson")
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        return queryset


@extend_schema_view(
    list=extend_schema(summary="Resurslar ro'yxati", description="Kurslar uchun PDF, video, havola va boshqa resurslar."),
    create=extend_schema(summary="Resurs yaratish"),
    retrieve=extend_schema(summary="Resurs detali"),
    update=extend_schema(summary="Resursni yangilash"),
    partial_update=extend_schema(summary="Resursni qisman yangilash"),
    destroy=extend_schema(summary="Resursni o'chirish"),
)
class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.select_related("course").all()
    serializer_class = ResourceSerializer
    permission_classes = [permissions.IsAuthenticated]
    # allow multipart form data so resource files can be uploaded
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def create(self, request, *args, **kwargs):
        print("======= resource create payload =======")
        print(request.data)
        print("FILES:", request.FILES)
        return super().create(request, *args, **kwargs)



@extend_schema_view(
    list=extend_schema(summary="Testlar ro'yxati", description="Kurslar uchun testlar va savollar."),
    create=extend_schema(summary="Test yaratish"),
    retrieve=extend_schema(summary="Test detali"),
    update=extend_schema(summary="Testni yangilash"),
    partial_update=extend_schema(summary="Testni qisman yangilash"),
    destroy=extend_schema(summary="Testni o'chirish"),
)
class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.select_related("course").all()
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # allow filtering by course id
        queryset = super().get_queryset()
        course_id = self.request.query_params.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset


@extend_schema_view(
    list=extend_schema(summary="Test natijalari ro'yxati", description="Talabaning test natijalari."),
    retrieve=extend_schema(summary="Test natijasi detali"),
)
class TestResultViewSet(viewsets.ModelViewSet):
    queryset = TestResult.objects.select_related("student", "test").all()
    serializer_class = TestResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        # Students can only see their own results
        queryset = super().get_queryset()
        if self.request.user.role == 'student':
            queryset = queryset.filter(student=self.request.user)
        return queryset

    def create(self, request, *args, **kwargs):
        """Submit test result"""
        data = request.data
        test_id = data.get('test')
        answers = data.get('answers', [])  # List of answer indices
        time_spent = data.get('time_spent', 0)  # in seconds

        try:
            test = Test.objects.get(id=test_id)
        except Test.DoesNotExist:
            return Response({'error': 'Test topilmadi'}, status=status.HTTP_404_NOT_FOUND)

        # Calculate score
        questions = test.questions.all()
        correct_answers = 0
        for i, answer_idx in enumerate(answers):
            if i < len(questions) and answer_idx == questions[i].correct_answer:
                correct_answers += 1

        score = round((correct_answers / max(len(questions), 1)) * 100) if len(questions) > 0 else 0

        # Create result
        result = TestResult.objects.create(
            student=request.user,
            test=test,
            score=score,
            max_score=100,
            answers=answers,
            time_spent=time_spent,
            correct_answers=correct_answers,
            total_questions=len(questions),
        )

        serializer = self.get_serializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StatisticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Umumiy statistika",
        description="Jami talabalar, kurslar, resurslar, faol foydalanuvchilar va boshqa ko'rsatkichlar.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "totalStudents": {"type": "integer", "description": "Jami talabalar"},
                    "totalCourses": {"type": "integer", "description": "Jami kurslar"},
                    "totalResources": {"type": "integer", "description": "Jami resurslar"},
                    "activeUsers": {"type": "integer", "description": "Faol foydalanuvchilar"},
                    "completionRate": {"type": "number", "description": "Tugatish foizi"},
                    "averageScore": {"type": "number", "description": "O'rtacha ball"},
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def overview(self, request):
        total_students = User.objects.filter(role="student").count()
        total_courses = Course.objects.count()
        total_resources = Resource.objects.count()
        active_users = User.objects.filter(is_active=True).count()

        data = {
            "totalStudents": total_students,
            "totalCourses": total_courses,
            "totalResources": total_resources,
            "activeUsers": active_users,
            "completionRate": 0,
            "averageScore": 0,
        }
        return Response(data)


class StudentCourseProgressView(APIView):
    """
    Talaba kurs bo'yicha detaliy progress ma'lumoti:
    - Qaysi dars bo'yicha ketayotgani
    - Testlar tugatilganligi
    - Kurs tugatilganligi
    - Yutuqlar (achievements)
    
    GET /api/courses/student-course-progress/?student_id=X&course_id=Y
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Q, Count
        
        student_id = request.query_params.get('student_id')
        course_id = request.query_params.get('course_id')
        
        if not student_id or not course_id:
            return Response(
                {"error": "student_id va course_id parametrlari talab qilinadi"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get course enrollment
            enrollment = CourseEnrollment.objects.get(
                student_id=student_id,
                course_id=course_id
            )
        except CourseEnrollment.DoesNotExist:
            return Response(
                {"error": "Talaba bu kursga yozilgan emas"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get course lessons
        lessons = Lesson.objects.filter(course_id=course_id).order_by('order')
        
        lessons_data = []
        for lesson in lessons:
            resources = LessonResource.objects.filter(lesson=lesson)
            
            # Check if all resources in lesson are marked as ready (watched/completed)
            total_resources = resources.count()
            ready_resources = resources.filter(processing_status='ready').count()
            lesson_completed = total_resources > 0 and ready_resources == total_resources
            
            # Get tests for this lesson
            tests = Test.objects.filter(
                questions__related_to_lesson_id=lesson.id
            ).distinct()
            
            tests_data = []
            for test in tests:
                test_results = TestResult.objects.filter(
                    student_id=student_id,
                    test=test
                ).order_by('-created_at')
                
                test_passed = test_results.filter(score__gte=60).exists()
                best_score = test_results.first().score if test_results.exists() else 0
                
                tests_data.append({
                    'id': test.id,
                    'title': test.title,
                    'passed': test_passed,
                    'bestScore': best_score,
                    'totalAttempts': test_results.count(),
                    'completedAt': test_results.first().created_at.isoformat() if test_results.exists() else None,
                })
            
            lessons_data.append({
                'id': lesson.id,
                'title': lesson.title,
                'description': lesson.description,
                'order': lesson.order,
                'resources': {
                    'total': total_resources,
                    'ready': ready_resources,
                },
                'completed': lesson_completed,
                'tests': tests_data,
            })
        
        # Get all course tests (not just lesson-specific)
        course_tests = Test.objects.filter(questions__test=TestResult.objects.filter(test__questions__question_text__isnull=False)).distinct()
        
        # Calculate course completion
        course_tests = Test.objects.all()[:20]  # Get sample tests for now
        completed_tests = TestResult.objects.filter(
            student_id=student_id,
            score__gte=60
        ).values('test').distinct().count()
        
        course_completed = len(lessons_data) > 0 and all(
            lesson['completed'] and len(lesson['tests']) > 0 and all(t['passed'] for t in lesson['tests'])
            for lesson in lessons_data if lesson['tests']
        )
        
        # Calculate overall progress
        overall_progress = 0
        if lessons_data:
            completed_lessons = sum(1 for l in lessons_data if l['completed'])
            overall_progress = int((completed_lessons / len(lessons_data)) * 100)
        
        # Get or create achievements
        achievements = self._generate_achievements(student_id, course_id, enrollment)
        
        return Response({
            'enrollment': {
                'enrolledAt': enrollment.enrolled_at.isoformat(),
                'progressPercent': enrollment.progress_percent,
            },
            'course': {
                'id': enrollment.course.id,
                'title': enrollment.course.title,
                'totalLessons': len(lessons_data),
            },
            'progress': {
                'overallPercent': overall_progress,
                'completed': course_completed,
                'lessonsCompleted': sum(1 for l in lessons_data if l['completed']),
                'testsCompleted': completed_tests,
            },
            'lessons': lessons_data,
            'achievements': achievements,
        })
    
    def _generate_achievements(self, student_id, course_id, enrollment):
        """Generate dynamic achievements based on progress"""
        from datetime import datetime, timedelta
        
        achievements = []
        
        # Achievement 1: Course started
        if enrollment.enrolled_at:
            achievements.append({
                'id': f'course_{course_id}_started',
                'name': 'Kursni boshladi',
                'description': 'Kursga yozilish',
                'icon': '🎓',
                'type': 'course_start',
                'earnedAt': enrollment.enrolled_at.isoformat(),
                'points': 10,
            })
        
        # Achievement 2: First test passed
        test_results = TestResult.objects.filter(
            student_id=student_id,
            test__questions__test__isnull=False
        ).distinct()
        
        if test_results.exists():
            first_test = test_results.order_by('created_at').first()
            if first_test.score >= 60:
                achievements.append({
                    'id': f'course_{course_id}_first_test',
                    'name': 'Birinchi test',
                    'description': 'Birinchi testni topshirdi',
                    'icon': '✅',
                    'type': 'test_passed',
                    'earnedAt': first_test.created_at.isoformat(),
                    'points': 20,
                })
        
        # Achievement 3: High scores (3+ tests with 80%+)
        high_score_tests = test_results.filter(score__gte=80)
        if high_score_tests.count() >= 3:
            achievements.append({
                'id': f'course_{course_id}_high_scores',
                'name': 'Yuqori natija',
                'description': '3 ta testda 80%+ ball oling',
                'icon': '⭐',
                'type': 'high_scores',
                'earnedAt': high_score_tests.order_by('-created_at').first().created_at.isoformat(),
                'points': 50,
            })
        
        return achievements


@extend_schema_view(
    list=extend_schema(summary="Kurs yozilishlari ro'yxati"),
    create=extend_schema(summary="Kursga yozilish"),
    destroy=extend_schema(summary="Kursdan chiqish"),
)
class CourseEnrollmentViewSet(viewsets.ModelViewSet):
    """Course enrollment management viewset"""
    queryset = CourseEnrollment.objects.select_related("student", "course").all()
    serializer_class = CourseEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    
    def get_queryset(self):
        """Filter enrollments based on user role"""
        queryset = super().get_queryset()
        if self.request.user.role == 'student':
            # Students can only see their own enrollments
            queryset = queryset.filter(student=self.request.user)
        elif self.request.user.role == 'instructor':
            # Instructors can see enrollments for their courses
            queryset = queryset.filter(course__instructor=self.request.user)
        return queryset
    
    def perform_create(self, serializer):
        """Enroll student in course"""
        # Check if already enrolled
        course_id = self.request.data.get('course')
        if CourseEnrollment.objects.filter(
            student=self.request.user,
            course_id=course_id
        ).exists():
            raise serializers.ValidationError("Siz already bu kursga yozilgansiz")
        serializer.save(student=self.request.user)
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        """Get all students enrolled in a course"""
        course = Course.objects.get(pk=pk)
        # Check permission
        if request.user.role == 'instructor' and course.instructor != request.user:
            return Response(
                {"error": "Ruxsat yo'q"},
                status=status.HTTP_403_FORBIDDEN
            )
        enrollments = CourseEnrollment.objects.filter(course=course)
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)
