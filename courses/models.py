from django.conf import settings
from django.db import models


User = settings.AUTH_USER_MODEL


class Category(models.Model):
    name = models.CharField("Kategoriya nomi", max_length=100, unique=True)
    description = models.TextField("Tavsif", blank=True)
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"

    def __str__(self) -> str:
        return self.name


class Course(models.Model):
    DIFFICULTY_CHOICES = [
        ("beginner", "Boshlang'ich"),
        ("intermediate", "O'rta"),
        ("advanced", "Murakkab"),
    ]

    title = models.CharField("Kurs nomi", max_length=255)
    description = models.TextField("Tavsif")
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="courses",
        verbose_name="Domla",
    )
    thumbnail = models.ImageField("Muqova rasmi", upload_to="course_thumbnails/", blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="courses",
        verbose_name="Kategoriya",
    )
    difficulty = models.CharField("Daraja", max_length=20, choices=DIFFICULTY_CHOICES, default="beginner")
    total_lessons = models.PositiveIntegerField("Darslar soni", default=0)

    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqti", auto_now=True)

    class Meta:
        verbose_name = "Kurs"
        verbose_name_plural = "Kurslar"

    def __str__(self) -> str:
        return self.title


class Resource(models.Model):
    TYPE_CHOICES = [
        ("pdf", "PDF"),
        ("pptx", "PPTX"),
        ("docx", "DOCX"),
        ("video", "Video"),
        ("link", "Havola"),
    ]

    title = models.CharField("Resurs nomi", max_length=255)
    type = models.CharField("Turi", max_length=20, choices=TYPE_CHOICES)
    file = models.FileField("Fayl", upload_to="course_resources/", blank=True, null=True)
    url = models.URLField("URL", blank=True, null=True)
    uploaded_at = models.DateTimeField("Yuklangan vaqti", auto_now_add=True)
    size = models.CharField("Hajmi", max_length=50, blank=True)
    ai_topics = models.JSONField("AI mavzulari", default=list, blank=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="resources",
        verbose_name="Kurs",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="resources",
        verbose_name="Kategoriya",
    )

    class Meta:
        verbose_name = "Resurs"
        verbose_name_plural = "Resurslar"

    def __str__(self) -> str:
        return self.title


class Lesson(models.Model):
    """Dars - Course ichidagi individual dars"""
    title = models.CharField("Dars nomi", max_length=255)
    description = models.TextField("Tavsif", blank=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Kurs",
    )
    order = models.PositiveIntegerField("Tartib", default=1)
    duration = models.PositiveIntegerField("Davomiyligi (minut)", default=30, blank=True)
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqti", auto_now=True)

    class Meta:
        verbose_name = "Dars"
        verbose_name_plural = "Darslar"
        ordering = ["course", "order"]

    def __str__(self) -> str:
        return f"{self.course.title} - {self.title}"


class LessonResource(models.Model):
    """Dars uchun resurs - video, fayl, havola"""
    TYPE_CHOICES = [
        ("video", "Video"),
        ("pdf", "PDF"),
        ("pptx", "PPTX"),
        ("docx", "DOCX"),
        ("link", "Havola"),
    ]

    title = models.CharField("Resurs nomi", max_length=255)
    type = models.CharField("Turi", max_length=20, choices=TYPE_CHOICES)
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="resources",
        verbose_name="Dars",
    )
    file = models.FileField("Fayl", upload_to="lesson_resources/", blank=True, null=True)
    url = models.URLField("URL (Video yoki havola)", blank=True, null=True)
    description = models.TextField("Tavsif", blank=True)
    order = models.PositiveIntegerField("Tartib", default=1)
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    
    # AI Pipeline fields
    transcript = models.TextField("Transkript", blank=True, default="")
    script = models.TextField("Video skript", blank=True, default="")
    audio_url = models.URLField("Audio URL", blank=True, default="")
    processing_status = models.CharField(
        "Qayta ishlash holati",
        max_length=20,
        choices=[
            ("idle", "Kutilmoqda"),
            ("extracting", "Matn ajratilmoqda"),
            ("scripting", "Skript yaratilmoqda"),
            ("audio", "Ovoz yaratilmoqda"),
            ("video", "Video yaratilmoqda"),
            ("quiz", "Test yaratilmoqda"),
            ("ready", "Tayyor"),
            ("failed", "Xato"),
        ],
        default="idle",
    )
    error_message = models.TextField("Xato xabari", blank=True, default="")
    video_url = models.URLField("Video URL", blank=True, default="")
    has_quiz = models.BooleanField("Test mavjud", default=False)

    class Meta:
        verbose_name = "Dars Resurs"
        verbose_name_plural = "Dars Resurslar"
        ordering = ["lesson", "order"]

    def __str__(self) -> str:
        return f"{self.lesson.title} - {self.title}"


class Test(models.Model):
    DIFFICULTY_CHOICES = [
        ("easy", "Oson"),
        ("medium", "O'rta"),
        ("hard", "Qiyin"),
    ]

    title = models.CharField("Test nomi", max_length=255)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="tests",
        verbose_name="Kurs",
    )
    resource = models.ForeignKey(
        "LessonResource",
        on_delete=models.CASCADE,
        related_name="tests",
        verbose_name="Dars Resurs",
        null=True,
        blank=True,
    )
    duration = models.PositiveIntegerField("Davomiyligi (daq)", default=30)
    ai_generated = models.BooleanField("AI tomonidan yaratilgan", default=False)
    difficulty = models.CharField("Daraja", max_length=20, choices=DIFFICULTY_CHOICES, default="easy")

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"

    def __str__(self) -> str:
        return self.title


class Question(models.Model):
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Test",
    )
    text = models.TextField("Savol matni")
    options = models.JSONField("Variantlar", default=list)
    image = models.ImageField(upload_to='questions/images/', null=True, blank=True)
    image_caption = models.CharField(max_length=255, null=True, blank=True)
    image_position = models.CharField(
        max_length=10,
        choices=[('top','Tepada'), ('right','O\'ngda'), ('bottom','Pastda'), ('left','Chapda')],
        default='top',
        blank=True
    )
    correct_answer = models.PositiveIntegerField("To'g'ri javob indeksi")
    explanation = models.TextField("Izoh", blank=True)
    points = models.PositiveIntegerField("Ball", default=1)
    earned_points = models.PositiveIntegerField("Yig'ilgan ball", default=0)

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"

    def __str__(self) -> str:
        return self.text[:50]


class TestResult(models.Model):
    """Talaba tomonidan bajarilgan testning natijasi"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="test_results",
        verbose_name="Talaba",
    )
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="Test",
    )
    score = models.PositiveIntegerField("Olingan ball")
    max_score = models.PositiveIntegerField("Maksimal ball", default=100)
    answers = models.JSONField("Javoblar", default=list)  # List of answer indices
    time_spent = models.PositiveIntegerField("Sarflangan vaqt (sekundlarda)", default=0)
    correct_answers = models.PositiveIntegerField("To'g'ri javoblar soni")
    total_questions = models.PositiveIntegerField("Umumiy savol soni")
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    
    # AI Analysis fields
    weak_topics = models.JSONField("Zaif mavzular", default=list, blank=True)
    ai_feedback = models.TextField("AI tahlili", blank=True, default="")
    recommendations = models.JSONField("Tavsiyalar", default=list, blank=True)
    earned_points = models.PositiveIntegerField("Yig'ilgan ball", default=0)


    class Meta:
        verbose_name = "Test natijasi"
        verbose_name_plural = "Test natijalari"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.student.email} - {self.test.title} ({self.score}%)"


class CourseEnrollment(models.Model):
    """Talaba kursga yozilishi"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Talaba"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Kurs"
    )
    enrolled_at = models.DateTimeField("Yozilgan vaqti", auto_now_add=True)
    progress_percent = models.FloatField("Progress %", default=0)
    
    class Meta:
        verbose_name = "Kurs yozilishi"
        verbose_name_plural = "Kurs yozilishlari"
        unique_together = ["student", "course"]
    
    def __str__(self) -> str:
        return f"{self.student.email} - {self.course.title}"

