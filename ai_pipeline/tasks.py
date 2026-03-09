from celery import shared_task
import tempfile, os, requests
from django.conf import settings


def _send_ws_progress(resource_id, status, message, video_url=""):
    """Send WebSocket progress update via Django Channels"""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"resource_{resource_id}",
                {
                    "type": "progress_update",
                    "status": status,
                    "message": message,
                    "video_url": video_url,
                }
            )
    except Exception as e:
        print(f"WebSocket send error: {e}")


def process_resource_pipeline_sync(resource_id: str):
    """
    Synchronous version of the AI pipeline for testing/development
    """
    from courses.models import LessonResource, Test, Question
    from ai_pipeline.services import TextExtractor, ClaudeService, ElevenLabsService, KlingAIService, S3Service

    def update(status, message, video_url=""):
        try:
            LessonResource.objects.filter(id=resource_id).update(
                processing_status=status,
                error_message="" if status != "failed" else message,
            )
        except Exception:
            pass
        _send_ws_progress(resource_id, status, message, video_url)

    try:
        resource = LessonResource.objects.get(id=resource_id)
    except LessonResource.DoesNotExist:
        return {"error": "Resource not found"}

    # Check if required API keys are configured
    if not settings.ANTHROPIC_API_KEY:
        update("failed", "❌ ANTHROPIC_API_KEY sozlanmagan. Admin bilan bog'laning.")
        return {"error": "Claude API key not configured"}

    try:
        # ── STEP 1: Extract text ──────────────────────────────────────────────
        update("extracting", "📄 Fayldan matn ajratilmoqda...")

        if not resource.file:
            update("failed", "Fayl yuklanmagan. Avval fayl yuklang.")
            return {"error": "No file attached"}

        file_path = resource.file.path
        file_name = resource.file.name
        if '.' not in file_name:
            update("failed", "Fayl kengaytmasi yo'q. Fayl nomini tekshiring.")
            return {"error": "File has no extension"}
        
        file_ext = file_name.rsplit(".", 1)[-1].lower()
        extractor = TextExtractor()
        transcript = extractor.extract(file_path, file_ext)

        if not transcript or len(transcript.strip()) < 50:
            update("failed", "Fayldan matn ajratib bo'lmadi. Fayl to'g'ri formatda ekanligini tekshiring.")
            return {"error": "Empty transcript"}

        LessonResource.objects.filter(id=resource_id).update(transcript=transcript[:15000])

        # ── STEP 2: Generate script with Claude ───────────────────────────────
        update("scripting", "🧠 Claude AI skript yaratmoqda...")
        claude = ClaudeService()
        script = claude.generate_video_script(transcript)
        LessonResource.objects.filter(id=resource_id).update(script=script)

        # ── STEP 3: Generate audio with ElevenLabs ────────────────────────────
        update("audio", "🎙️ O'zbek tilida ovoz yaratilmoqda...")

        audio_url_final = ""
        if settings.ELEVENLABS_API_KEY:
            try:
                elevenlabs = ElevenLabsService()
                audio_bytes = elevenlabs.generate_audio(script)

                # Try S3 upload; fall back to local media if S3 not configured
                if settings.AWS_S3_BUCKET and settings.AWS_ACCESS_KEY_ID:
                    s3 = S3Service()
                    audio_key = f"audio/{resource_id}/narration.mp3"
                    audio_url_final = s3.upload_bytes(audio_bytes, audio_key, "audio/mpeg")
                else:
                    # Local fallback: save under MEDIA_ROOT
                    audio_dir = os.path.join(settings.MEDIA_ROOT, "audio", str(resource_id))
                    os.makedirs(audio_dir, exist_ok=True)
                    audio_path = os.path.join(audio_dir, "narration.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(audio_bytes)
                    audio_url_final = f"{settings.MEDIA_URL}audio/{resource_id}/narration.mp3"

                LessonResource.objects.filter(id=resource_id).update(audio_url=audio_url_final)
            except Exception as e:
                print(f"Audio generation failed (non-fatal): {e}")
                update("audio", f"⚠️ Ovoz yaratishda xato (davom etilmoqda): {str(e)[:100]}")
        else:
            update("audio", "⚠️ ElevenLabs API kaliti sozlanmagan - ovoz yaratilmaydi")

        # ── STEP 4: Generate video with Kling AI ──────────────────────────────
        update("video", "🎬 Video yaratilmoqda (5-10 daqiqa ketadi)...")

        video_url_final = ""
        if settings.KLING_API_KEY and audio_url_final:
            try:
                kling = KlingAIService()
                video_url_raw = kling.generate_video(audio_url_final, script[:300])

                # Download and re-upload to our S3/local
                video_response = requests.get(video_url_raw, timeout=120)
                if settings.AWS_S3_BUCKET and settings.AWS_ACCESS_KEY_ID:
                    s3 = S3Service()
                    video_key = f"videos/{resource_id}/lesson.mp4"
                    video_url_final = s3.upload_bytes(video_response.content, video_key, "video/mp4")
                else:
                    video_dir = os.path.join(settings.MEDIA_ROOT, "videos", str(resource_id))
                    os.makedirs(video_dir, exist_ok=True)
                    video_path = os.path.join(video_dir, "lesson.mp4")
                    with open(video_path, "wb") as f:
                        f.write(video_response.content)
                    video_url_final = f"{settings.MEDIA_URL}videos/{resource_id}/lesson.mp4"

                LessonResource.objects.filter(id=resource_id).update(url=video_url_final)
            except Exception as e:
                print(f"Video generation failed (non-fatal): {e}")
        else:
            update("video", "⚠️ Kling AI API kaliti sozlanmagan yoki audio yo'q - video yaratilmaydi")

        # ── STEP 5: Generate quiz with Claude ─────────────────────────────────
        update("quiz", "📝 AI test yaratilmoqda...")

        try:
            quiz_data = claude.generate_quiz(transcript, num_questions=10)

            # Delete old AI-generated test for this resource's lesson
            resource_fresh = LessonResource.objects.get(id=resource_id)
            Test.objects.filter(course=resource_fresh.lesson.course, ai_generated=True).delete()

            test = Test.objects.create(
                title=f"AI Test: {resource_fresh.title}",
                course=resource_fresh.lesson.course,
                duration=15,
                ai_generated=True,
                difficulty="medium",
            )
            for q in quiz_data.get("questions", []):
                Question.objects.create(
                    test=test,
                    text=q["text"],
                    options=q["options"],
                    correct_answer=q["correct_answer"],
                    explanation=q.get("topic", ""),
                )
        except Exception as e:
            print(f"Quiz generation failed (non-fatal): {e}")

        # ── DONE ──────────────────────────────────────────────────────────────
        update("ready", "✅ Video va test tayyor! Endi talabalar ko'ra oladi.", video_url_final)
        return {"status": "success", "resource_id": resource_id, "video_url": video_url_final}

    except Exception as exc:
        error_msg = f"❌ Pipeline xatosi: {str(exc)}"
        update("failed", error_msg)
        raise


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_resource_pipeline(self, resource_id: str):
    """
    Full AI pipeline: File → Text → Script → ElevenLabs Audio → Kling Video → Quiz
    Each step:
    - Updates LessonResource.processing_status
    - Sends WebSocket progress to group resource_{resource_id}
    - Saves intermediate results (transcript, script, audio_url, video url)
    """
    from courses.models import LessonResource, Test, Question
    from ai_pipeline.services import TextExtractor, ClaudeService, ElevenLabsService, KlingAIService, S3Service

    def update(status, message, video_url=""):
        try:
            LessonResource.objects.filter(id=resource_id).update(
                processing_status=status,
                error_message="" if status != "failed" else message,
            )
        except Exception:
            pass
        _send_ws_progress(resource_id, status, message, video_url)

    try:
        resource = LessonResource.objects.get(id=resource_id)
    except LessonResource.DoesNotExist:
        return {"error": "Resource not found"}

    # Check if required API keys are configured
    if not settings.ANTHROPIC_API_KEY:
        update("failed", "❌ ANTHROPIC_API_KEY sozlanmagan. Admin bilan bog'laning.")
        return {"error": "Claude API key not configured"}

    try:
        # ── STEP 1: Extract text ──────────────────────────────────────────────
        update("extracting", "📄 Fayldan matn ajratilmoqda...")

        if not resource.file:
            update("failed", "Fayl yuklanmagan. Avval fayl yuklang.")
            return {"error": "No file attached"}

        file_path = resource.file.path
        file_name = resource.file.name
        if '.' not in file_name:
            update("failed", "Fayl kengaytmasi yo'q. Fayl nomini tekshiring.")
            return {"error": "File has no extension"}
        
        file_ext = file_name.rsplit(".", 1)[-1].lower()
        extractor = TextExtractor()
        transcript = extractor.extract(file_path, file_ext)

        if not transcript or len(transcript.strip()) < 50:
            update("failed", "Fayldan matn ajratib bo'lmadi. Fayl to'g'ri formatda ekanligini tekshiring.")
            return {"error": "Empty transcript"}

        LessonResource.objects.filter(id=resource_id).update(transcript=transcript[:15000])

        # ── STEP 2: Generate script with Claude ───────────────────────────────
        update("scripting", "🧠 Claude AI skript yaratmoqda...")
        claude = ClaudeService()
        script = claude.generate_video_script(transcript)
        LessonResource.objects.filter(id=resource_id).update(script=script)

        # ── STEP 3: Generate audio with ElevenLabs ────────────────────────────
        update("audio", "🎙️ O'zbek tilida ovoz yaratilmoqda...")

        audio_url_final = ""
        if settings.ELEVENLABS_API_KEY:
            try:
                elevenlabs = ElevenLabsService()
                audio_bytes = elevenlabs.generate_audio(script)

                # Try S3 upload; fall back to local media if S3 not configured
                if settings.AWS_S3_BUCKET and settings.AWS_ACCESS_KEY_ID:
                    s3 = S3Service()
                    audio_key = f"audio/{resource_id}/narration.mp3"
                    audio_url_final = s3.upload_bytes(audio_bytes, audio_key, "audio/mpeg")
                else:
                    # Local fallback: save under MEDIA_ROOT
                    import uuid
                    audio_dir = os.path.join(settings.MEDIA_ROOT, "audio", str(resource_id))
                    os.makedirs(audio_dir, exist_ok=True)
                    audio_path = os.path.join(audio_dir, "narration.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(audio_bytes)
                    audio_url_final = f"{settings.MEDIA_URL}audio/{resource_id}/narration.mp3"

                LessonResource.objects.filter(id=resource_id).update(audio_url=audio_url_final)
            except Exception as e:
                print(f"Audio generation failed (non-fatal): {e}")
                update("audio", f"⚠️ Ovoz yaratishda xato (davom etilmoqda): {str(e)[:100]}")
        else:
            update("audio", "⚠️ ElevenLabs API kaliti sozlanmagan - ovoz yaratilmaydi")

        # ── STEP 4: Generate video with Kling AI ──────────────────────────────
        update("video", "🎬 Video yaratilmoqda (5-10 daqiqa ketadi)...")

        video_url_final = ""
        if settings.KLING_API_KEY and audio_url_final:
            try:
                kling = KlingAIService()
                video_url_raw = kling.generate_video(audio_url_final, script[:300])

                # Download and re-upload to our S3/local
                video_response = requests.get(video_url_raw, timeout=120)
                if settings.AWS_S3_BUCKET and settings.AWS_ACCESS_KEY_ID:
                    s3 = S3Service()
                    video_key = f"videos/{resource_id}/lesson.mp4"
                    video_url_final = s3.upload_bytes(video_response.content, video_key, "video/mp4")
                else:
                    video_dir = os.path.join(settings.MEDIA_ROOT, "videos", str(resource_id))
                    os.makedirs(video_dir, exist_ok=True)
                    video_path = os.path.join(video_dir, "lesson.mp4")
                    with open(video_path, "wb") as f:
                        f.write(video_response.content)
                    video_url_final = f"{settings.MEDIA_URL}videos/{resource_id}/lesson.mp4"

                LessonResource.objects.filter(id=resource_id).update(url=video_url_final)
            except Exception as e:
                print(f"Video generation failed (non-fatal): {e}")
        else:
            update("video", "⚠️ Kling AI API kaliti sozlanmagan yoki audio yo'q - video yaratilmaydi")

        # ── STEP 5: Generate quiz with Claude ─────────────────────────────────
        update("quiz", "📝 AI test yaratilmoqda...")

        try:
            quiz_data = claude.generate_quiz(transcript, num_questions=10)

            # Delete old AI-generated test for this resource's lesson
            resource_fresh = LessonResource.objects.get(id=resource_id)
            Test.objects.filter(course=resource_fresh.lesson.course, ai_generated=True).delete()

            test = Test.objects.create(
                title=f"AI Test: {resource_fresh.title}",
                course=resource_fresh.lesson.course,
                duration=15,
                ai_generated=True,
                difficulty="medium",
            )
            for q in quiz_data.get("questions", []):
                Question.objects.create(
                    test=test,
                    text=q["text"],
                    options=q["options"],
                    correct_answer=q["correct_answer"],
                    explanation=q.get("topic", ""),
                )
        except Exception as e:
            print(f"Quiz generation failed (non-fatal): {e}")

        # ── DONE ──────────────────────────────────────────────────────────────
        update("ready", "✅ Video va test tayyor! Endi talabalar ko'ra oladi.", video_url_final)
        return {"status": "success", "resource_id": resource_id, "video_url": video_url_final}

    except Exception as exc:
        error_msg = f"❌ Pipeline xatosi: {str(exc)}"
        update("failed", error_msg)
        raise self.retry(exc=exc)


@shared_task
def analyze_quiz_results_task(test_result_id: int):
    """
    After a student submits a quiz, analyze weak topics with Claude.
    Updates TestResult with weak_topics and ai_feedback fields.
    Requires weak_topics and ai_feedback fields on TestResult model (see BACKEND PROBLEM 5).
    """
    from courses.models import TestResult
    from ai_pipeline.services import ClaudeService

    try:
        result = TestResult.objects.select_related("student", "test__course").get(id=test_result_id)
        claude = ClaudeService()

        # Get questions with topics
        questions = list(result.test.questions.values("text", "correct_answer", "explanation"))
        answers = result.answers  # list of submitted answer indices
        wrong = []
        for i, (q, ans) in enumerate(zip(questions, answers)):
            if ans != q["correct_answer"]:
                wrong.append({
                    "question": q["text"],
                    "topic": q["explanation"],  # explanation field stores topic tag
                    "submitted": ans,
                })

        analysis = claude.analyze_weak_topics(wrong, result.student.get_full_name() or result.student.email)

        # Save analysis — these fields must exist on TestResult (see PROBLEM 5)
        TestResult.objects.filter(id=test_result_id).update(
            weak_topics=analysis.get("weak_topics", []),
            ai_feedback=analysis.get("overall_feedback", ""),
            recommendations=analysis.get("recommendations", []),
        )
        return {"status": "success", "analysis": analysis}

    except Exception as e:
        print(f"Quiz analysis failed: {e}")
        return {"status": "error", "message": str(e)}
