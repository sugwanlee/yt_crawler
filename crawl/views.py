from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .task import crawl_shorts
from background_task.models import Task
from rest_framework import status
# Create your views here.
class CrawlShorts(APIView):

    def post(self, request):
        try:
            urls = request.data.get("urls")
            crawl_shorts(urls ,repeat=86400)
            return Response({"message": "24시간 주기 크롤링 작업 시작"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        try:
            Task.objects.all().delete()
            return Response({"message": "크롤링 작업 취소"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)