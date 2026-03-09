from django.conf import settings
from django.db import models

from courses.models import Course, LessonResource

User = settings.AUTH_USER_MODEL


class StudentCourseProgress(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="course_progress",
        verbose_name="Talaba",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="student_progress",
        verbose_name="Kurs",
    )
    completed_lessons = models.PositiveIntegerField("Tugallangan darslar", default=0)
    total_lessons = models.PositiveIntegerField("Jami darslar", default=0)
    progress = models.FloatField("Progres (%)", default=0)

    class Meta:
        verbose_name = "Talaba progressi"
        verbose_name_plural = "Talaba progresslari"
        unique_together = ("student", "course")

    def save(self, *args, **kwargs):
        if self.total_lessons > 0:
            self.progress = min(100.0, (self.completed_lessons / self.total_lessons) * 100)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.student} - {self.course} ({self.progress:.0f}%)"


class Notification(models.Model):
    TYPE_CHOICES = [
        ("info", "Ma'lumot"),
        ("success", "Muvaffaqiyat"),
        ("warning", "Ogohlantirish"),
        ("error", "Xato"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Foydalanuvchi",
    )
    title = models.CharField("Sarlavha", max_length=255)
    message = models.TextField("Xabar")
    type = models.CharField("Turi", max_length=20, choices=TYPE_CHOICES, default="info")
    read = models.BooleanField("O'qilgan", default=False)
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)

    class Meta:
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"

    def __str__(self) -> str:
        return f"{self.title} ({self.get_type_display()})"


class AIMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "Foydalanuvchi"),
        ("assistant", "Yordamchi"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_messages",
        verbose_name="Foydalanuvchi",
    )
    role = models.CharField("Rol", max_length=20, choices=ROLE_CHOICES)
    content = models.TextField("Matn")
    timestamp = models.DateTimeField("Vaqt", auto_now_add=True)
    confidence = models.FloatField("Ishonchlilik", blank=True, null=True)
    sources = models.JSONField("Manbalar", default=list, blank=True)

    class Meta:
        verbose_name = "AI xabari"
        verbose_name_plural = "AI xabarlari"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.user} - {self.get_role_display()}: {self.content[:40]}"


class VideoProgress(models.Model):
    """Talaba video darsni ko'rish progressi"""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="video_progress",
        verbose_name="Talaba"
    )
    lesson_resource = models.ForeignKey(
        LessonResource,
        on_delete=models.CASCADE,
        related_name="student_progress",
        verbose_name="Dars Resurs"
    )
    watched_seconds = models.IntegerField("Ko'rilgan sekundlar", default=0)
    total_seconds = models.IntegerField("Jami sekundlar", default=0)
    completed = models.BooleanField("Tugallangan", default=False)
    last_watched = models.DateTimeField("Oxirgi ko'rilgan vaqti", auto_now=True)
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    
    class Meta:
        verbose_name = "Video progressi"
        verbose_name_plural = "Video progresslari"
        unique_together = ["student", "lesson_resource"]
    
    def __str__(self) -> str:
        return f"{self.student.email} - {self.lesson_resource.title}"