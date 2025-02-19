from django.db import models

class Alert(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    metric = models.CharField(max_length=50)
    status = models.CharField(max_length=10)  # 'warning' or 'critical'
    message = models.TextField()

    def __str__(self):
        return f"{self.timestamp} - {self.metric} - {self.status}"