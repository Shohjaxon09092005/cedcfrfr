from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "role", "level", "xp", "avatar", "organization"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name", "role"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        # username sifatida emailni ishlatamiz
        user = User(username=validated_data.get("email"), **validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            raise serializers.ValidationError("Email yoki parol xato.")

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Email yoki parol xato.")
        if not user.is_active:
            raise serializers.ValidationError("Foydalanuvchi faol emas.")
        attrs["user"] = user
        return attrs


class OrganizationSerializer(serializers.ModelSerializer):
    """Tashkilot serializer"""
    class Meta:
        from accounts.models import Organization
        model = Organization
        fields = [
            "id",
            "name",
            "plan",
            "max_students",
            "max_videos_per_month",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserProfileSerializer(serializers.ModelSerializer):
    """Foydalanuvchi profili serializer"""
    class Meta:
        from accounts.models import UserProfile
        model = UserProfile
        fields = [
            "id",
            "user",
            "avatar_url",
            "bio",
            "phone",
            "country",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user"]


class UserDetailSerializer(serializers.ModelSerializer):
    """Kengaytirilgan foydalanuvchi serializer"""
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "level",
            "xp",
            "avatar",
            "organization",
            "organization_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined", "level", "xp"]
