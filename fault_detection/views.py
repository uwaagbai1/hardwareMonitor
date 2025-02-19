from django.views.generic import TemplateView
from django.http import JsonResponse
from fault_detection.models import Alert

class MonitorView(TemplateView):
    template_name = 'fault_detection/monitor.html'

def alert_history(request):
    alerts = Alert.objects.order_by('-timestamp')[:5]
    data = [{
        'timestamp': alert.timestamp.isoformat(),
        'message': alert.message,
        'status': alert.status
    } for alert in alerts]
    return JsonResponse(data, safe=False)