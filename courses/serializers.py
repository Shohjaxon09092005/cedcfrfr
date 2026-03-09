from rest_framework import serializers

from .models import Course, Resource, Test, Question, Category, Lesson, LessonResource, TestResult, CourseEnrollment


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class LessonResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonResource
        fields = [
            "id", "title", "type", "file", "url", "description", "order", "lesson", "created_at",
            "transcript", "script", "audio_url", "processing_status", "error_message",
        ]
        read_only_fields = ["id", "created_at", "transcript", "script", "audio_url", "processing_status", "error_message"]


class LessonSerializer(serializers.ModelSerializer):
    resources = LessonResourceSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "description", "course", "order", "duration", "resources", "created_at"]
        read_only_fields = ["id", "created_at"]


class CourseSerializer(serializers.ModelSerializer):
    instructor_name = serializers.SerializerMethodField()
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False)
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "instructor",
            "instructor_name",
            "thumbnail",
            "category",
            "category_id",
            "difficulty",
            "total_lessons",
            "lessons",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "instructor_name"]

    def get_instructor_name(self, obj) -> str:
        full_name = obj.instructor.get_full_name()
        return full_name or obj.instructor.email


class ResourceSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Resource
        fields = [
            "id",
            "title",
            "type",
            "file",
            "url",
            "uploaded_at",
            "size",
            "ai_topics",
            "course",
            "category",
            "category_id",
        ]
        read_only_fields = ["id", "uploaded_at"]


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "text", "options", "correct_answer", "explanation"]
        read_only_fields = ["id"]


class TestSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)
    course_title = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = [
            "id",
            "title",
            "course",
            "course_title",
            "duration",
            "ai_generated",
            "difficulty",
            "questions",
        ]
        read_only_fields = ["id", "course_title"]

    def get_course_title(self, obj):
        return obj.course.title

    def create(self, validated_data):
        questions_data = validated_data.pop("questions", [])
        test = Test.objects.create(**validated_data)
        for q in questions_data:
            Question.objects.create(test=test, **q)
        return test

    def update(self, instance, validated_data):
        questions_data = validated_data.pop("questions", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if questions_data is not None:
            instance.questions.all().delete()
            for q in questions_data:
                Question.objects.create(test=instance, **q)
        return instance


class TestResultSerializer(serializers.ModelSerializer):
    test_title = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = TestResult
        fields = [
            "id",
            "student",
            "student_name",
            "test",
            "test_title",
            "course_title",
            "score",
            "max_score",
            "answers",
            "time_spent",
            "correct_answers",
            "total_questions",
            "weak_topics",
            "ai_feedback",
            "recommendations",
            "created_at",
        ]
        read_only_fields = ["id", "student", "created_at", "student_name", "test_title", "course_title",
                            "weak_topics", "ai_feedback", "recommendations"]

    def get_test_title(self, obj):
        return obj.test.title

    def get_course_title(self, obj):
        return obj.test.course.title

    def get_student_name(self, obj):
        return obj.student.email


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseEnrollment
        fields = [
            "id",
            "student",
            "student_name",
            "course",
            "course_title",
            "enrolled_at",
            "progress_percent",
        ]
        read_only_fields = ["id", "enrolled_at"]
    
    def get_student_name(self, obj):
        return obj.student.email or obj.student.get_full_name()
    
    def get_course_title(self, obj):
        return obj.course.title
