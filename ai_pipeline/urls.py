from django.urls import path
from . import views

urlpatterns = [
    # Trigger AI pipeline for a LessonResource
    path("process/<int:resource_id>/", views.TriggerPipelineView.as_view(), name="trigger-pipeline"),
    # Check processing status
    path("status/<int:resource_id>/", views.ResourceStatusView.as_view(), name="resource-status"),
    # Generate quiz for a LessonResource
    path("generate-quiz/<int:resource_id>/", views.GenerateQuizView.as_view(), name="generate-quiz"),
    # AI Chatbot endpoint
    path("chat/", views.AIChatView.as_view(), name="ai-chat"),
]
