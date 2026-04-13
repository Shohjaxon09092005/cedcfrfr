#!/usr/bin/env python
"""
Test API endpoints for quiz generation.
Tests the GenerateQuizView and other quiz endpoints.
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

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from courses.models import Course, Lesson, LessonResource, Test
from ai_pipeline.views import GenerateQuizView
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def get_or_create_test_user():
    """Get or create a test user with proper authentication"""
    user, created = User.objects.get_or_create(
        username='testapi',
        defaults={
            'email': 'testapi@example.com',
            'is_staff': False,
            'is_superuser': False
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
    return user


def test_generate_quiz_endpoint():
    """Test GenerateQuizView endpoint"""
    print("\n" + "="*60)
    print("TEST: GenerateQuizView API Endpoint")
    print("="*60)
    
    try:
        # Get test user and resources
        user = get_or_create_test_user()
        
        # Generate JWT token for the user
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        resources = LessonResource.objects.filter(transcript__isnull=False).exclude(transcript='')[:5]
        
        if not resources:
            print("❌ No resources with transcripts found in database")
            return False
        
        test_resource = resources[0]
        print(f"✅ Using resource: {test_resource.title} (ID: {test_resource.id})")
        print(f"   Transcript length: {len(test_resource.transcript)} chars")
        
        # Test using Client with JWT authentication
        client = Client()
        
        # Make POST request to the endpoint with JWT token
        response = client.post(
            f'/api/ai/generate-quiz/{test_resource.id}/',
            json.dumps({
                'duration': 20,
                'difficulty': 'medium',
                'num_questions': 5
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {access_token}'
        )
        
        print(f"✅ API Response Status: {response.status_code}")
        
        # Parse response
        if response.status_code in [200, 201]:
            try:
                response_data = json.loads(response.content)
                print(f"✅ Response data:")
                print(f"   test_id: {response_data.get('test_id')}")
                print(f"   question_count: {response_data.get('question_count')}")
                
                # Verify test was created
                test_id = response_data.get('test_id')
                if test_id:
                    test_obj = Test.objects.get(id=test_id)
                    print(f"✅ Test created successfully: {test_obj.title}")
                    print(f"   Questions: {test_obj.questions.count()}")
                    print(f"   AI Generated: {test_obj.ai_generated}")
                    print(f"   Resource: {test_obj.resource.title if test_obj.resource else 'None'}")
                    return True
            except json.JSONDecodeError:
                print(f"  Response content: {response.content[:200]}")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            try:
                print(f"   Response: {json.loads(response.content)}")
            except:
                print(f"   Response: {response.content[:200].decode('utf-8', errors='ignore')}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing API endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_existing_tests_count():
    """Check how many tests exist"""
    print("\n" + "="*60)
    print("TEST: Existing Tests in Database")
    print("="*60)
    
    try:
        total_tests = Test.objects.count()
        ai_generated = Test.objects.filter(ai_generated=True).count()
        
        print(f"✅ Total tests: {total_tests}")
        print(f"✅ AI-generated tests: {ai_generated}")
        
        # Show recent tests
        recent_tests = Test.objects.order_by('-id')[:5]
        if recent_tests:
            print(f"\nRecent tests:")
            for test in recent_tests:
                print(f"  - {test.title} (ID: {test.id})")
                print(f"    Questions: {test.questions.count()}")
                print(f"    Difficulty: {test.difficulty}")
                print(f"    AI Generated: {test.ai_generated}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Run all API tests"""
    print("\n" + "█"*60)
    print("Quiz Generation API Test Suite")
    print("█"*60)
    
    results = []
    
    # Test API endpoint
    results.append(("GenerateQuizView Endpoint", test_generate_quiz_endpoint()))
    
    # Check existing tests
    results.append(("Existing Tests Count", test_existing_tests_count()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*60)
    
    return all(result for _, result in results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
