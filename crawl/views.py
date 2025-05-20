from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .task import crawl_shorts
from background_task.models import Task, CompletedTask
from rest_framework import status
from .serializers import ShortsSerializer, TaskSerializer, CompletedTaskSerializer
from .models import Shorts
import time

class CrawlShorts(APIView):
    """
    유튜브 쇼츠 크롤링 작업 24시간 주기 반복 등록 api

    json 형태 {"urls" : list[str]}

    수집하는 항목 : 각 영상 당; 채널명, 영상 제목, 영상 링크, 업로드일, 조회수, 구독자 수
    """

    def get(self, request):
        try:
            task = Task.objects.all()
            serializer = TaskSerializer(task, many=True)
            return Response({"message": "모든 크롤링 작업 조회", "task" : serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "작업 조회 실패", "error" : str(e)}, status=status.HTTP_400_BAD_REQUEST)
    # 크롤링 작업을 워커에게 등록하는 api
    def post(self, request):
        try:
            urls = request.data.get("urls")
            verbose_name = request.data.get("task_name")
            if Task.objects.filter(verbose_name = verbose_name).exists() or CompletedTask.objects.filter(verbose_name = verbose_name).exists():
                return Response({"message": "중복된 verbose_name입니다"}, status=status.HTTP_400_BAD_REQUEST)
            crawl_shorts(urls, verbose_name=verbose_name ,repeat=86400)
            task =  Task.objects.last()
            serializer = TaskSerializer(task)
            return Response({"message": "24시간 주기 크롤링 작업 시작", "task" : serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # 등록한 작업을 모두 취소하는 api
    def delete(self, request):
        try:
            Task.objects.all().delete()
            return Response({"message": "모든 크롤링 작업 취소"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class TaskCompleted(APIView):
    def get(self, request):
        try:
            verbose_name = request.data.get("task_name")
            if CompletedTask.objects.filter(verbose_name = verbose_name).exists():
                task = CompletedTask.objects.get(verbose_name = verbose_name)
                serializer = CompletedTaskSerializer(task)
                if task.failed_at:
                    return Response({"message": "크롤링 작업을 실패하였습니다.", "failed_tasks": serializer.data}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "완료된 작업입니다.", "completed_tasks": serializer.data}, status=status.HTTP_200_OK)
            return Response({"message": "실패한 작업을 찾지 못하였습니다."}, status=status.HTTP_200_OK)
        except Exception as e:
            Response({"message": "조회 중 에러 발생", "error" : str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        try:
            CompletedTask.objects.all().delete()
            return Response({"message": "완료, 실패한 작업 기록 삭제"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        
class ShortsData(APIView):

    def get(self, request):
        try:
            shorts = Shorts.objects.all()
            serializer = ShortsSerializer(shorts, many=True)
            return Response({"message" : "수집된 쇼츠 정보들 조회 완료", "data" : serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request):
        try:
            Shorts.objects.all().delete()
            return Response({"message": "수집된 모든 쇼츠 정보 삭제"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        