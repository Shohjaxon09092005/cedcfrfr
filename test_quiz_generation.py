#!/usr/bin/env python
"""
Test script for quiz generation functionality.
Tests both mock and real Claude API responses.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eduai_backend.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from courses.models import Course, Lesson, LessonResource, Test, Question
from ai_pipeline.services import ClaudeService
from django.contrib.auth import get_user_model
import json

User = get_user_model()


def test_mock_quiz_generation():
    """Test quiz generation with mock responses"""
    print("\n" + "="*60)
    print("TEST 1: Mock Quiz Generation")
    print("="*60)
    
    try:
        claude = ClaudeService()
        
        # Sample transcript
        transcript = """
        Omborxona tizimi - bu mahsulotlarni saqlash va boshqarish tizimi.
        Omborxonaning asosiy maqsadi - mahsulotlarni samarali shakilda saqlash.
        FIFO (Birinchi kirgan - birinchi chiqadi) metodi omborxonada keng ishlatilyadi.
        LIFO (Oxirgi kirgan - birinchi chiqadi) metodi esa ba'zi hollarda qo'llaniladi.
        Omborxonaning samaradorligini oshirish uchun avtomatlashtirish zarur.
        """
        
        # Generate quiz
        quiz_data = claude.generate_quiz(
            transcript,
            num_questions=5,
            difficulty="medium"
        )
        
        print(f"✅ Generated {len(quiz_data.get('questions', []))} questions")
        
        for i, q in enumerate(quiz_data.get('questions', []), 1):
            print(f"\nQuestion {i}:")
            print(f"  Text: {q.get('text', 'N/A')[:50]}...")
            print(f"  Options: {len(q.get('options', []))} variants")
            print(f"  Correct Answer: {q.get('correct_answer', 'N/A')}")
            print(f"  Topic: {q.get('topic', 'N/A')}")
            print(f"  Difficulty: {q.get('difficulty', 'N/A')}")
        
        print("\n✅ Mock quiz generation successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error in mock quiz generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_quiz_creation_in_db():
    """Test creating quiz in database"""
    print("\n" + "="*60)
    print("TEST 2: Quiz Creation in Database")
    print("="*60)
    
    try:
        # Get or create test data
        user, _ = User.objects.get_or_create(
            username='testinstructor',
            defaults={'email': 'test@example.com', 'is_staff': False}
        )
        
        course, _ = Course.objects.get_or_create(
            title='Test Course',
            defaults={
                'description': 'Test course for quiz generation',
                'instructor': user,
                'difficulty': 'beginner'
            }
        )
        
        lesson, _ = Lesson.objects.get_or_create(
            title='Test Lesson',
            course=course,
            defaults={'order': 1}
        )
        
        resource, _ = LessonResource.objects.get_or_create(
            title='Test Resource',
            lesson=lesson,
            type='pdf',
            defaults={
                'transcript': 'Omborxona tizimi - bu mahsulotlarni saqlash usuli.',
                'description': 'Test resource'
            }
        )
        
        print(f"✅ Created/Retrieved resource: {resource.title} (ID: {resource.id})")
        print(f"   Resource transcript: {resource.transcript[:50]}...")
        
        # Generate quiz questions
        claude = ClaudeService()
        quiz_data = claude.generate_quiz(
            resource.transcript,
            num_questions=3,
            difficulty='easy'
        )
        
        # Create test in database
        test = Test.objects.create(
            title=f"Test Quiz from {resource.title}",
            course=course,
            resource=resource,
            duration=15,
            ai_generated=True,
            difficulty='easy'
        )
        print(f"✅ Created test: {test.title} (ID: {test.id})")
        
        # Create questions
        question_count = 0
        for q in quiz_data.get('questions', []):
            question = Question.objects.create(
                test=test,
                text=q.get('text', 'No text'),
                options=q.get('options', []),
                correct_answer=q.get('correct_answer', 0),
                explanation=q.get('topic', '')
            )
            question_count += 1
            print(f"  ✅ Created question {question_count}: {question.text[:40]}...")
        
        print(f"\n✅ Successfully created test with {question_count} questions")
        
        # Verify by retrieving
        retrieved_test = Test.objects.get(id=test.id)
        question_count_retrieved = retrieved_test.questions.count()
        print(f"✅ Retrieved test has {question_count_retrieved} questions")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in database quiz creation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_list_existing_resources():
    """List existing resources for testing"""
    print("\n" + "="*60)
    print("TEST 3: List Existing Resources")
    print("="*60)
    
    try:
        resources = LessonResource.objects.all()
        if not resources.exists():
            print("❌ No resources found in database")
            return False
        
        print(f"✅ Found {resources.count()} resources:")
        for resource in resources:
            transcript_preview = resource.transcript[:50] if resource.transcript else "No transcript"
            print(f"  - {resource.title} (ID: {resource.id})")
            print(f"    Type: {resource.type}")
            print(f"    Transcript: {transcript_preview}...")
            print(f"    Status: {resource.processing_status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error listing resources: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "█"*60)
    print("SQL Quiz Generation Test Suite")
    print("█"*60)
    
    results = []
    
    # Test 1: Mock quiz generation
    results.append(("Mock Quiz Generation", test_mock_quiz_generation()))
    
    # Test 2: Database quiz creation
    results.append(("Database Quiz Creation", test_quiz_creation_in_db()))
    
    # Test 3: List resources
    results.append(("List Existing Resources", test_list_existing_resources()))
    
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
