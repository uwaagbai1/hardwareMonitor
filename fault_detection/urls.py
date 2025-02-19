from django.urls import path
from .views import MonitorView, alert_history

urlpatterns = [
    path('', MonitorView.as_view(), name='monitor'),
    path('alerts/history/', alert_history, name='alert_history'),
]