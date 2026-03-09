from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from drf_spectacular.utils import extend_schema
from courses.models import Course, TestResult, CourseEnrollment

User = get_user_model()


class TeacherDashboardView(APIView):
    """
    GET /api/analytics/teacher/dashboard/
    Returns: total_students, total_courses, total_videos,
             avg_score, recent_results, weak_topics_summary
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Domla dashboard statistikasi")
    def get(self, request):
        user = request.user
        courses = Course.objects.filter(instructor=user)
        course_ids = courses.values_list("id", flat=True)

        enrollments = CourseEnrollment.objects.filter(course_id__in=course_ids)
        total_students = enrollments.values("student").distinct().count()

        results = TestResult.objects.filter(test__course_id__in=course_ids).select_related("student", "test")
        avg_score = results.aggregate(avg=Avg("score"))["avg"] or 0

        # Collect weak topics from recent results
        weak_topic_counter = {}
        for r in results.order_by("-created_at")[:100]:
            for topic in (r.weak_topics or []):
                weak_topic_counter[topic] = weak_topic_counter.get(topic, 0) + 1

        weak_topics_summary = [
            {"topic": t, "count": c}
            for t, c in sorted(weak_topic_counter.items(), key=lambda x: -x[1])[:10]
        ]

        recent_results = []
        for r in results.order_by("-created_at")[:5]:
            recent_results.append({
                "id": r.id,
                "student_name": r.student.get_full_name() or r.student.email,
                "test_title": r.test.title,
                "score": r.score,
                "created_at": r.created_at.isoformat(),
                "weak_topics": r.weak_topics or [],
                "ai_feedback": r.ai_feedback or "",
            })

        return Response({
            "total_students": total_students,
            "total_courses": courses.count(),
            "total_videos": 0,
            "avg_score": round(avg_score, 1),
            "recent_results": recent_results,
            "weak_topics_summary": weak_topics_summary,
            "monthly_videos_used": 0,
            "monthly_videos_limit": getattr(request.user.organization, "max_videos_per_month", 20) if request.user.organization else 20,
        })


class StudentDashboardView(APIView):
    """
    GET /api/analytics/student/dashboard/
    Returns: enrolled_courses, completed_videos, avg_quiz_score,
             weak_topics, recommendations, recent_activity
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Talaba dashboard statistikasi")
    def get(self, request):
        user = request.user
        enrollments = CourseEnrollment.objects.filter(student=user)
        results = TestResult.objects.filter(student=user).select_related("test__course").order_by("-created_at")

        avg_score = results.aggregate(avg=Avg("score"))["avg"] or 0

        # Collect all weak topics from all results
        all_weak = {}
        all_recommendations = []
        for r in results[:20]:
            for t in (r.weak_topics or []):
                all_weak[t] = all_weak.get(t, 0) + 1
            if r.recommendations:
                all_recommendations.extend(r.recommendations)

        top_weak = [t for t, _ in sorted(all_weak.items(), key=lambda x: -x[1])[:5]]
        unique_recs = list(dict.fromkeys(all_recommendations))[:5]

        recent_activity = []
        for r in results[:5]:
            recent_activity.append({
                "type": "quiz",
                "title": r.test.title,
                "date": r.created_at.isoformat(),
                "score": r.score,
            })

        enrolled_courses_data = []
        for enrollment in enrollments.select_related("course"):
            enrolled_courses_data.append({
                "id": enrollment.id,
                "student_id": enrollment.student.id,
                "student_name": enrollment.student.get_full_name() or enrollment.student.email,
                "course_id": enrollment.course.id,
                "course_title": enrollment.course.title,
                "enrolled_at": enrollment.enrolled_at.isoformat(),
                "progress_percent": enrollment.progress_percent,
            })

        return Response({
            "enrolled_courses": enrolled_courses_data,
            "completed_videos": 0,
            "avg_quiz_score": round(avg_score, 1),
            "weak_topics": top_weak,
            "recommendations": unique_recs if unique_recs else [
                "Zaif mavzularni qayta o'rganing",
                "Har kuni kamida 30 daqiqa o'qing",
                "Test topshirishdan oldin video darsni ko'ring",
            ],
            "recent_activity": recent_activity,
        })


class CourseAnalyticsView(APIView):
    """GET /api/analytics/course/{course_id}/"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Kurs bo'yicha analytics")
    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Kurs topilmadi"}, status=404)

        results = TestResult.objects.filter(test__course=course)
        enrollments = CourseEnrollment.objects.filter(course=course)

        avg_score = results.aggregate(avg=Avg("score"))["avg"] or 0

        student_stats = []
        for enrollment in enrollments.select_related("student")[:50]:
            student_results = results.filter(student=enrollment.student)
            student_avg = student_results.aggregate(avg=Avg("score"))["avg"] or 0
            all_weak = []
            for r in student_results:
                all_weak.extend(r.weak_topics or [])
            student_stats.append({
                "student_id": enrollment.student.id,
                "student_name": enrollment.student.get_full_name() or enrollment.student.email,
                "avg_score": round(student_avg, 1),
                "tests_taken": student_results.count(),
                "weak_topics": list(set(all_weak))[:3],
                "progress_percent": enrollment.progress_percent,
            })

        return Response({
            "course_id": course_id,
            "course_title": course.title,
            "total_students": enrollments.count(),
            "avg_score": round(avg_score, 1),
            "student_stats": student_stats,
        })


class LeaderboardView(APIView):
    """
    GET /api/analytics/leaderboard/
    Returns top students by XP/score
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Talabalar reytingi")
    def get(self, request):
        # Get all test results and aggregate by student
        from django.db.models import Q
        student_stats = {}
        
        for result in TestResult.objects.select_related("student").all():
            student_id = result.student.id
            if student_id not in student_stats:
                student_stats[student_id] = {
                    "student_id": student_id,
                    "student_name": result.student.get_full_name() or result.student.email,
                    "total_xp": 0,
                    "avg_score": 0,
                    "tests_count": 0,
                    "total_score": 0,
                }
            
            # Calculate XP (simplified: 10 points per test + score bonus)
            xp_earned = 10 + (result.score / 10)
            student_stats[student_id]["total_xp"] += xp_earned
            student_stats[student_id]["total_score"] += result.score
            student_stats[student_id]["tests_count"] += 1

        # Calculate average scores and convert to list
        leaderboard = []
        for data in student_stats.values():
            if data["tests_count"] > 0:
                data["avg_score"] = round(data["total_score"] / data["tests_count"], 1)
                data["level"] = int(data["total_xp"] / 500) + 1  # Level calculation
                leaderboard.append(data)

        # Sort by XP descending
        leaderboard = sorted(leaderboard, key=lambda x: x["total_xp"], reverse=True)

        # Add ranks
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return Response(leaderboard[:100])
