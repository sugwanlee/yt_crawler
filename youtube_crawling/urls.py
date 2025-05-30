from django.urls import path
from youtube_crawling.views.longform_views import (
    YoutubeLongFormCrawlAPIView,
    YouTubeVideoOneAPIView,
    ChannelCrawlTriggerView
    )

urlpatterns = [
    path('', YoutubeLongFormCrawlAPIView.as_view()), # 여러 개 영상 크롤링 (C,R,PUT,D)
    path('<str:video_id>/', YouTubeVideoOneAPIView.as_view()), # 특정 영상 한 개 (R,D,PATCH)
    path('channel/task/', ChannelCrawlTriggerView.as_view()), # 유튜브 채널에 있는 영상 크롤링 (POST)
]