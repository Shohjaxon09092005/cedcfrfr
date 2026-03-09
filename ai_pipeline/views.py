from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from drf_spectacular.utils import extend_schema
from courses.models import LessonResource, Test, Question
from .tasks import process_resource_pipeline


class TriggerPipelineView(APIView):
    """
    POST /api/ai/process/{resource_id}/
    Triggers the full AI pipeline for a LessonResource:
    file -> text extraction -> Claude script -> ElevenLabs audio -> Kling video -> quiz generation
    Returns immediately. Use WebSocket ws/resource/{id}/ or /api/ai/status/{id}/ to track progress.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="AI pipeline ishga tushirish",
        description="LessonResource uchun to'liq AI pipeline (matn→skript→audio→video→test) ni Celery orqali ishga tushiradi.",
        responses={202: {"type": "object", "properties": {
            "message": {"type": "string"},
            "resource_id": {"type": "integer"},
            "task_id": {"type": "string"},
        }}}
    )
    def post(self, request, resource_id):
        try:
            resource = LessonResource.objects.get(id=resource_id)
        except LessonResource.DoesNotExist:
            return Response({"error": "Resurs topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        # Check ownership
        if request.user.role == "instructor" and resource.lesson.course.instructor != request.user:
            return Response({"error": "Ruxsat yo'q"}, status=status.HTTP_403_FORBIDDEN)

        # Only process if there's a file
        if not resource.file:
            return Response({"error": "Fayl yuklanmagan"}, status=status.HTTP_400_BAD_REQUEST)

        # Trigger Celery task
        # For development/testing, run synchronously if Redis not available
        try:
            # Try to trigger async task
            task = process_resource_pipeline.delay(str(resource_id))
            return Response({
                "message": "AI pipeline ishga tushirildi",
                "resource_id": resource_id,
                "task_id": task.id,
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            # If Celery/Redis not available, run synchronously for testing
            print(f"Celery not available, running synchronously: {e}")
            try:
                # Import and call the synchronous function directly
                from .tasks import process_resource_pipeline_sync
                result = process_resource_pipeline_sync(str(resource_id))
                return Response({
                    "message": "AI pipeline sinxron bajarildi",
                    "resource_id": resource_id,
                    "result": result,
                }, status=status.HTTP_200_OK)
            except Exception as sync_error:
                return Response({
                    "error": f"Pipeline xatosi: {str(sync_error)}",
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResourceStatusView(APIView):
    """
    GET /api/ai/status/{resource_id}/
    Returns current processing status, video_url, transcript snippet.
    Used for polling if WebSocket is not available.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Resurs qayta ishlash holati",
        responses={200: {"type": "object", "properties": {
            "status": {"type": "string"},
            "video_url": {"type": "string"},
            "audio_url": {"type": "string"},
            "has_quiz": {"type": "boolean"},
            "error_message": {"type": "string"},
        }}}
    )
    def get(self, request, resource_id):
        try:
            resource = LessonResource.objects.get(id=resource_id)
        except LessonResource.DoesNotExist:
            return Response({"error": "Resurs topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        has_quiz = Test.objects.filter(course=resource.lesson.course, ai_generated=True).exists()

        return Response({
            "status": getattr(resource, "processing_status", "unknown"),
            "video_url": resource.url or "",
            "audio_url": getattr(resource, "audio_url", ""),
            "has_quiz": has_quiz,
            "error_message": getattr(resource, "error_message", ""),
        })


class GenerateQuizView(APIView):
    """
    POST /api/ai/generate-quiz/{resource_id}/
    Manually (re)generate AI quiz from a LessonResource's transcript.
    Deletes existing AI-generated quiz for this lesson, creates new one.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="AI test generatsiyasi",
        responses={201: {"type": "object", "properties": {
            "test_id": {"type": "integer"},
            "question_count": {"type": "integer"},
        }}}
    )
    def post(self, request, resource_id):
        try:
            resource = LessonResource.objects.get(id=resource_id)
        except LessonResource.DoesNotExist:
            return Response({"error": "Resurs topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        transcript = getattr(resource, "transcript", "") or ""
        if not transcript:
            return Response({"error": "Transkript mavjud emas. Avval AI pipeline ishga tushiring."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .services import ClaudeService
            claude = ClaudeService()
            quiz_data = claude.generate_quiz(transcript, num_questions=10)
        except Exception as e:
            return Response({"error": f"Quiz generatsiyada xato: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Delete old AI quiz for this lesson
        Test.objects.filter(course=resource.lesson.course, ai_generated=True).delete()

        # Create new test
        test = Test.objects.create(
            title=f"AI Test: {resource.title}",
            course=resource.lesson.course,
            duration=15,
            ai_generated=True,
            difficulty="medium",
        )
        # Create questions
        for i, q in enumerate(quiz_data.get("questions", [])):
            Question.objects.create(
                test=test,
                text=q["text"],
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q.get("topic", ""),
            )

        return Response({
            "test_id": test.id,
            "question_count": test.questions.count(),
        }, status=status.HTTP_201_CREATED)


class AIChatView(APIView):
    """
    POST /api/ai/chat/
    Body: {"message": "...", "course_id": optional int, "history": [{"role":"user","content":"..."}]}
    Returns: {"reply": "...", "sources": []}
    AI tutor that answers questions about course materials.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="AI tutor chat",
        request={"type": "object", "properties": {
            "message": {"type": "string"},
            "course_id": {"type": "integer"},
            "history": {"type": "array"},
        }},
        responses={200: {"type": "object", "properties": {
            "reply": {"type": "string"},
            "sources": {"type": "array"},
        }}}
    )
    def post(self, request):
        message = request.data.get("message", "").strip()
        course_id = request.data.get("course_id")
        history = request.data.get("history", [])

        if not message:
            return Response({"error": "Xabar bo'sh"}, status=status.HTTP_400_BAD_REQUEST)

        # Build context from course transcripts if course_id provided
        context = ""
        if course_id:
            from courses.models import LessonResource
            resources = LessonResource.objects.filter(
                lesson__course_id=course_id
            ).exclude(transcript="").values_list("transcript", flat=True)[:3]
            context = "\n\n".join(list(resources))[:5000]

        try:
            import anthropic
            from django.conf import settings
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            system_prompt = f"""Siz EduAI platformasining AI tutor assistentisiz.
Talabalar savollariga O'zbek tilida javob bering.
Qisqa, aniq va tushunарли javob bering.
{f"Kurs materiallari: {context}" if context else ""}"""

            messages_payload = []
            for h in history[-6:]:  # last 6 messages for context
                if h.get("role") in ("user", "assistant"):
                    messages_payload.append({"role": h["role"], "content": h["content"]})
            messages_payload.append({"role": "user", "content": message})

            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                system=system_prompt,
                messages=messages_payload,
            )
            reply = response.content[0].text

        except Exception as e:
            return Response({"error": f"AI xato: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"reply": reply, "sources": []})
