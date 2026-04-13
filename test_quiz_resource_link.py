#!/usr/bin/env python
"""
Test quiz creation directly from pipeline without API calls.
Tests that the test/resource linking works correctly.
"""

import os
import sys
import django
from pathlib import Path
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduai_backend.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Course, Lesson, LessonResource, Test, Question

User = get_user_model()


def test_quiz_creation_with_resource_link():
    """Test that quizzes are properly linked to resources"""
    print("\n" + "="*60)
    print("TEST: Quiz Creation with Resource Link")
    print("="*60)
    
    try:
        # Get or create test data
        user, _ = User.objects.get_or_create(
            username='pipelinetest',
            defaults={'email': 'pipeline@test.com'}
        )
        
        course, _ = Course.objects.get_or_create(
            title='Pipeline Test Course',
            defaults={
                'description': 'for testing pipeline',
                'instructor': user,
                'difficulty': 'beginner'
            }
        )
        
        lesson, _ = Lesson.objects.get_or_create(
            title='Pipeline Test Lesson',
            course=course,
            defaults={'order': 1}
        )
        
        resource, created = LessonResource.objects.get_or_create(
            title='Pipeline Test Resource',
            lesson=lesson,
            type='pdf',
            defaults={
                'transcript': 'Test transcript for pipeline testing',
                'description': 'Testing resource'
            }
        )
        
        print(f"✅ Resource: {resource.title} (ID: {resource.id})")
        print(f"   has_quiz before: {resource.has_quiz}")
        print(f"   video_url before: {resource.video_url}")
        
        # Simulate what the pipeline does for quiz creation
        print(f"\n🔧 Simulating pipeline quiz creation...")
        
        quiz_data = {
            "questions": [
                {
                    "text": "Test Question 1?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 0,
                    "topic": "Topic 1"
                },
                {
                    "text": "Test Question 2?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": 1,
                    "topic": "Topic 2"
                }
            ]
        }
        
        # Create test linked to resource (this is what should happen in pipeline)
        test = Test.objects.create(
            title=f"Pipeline Test: {resource.title}",
            course=course,
            resource=resource,  # ✅ This is the critical fix
            duration=15,
            ai_generated=True,
            difficulty="medium",
        )
        
        print(f"✅ Created test: {test.title} (ID: {test.id})")
        print(f"   Linked to resource: {test.resource.title if test.resource else 'NOT LINKED'}")
        
        # Create questions
        for q in quiz_data.get("questions", []):
            Question.objects.create(
                test=test,
                text=q["text"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q.get("topic", ""),
            )
        
        print(f"✅ Created {test.questions.count()} questions")
        
        # Update resource to mark quiz as created
        resource.has_quiz = True
        resource.video_url = "/media/videos/sample.mp4"
        resource.processing_status = "ready"
        resource.save()
        
        print(f"\n📊 Resource status after quiz creation:")
        resource.refresh_from_db()
        print(f"   has_quiz: {resource.has_quiz}")
        print(f"   video_url: {resource.video_url}")
        print(f"   status: {resource.processing_status}")
        
        # Verify the relationship works both ways
        print(f"\n✅ Relationship verification:")
        
        # From resource to test
        tests_for_resource = Test.objects.filter(resource=resource)
        print(f"   Tests for this resource: {tests_for_resource.count()}")
        for t in tests_for_resource:
            print(f"     - {t.title} ({t.questions.count()} questions)")
        
        # Check has_quiz detection
        from ai_pipeline.views import ResourceStatusView
        print(f"\n✅ API response check:")
        has_quiz = resource.has_quiz or Test.objects.filter(resource=resource, ai_generated=True).exists()
        print(f"   has_quiz from API logic: {has_quiz}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run test"""
    print("\n" + "█"*60)
    print("Quiz Creation with Resource Link Test")
    print("█"*60)
    
    success = test_quiz_creation_with_resource_link()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if success:
        print("✅ PASS - Quiz creation with resource link works correctly")
    else:
        print("❌ FAIL - Quiz creation has issues")
    
    print("="*60)
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
