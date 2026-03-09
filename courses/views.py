from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.response import Response
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
