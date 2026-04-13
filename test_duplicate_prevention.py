#!/usr/bin/env python
"""
Test script for duplicate resource prevention.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduai_backend.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from courses.models import Course, Lesson, LessonResource
from django.contrib.auth import get_user_model

User = get_user_model()

def test_duplicate_prevention():
    """Test that duplicate files are prevented"""
    print("\n" + "="*60)
    print("TEST: Duplicate Resource Prevention")
    print("="*60)

    try:
        # Get test data
        instructor = User.objects.filter(role='instructor').first()
        if not instructor:
            print("❌ No instructor found")
            return False

        course = Course.objects.filter(instructor=instructor).first()
        if not course:
            print("❌ No course found")
            return False

        lesson = Lesson.objects.filter(course=course).first()
        if not lesson:
            print("❌ No lesson found")
            return False

        # Get existing resource
        existing_resources = LessonResource.objects.filter(lesson=lesson, file__isnull=False)
        if not existing_resources:
            print("❌ No existing file resources found")
            return False

        existing_resource = existing_resources[0]
        print(f"✅ Found existing resource: {existing_resource.title}")
        print(f"   File: {existing_resource.file.name}")

        # Try to create a duplicate
        from courses.serializers import LessonResourceSerializer
        data = {
            'title': 'Duplicate Test Resource',
            'type': existing_resource.type,
            'lesson': lesson.id,
            'file': existing_resource.file,  # Same file
            'description': 'Test duplicate',
            'order': 999
        }

        serializer = LessonResourceSerializer(data=data)
        is_valid = serializer.is_valid()
        print(f"✅ Serializer validation result: {is_valid}")

        if not is_valid:
            print(f"✅ Validation errors: {serializer.errors}")
            if 'non_field_errors' in serializer.errors:
                print("✅ Duplicate prevention working!")
                return True
            else:
                print("❌ Unexpected validation error")
                return False
        else:
            print("❌ Duplicate was allowed - this is bad!")
            return False

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_duplicate_prevention()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")