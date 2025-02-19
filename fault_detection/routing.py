from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/hardware_monitor/$', consumers.HardwareMonitorConsumer.as_asgi()),
]