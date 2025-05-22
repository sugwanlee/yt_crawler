from django.db import models
from datetime import date, timedelta
# Create your models here.

class Shorts(models.Model):
    stack_date = models.DateField()                         # 누적집계일
    created_date = models.DateField(auto_now_add=True)      # 추출일
    channel_name = models.CharField(max_length=200)         # 채널명
    video_title = models.CharField(max_length=200)          # 영상 제목
    video_url = models.URLField()                           # 영상 링크
    upload_date = models.DateField()                        # 업로드일
    video_views = models.IntegerField()                     # 조회수
    subscriber_count = models.IntegerField()                # 구독자 수


    # 누적집계일 자동 생성
    def save(self, *args, **kwargs):
        if not self.stack_date:
            today = date.today()
            self.stack_date = today - timedelta(days=1)
        super().save(*args, **kwargs)