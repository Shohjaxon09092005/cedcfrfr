#!/usr/bin/env python
"""
Test full AI pipeline including test creation.
Tests the process_resource_pipeline_sync function.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduai_backend.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Course, Lesson, LessonResource, Test

User = get_user_model()


def test_full_pipeline():
    """Test full pipeline with quiz creation"""
    print("\n" + "="*60)
    print("TEST: Full AI Pipeline with Quiz Creation")
    print("="*60)
    
    try:
        # Get or create test resource
        resources = LessonResource.objects.filter(
            transcript__isnull=False
        ).exclude(transcript='').exclude(transcript='')[:1]
        
        if not resources:
            print("❌ No resources with transcripts found")
            return False
        
        resource = resources[0]
        print(f"✅ Selected resource: {resource.title} (ID: {resource.id})")
        print(f"   Transcript length: {len(resource.transcript)} chars")
        
        # Reset the resource
        before_count = Test.objects.filter(resource=resource).count()
        print(f"   Tests before pipeline: {before_count}")
        
        # Run the pipeline synchronously
        print("\n🚀 Running full pipeline...")
        from ai_pipeline.tasks import process_resource_pipeline_sync
        result = process_resource_pipeline_sync(str(resource.id))
        
        print(f"✅ Pipeline result: {result}")
        
        # Check the resource status
        resource.refresh_from_db()
        print(f"\n📊 Resource status after pipeline:")
        print(f"   Status: {resource.processing_status}")
        print(f"   Has Quiz: {resource.has_quiz}")
        print(f"   Video URL: {resource.video_url[:50] if resource.video_url else 'None'}")
        print(f"   Audio URL: {resource.audio_url[:50] if resource.audio_url else 'None'}")
        print(f"   Error: {resource.error_message if resource.error_message else 'None'}")
        
        # Check if test was created
        tests = Test.objects.filter(resource=resource)
        after_count = tests.count()
        print(f"\n✅ Tests after pipeline: {after_count}")
        print(f"   Tests created: {after_count - before_count}")
        
        if tests.exists():
            for test in tests:
                print(f"\n   Test: {test.title}")
                print(f"     Questions: {test.questions.count()}")
                print(f"     AI Generated: {test.ai_generated}")
                print(f"     Difficulty: {test.difficulty}")
                print(f"     Duration: {test.duration} min")
                
                # Show sample questions
                questions = test.questions.all()[:2]
                for i, q in enumerate(questions, 1):
                    print(f"\n     Question {i}:")
                    print(f"       Text: {q.text[:50]}...")
                    print(f"       Options: {len(q.options)}")
                    print(f"       Correct: {q.correct_answer}")
            
            # Verify status
            if resource.processing_status == "ready":
                print("\n✅ Pipeline completed successfully!")
                return True
            else:
                print(f"\n⚠️ Pipeline status: {resource.processing_status}")
                if resource.error_message:
                    print(f"   Error: {resource.error_message[:100]}")
                return True if after_count > before_count else False
        else:
            print("\n❌ No tests were created")
            return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run test"""
    print("\n" + "█"*60)
    print("Full Pipeline with Quiz Creation Test")
    print("█"*60)
    
    success = test_full_pipeline()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if success:
        print("✅ PASS - Full pipeline works with quiz creation")
    else:
        print("❌ FAIL - Pipeline has issues")
    
    print("="*60)
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
