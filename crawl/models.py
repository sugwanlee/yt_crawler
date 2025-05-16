from django.db import models
from datetime import date, timedelta
# Create your models here.

class Shorts(models.Model):
    stack_date = models.DateField()
    created_date = models.DateField(auto_now_add=True)
    channel_name = models.CharField(max_length=200)
    video_title = models.CharField(max_length=200)
    video_url = models.URLField()
    upload_date = models.DateTimeField()
    video_views = models.IntegerField()
    subscriber_count = models.IntegerField()


    def save(self, *args, **kwargs):
        if not self.stack_date:
            today = date.today()
            self.stack_date = today - timedelta(days=1)
        super().save(*args, **kwargs)