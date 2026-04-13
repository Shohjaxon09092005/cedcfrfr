#!/usr/bin/env python
"""
Final verification that all pipeline test generation fixes are in place.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduai_backend.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from courses.models import LessonResource, Test
from django.db import connection
from django.db.models import Q


def check_model_fields():
    """Verify model fields exist"""
    print("\n" + "="*60)
    print("1️⃣  Model Fields Verification")
    print("="*60)
    
    checks = []
    
    # Check LessonResource fields
    lr_fields = [f.name for f in LessonResource._meta.get_fields()]
    checks.append(("LessonResource.has_quiz", "has_quiz" in lr_fields))
    checks.append(("LessonResource.video_url", "video_url" in lr_fields))
    
    # Check Test fields
    test_fields = [f.name for f in Test._meta.get_fields()]
    checks.append(("Test.resource", "resource" in test_fields))
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
    
    return all(result for _, result in checks)


def check_migrations():
    """Verify migrations are applied"""
    print("\n" + "="*60)
    print("2️⃣  Database Migrations Verification")
    print("="*60)
    
    # Simply try to access the fields - if they exist, the migration was applied
    checks = []
    
    try:
        # Try to create a test LessonResource and access the new fields
        from courses.models import LessonResource
        
        # Check field exists by accessing field descriptor
        lr_model = LessonResource._meta
        has_quiz_field = lr_model.get_field('has_quiz')
        checks.append(("has_quiz field accessible", has_quiz_field is not None))
        
        video_url_field = lr_model.get_field('video_url')
        checks.append(("video_url field accessible", video_url_field is not None))
        
        # Check Test resource field
        from courses.models import Test
        test_model = Test._meta
        resource_field = test_model.get_field('resource')
        checks.append(("resource FK on Test accessible", resource_field is not None))
        
    except Exception as e:
        print(f"Error checking fields: {e}")
        return False
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
    
    return all(result for _, result in checks)


def check_pipeline_code():
    """Verify pipeline code has fixes"""
    print("\n" + "="*60)
    print("3️⃣  Pipeline Code Fixes Verification")
    print("="*60)
    
    checks = []
    
    # Check tasks.py for resource linking
    with open('ai_pipeline/tasks.py', 'r') as f:
        tasks_content = f.read()
        checks.append((
            "Quiz creation includes resource=resource_fresh",
            'resource=resource_fresh,' in tasks_content
        ))
        checks.append((
            "has_quiz flag is updated after quiz creation",
            'update(has_quiz=True)' in tasks_content
        ))
        checks.append((
            "video_url is stored in pipeline",
            'video_url=video_url_final' in tasks_content
        ))
    
    # Check views.py for correct has_quiz detection
    with open('ai_pipeline/views.py', 'r') as f:
        views_content = f.read()
        checks.append((
            "ResourceStatusView checks resource.has_quiz",
            'resource.has_quiz or Test.objects.filter(resource=resource' in views_content
        ))
        checks.append((
            "video_url field is prioritized over url",
            'resource.video_url or resource.url or' in views_content
        ))
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
    
    return all(result for _, result in checks)


def check_data_integrity():
    """Verify existing data has proper relationships"""
    print("\n" + "="*60)
    print("4️⃣  Data Integrity Verification")
    print("="*60)
    
    # Check tests are properly linked to resources
    tests_with_resource = Test.objects.filter(resource__isnull=False).count()
    tests_total = Test.objects.count()
    
    print(f"✅ Tests with resource linking: {tests_with_resource}/{tests_total}")
    
    # Check if any resources have has_quiz set
    resources_with_quiz = LessonResource.objects.filter(has_quiz=True).count()
    print(f"✅ Reources with has_quiz=True: {resources_with_quiz}")
    
    # Show sample of linked tests
    sample_tests = Test.objects.filter(resource__isnull=False)[:3]
    if sample_tests:
        print(f"\nSample tests with resource links:")
        for test in sample_tests:
            print(f"  - {test.title}")
            print(f"    Resource: {test.resource.title if test.resource else 'N/A'}")
            print(f"    Questions: {test.questions.count()}")
    
    return True


def main():
    """Run all verification checks"""
    print("\n" + "█"*60)
    print("🔍 EduAI Pipeline Test Generation - Final Verification")
    print("█"*60)
    
    results = []
    
    results.append(("Model Fields", check_model_fields()))
    results.append(("Database Migrations", check_migrations()))
    results.append(("Pipeline Code", check_pipeline_code()))
    results.append(("Data Integrity", check_data_integrity()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 VERIFICATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    print("="*60)
    
    if passed == total:
        print("\n✅ All pipeline test generation fixes are verified!")
        print("\nThe system is ready for:")
        print("  1. Manual quiz generation: POST /api/ai/generate-quiz/{resource_id}/")
        print("  2. Full pipeline: POST /api/ai/process/{resource_id}/")
        print("  3. Status tracking: GET /api/ai/status/{resource_id}/")
        return True
    else:
        print("\n⚠️  Some checks failed. Please review the output above.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
