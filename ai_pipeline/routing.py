from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/resource/(?P<resource_id>\d+)/$", consumers.ResourceProgressConsumer.as_asgi()),
]
