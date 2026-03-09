from django.contrib import admin

from .models import Course, Resource, Test, Question, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "instructor", "category", "difficulty", "total_lessons", "created_at")
    list_filter = ("category", "difficulty", "created_at")
    search_fields = ("title", "description", "instructor__first_name", "instructor__last_name", "instructor__email")


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "type", "course", "category", "uploaded_at")
    list_filter = ("type", "category", "uploaded_at")
    search_fields = ("title", "course__title")


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "course", "duration", "difficulty", "ai_generated")
    list_filter = ("difficulty", "ai_generated")
    search_fields = ("title", "course__title")
    inlines = [QuestionInline]

