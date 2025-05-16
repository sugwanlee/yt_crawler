from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .crawler import get_info
from .models import Shorts
# Create your views here.
class CrawlShorts(APIView):

    def post(self, request):
        urls = request.data.get("urls")
        data = get_info(urls)
        for item in data:
            Shorts.objects.create(
                stack_date = item["누적집계일"],
                channel_name = item["채널명"],
                video_title = item["영상 제목"],
                video_url = item["영상 링크"],
                upload_date = item["업로드일"],  # 이미 datetime이면 그대로
                video_views = item["조회수"],
                subscriber_count = item["구독자 수"]
            )
        return Response({"message": "success"})