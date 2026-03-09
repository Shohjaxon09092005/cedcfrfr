from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class Organization(models.Model):
    """Multi-tenant SaaS organization model"""
    PLAN_CHOICES = [
        ("basic", "Basic"),
        ("pro", "Pro"),
        ("enterprise", "Enterprise"),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField("Tashkilot nomi", max_length=255)
    plan = models.CharField("Tarif rejasi", max_length=20, choices=PLAN_CHOICES, default="basic")
    max_students = models.IntegerField("Maksimal talabalar", default=50)
    max_videos_per_month = models.IntegerField("Oy uchun maksimal videolar", default=20)
    stripe_customer_id = models.CharField("Stripe Customer ID", max_length=255, blank=True)
    stripe_subscription_id = models.CharField("Stripe Subscription ID", max_length=255, blank=True)
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    
    class Meta:
        verbose_name = "Tashkilot"
        verbose_name_plural = "Tashkilotlar"
    
    def __str__(self) -> str:
        return f"{self.name} ({self.get_plan_display()})"


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        INSTRUCTOR = "instructor", "Domla"
        STUDENT = "student", "Talaba"

    role = models.CharField(
        "Rol",
        max_length=20,
        choices=Roles.choices,
        default=Roles.STUDENT,
    )
    level = models.PositiveIntegerField("Daraja", default=1)
    xp = models.PositiveIntegerField("Tajriba (XP)", default=0)
    avatar = models.ImageField("Avatar", upload_to="avatars/", blank=True, null=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name="Tashkilot"
    )

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def save(self, *args, **kwargs):
        # Frontend faqat email kiritadi, shuning uchun username bo'sh bo'lsa, emailni ishlatamiz
        if not self.username and self.email:
            self.username = self.email
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="Foydalanuvchi")
    avatar_url = models.URLField("Avatar URL", blank=True)
    bio = models.TextField("Bioqrafiya", blank=True)
    phone = models.CharField("Telefon", max_length=20, blank=True)
    country = models.CharField("Davlat", max_length=100, blank=True)
    created_at = models.DateTimeField("Yaratilgan vaqti", auto_now_add=True)
    updated_at = models.DateTimeField("Yangilangan vaqti", auto_now=True)
    
    class Meta:
        verbose_name = "Foydalanuvchi profili"
        verbose_name_plural = "Foydalanuvchi profillari"
    
    def __str__(self) -> str:
        return f"{self.user.email} - Profil"

