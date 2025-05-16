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
            crawl_shorts(urls ,repeat=120)
            return Response({"message": "success"})
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        try:
            Task.objects.all().delete()
            return Response({"message": "success"})
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)