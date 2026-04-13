from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from drf_spectacular.utils import extend_schema
import datetime
from courses.models import LessonResource, Test, Question
from .tasks import process_resource_pipeline


class VideoProcessingView(APIView):
    """
    POST /api/ai/process-video/{resource_id}/
    Triggers VIDEO ONLY pipeline for a LessonResource:
    file -> text extraction -> Claude script -> ElevenLabs audio -> Kling video
    Does NOT generate test. Test must be created separately via /api/ai/generate-quiz/
    Returns immediately. Use WebSocket ws/resource/{id}/ or /api/ai/status/{id}/ to track progress.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Video yaratish pipeline",
        description="LessonResource uchun video yaratish pipeline ni ishga tushiradi (test yaratilmaydi).",
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

        # Only allow instructors and admins to trigger processing
        if request.user.role not in ['instructor', 'admin']:
            return Response({"error": "Faqat instruktorlar va adminlar AI processing ishga tushirishi mumkin"}, status=status.HTTP_403_FORBIDDEN)

        # Only process if there's a file
        if not resource.file:
            return Response({"error": "Fayl yuklanmagan"}, status=status.HTTP_400_BAD_REQUEST)

        # Trigger async video-only task
        try:
            from .tasks import process_resource_video_only
            task = process_resource_video_only.delay(str(resource_id))
            return Response({
                "message": "Video pipeline ishga tushirildi (test yaratilmaydi)",
                "resource_id": resource_id,
                "task_id": task.id,
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            # If Celery/Redis not available, run synchronously for testing
            print(f"Celery not available, running synchronously: {e}")
            try:
                from .tasks import process_resource_video_only_sync
                result = process_resource_video_only_sync(str(resource_id))
                return Response({
                    "message": "Video pipeline sinxron bajarildi",
                    "resource_id": resource_id,
                    "result": result,
                }, status=status.HTTP_200_OK)
            except Exception as sync_error:
                return Response({
                    "error": f"Video pipeline xatosi: {str(sync_error)}",
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TriggerPipelineView(APIView):
    """
    POST /api/ai/process/{resource_id}/
    Triggers the full AI pipeline for a LessonResource:
    file -> text extraction -> Claude script -> ElevenLabs audio -> Kling video -> quiz generation
    Returns immediately. Use WebSocket ws/resource/{id}/ or /api/ai/status/{id}/ to track progress.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="To'liq AI pipeline ishga tushirish",
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

        # Only allow instructors and admins to trigger processing
        if request.user.role not in ['instructor', 'admin']:
            return Response({"error": "Faqat instruktorlar va adminlar AI processing ishga tushirishi mumkin"}, status=status.HTTP_403_FORBIDDEN)

        # Only process if there's a filez
        if not resource.file:
            return Response({"error": "Fayl yuklanmagan"}, status=status.HTTP_400_BAD_REQUEST)

        # Trigger Celery task
        # For development/testing, run synchronously if Redis not available
        try:
            # Try to trigger async task
            task = process_resource_pipeline.delay(str(resource_id))
            return Response({
                "message": "To'liq AI pipeline ishga tushirildi (video va test yaratiladi)",
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
                    "message": "To'liq AI pipeline sinxron bajarildi",
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

        # Check if this resource has a quiz
        has_quiz = resource.has_quiz or Test.objects.filter(resource=resource, ai_generated=True).exists()

        return Response({
            "status": getattr(resource, "processing_status", "unknown"),
            "video_url": resource.video_url or resource.url or "",
            "audio_url": getattr(resource, "audio_url", ""),
            "has_quiz": has_quiz,
            "error_message": getattr(resource, "error_message", ""),
        })


class GenerateQuizView(APIView):
    """
    POST /api/ai/generate-quiz/{resource_id}/
    Manually (re)generate AI quiz from a LessonResource's transcript.
    Domla tanlay olishi mumkin:
    - duration: Test davomiyligi (minut), default: 30
    - difficulty: Darajasi (easy/medium/hard), default: medium
    - num_questions: Savollar soni, default: 10
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="AI test generatsiyasi",
        request={"type": "object", "properties": {
            "duration": {"type": "integer", "description": "Davomiyligi (minut)", "default": 15},
            "difficulty": {"type": "string", "description": "Darajasi (easy/medium/hard/mixed)", "default": "medium"},
            "num_questions": {"type": "integer", "description": "Savollar soni", "default": 10},
        }},
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

        # Get parameters from request, with defaults
        duration = request.data.get("duration", 15)
        difficulty = request.data.get("difficulty", "medium")
        num_questions = request.data.get("num_questions", 10)

        # Validate parameters
        try:
            duration = int(duration)
            if duration < 5 or duration > 120:
                raise ValueError("Davomiyligi 5 dan 120 minutgacha bo'lishi kerak")
        except (ValueError, TypeError):
            return Response({"error": "Davomiyligi noto'g'ri: 5-120 minut orasida bo'lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)

        if difficulty not in ["easy", "medium", "hard", "mixed"]:
            return Response({"error": "Darajasi noto'g'ri: easy, medium, hard yoki mixed bo'lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            num_questions = int(num_questions)
            if num_questions < 5 or num_questions > 30:
                raise ValueError("Savollar soni 5 dan 30 gacha bo'lishi kerak")
        except (ValueError, TypeError):
            return Response({"error": "Savollar soni noto'g'ri: 5-30 orasida bo'lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .services import ClaudeService
            claude = ClaudeService()
            quiz_data = claude.generate_quiz(transcript, num_questions=num_questions, difficulty=difficulty)
        except Exception as e:
            return Response({"error": f"Quiz generatsiyada xato: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Delete only this resource's old AI-generated tests
        Test.objects.filter(
            resource=resource,
            ai_generated=True
        ).delete()

        # Create new test with custom parameters
        test = Test.objects.create(
            title=f"AI Test: {resource.title} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            course=resource.lesson.course,
            resource=resource,
            duration=duration,
            ai_generated=True,
            difficulty=difficulty,
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
            "duration": duration,
            "difficulty": difficulty,
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
