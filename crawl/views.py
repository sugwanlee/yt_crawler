from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .tasks import crawl_shorts
from rest_framework import status
from .serializers import ShortsSerializer, PeriodicTaskSerializer
from .models import Shorts
from celery.result import AsyncResult
from celery import current_app  
import time
import json
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

# 매일 오전 9시에 실행되는 크론 스케줄 만들기


class CrawlShorts(APIView):
    """
    유튜브 쇼츠 크롤링 작업 24시간 주기 반복 등록 api

    json 형태 {"urls" : list[str]}

    수집하는 항목 : 각 영상 당; 채널명, 영상 제목, 영상 링크, 업로드일, 조회수, 구독자 수
    """

    def get(self, request):
        try:
            tasks = PeriodicTask.objects.all()
            serializer = PeriodicTaskSerializer(tasks, many=True)
            return Response({"message": "모든 크롤링 작업 조회", "tasks": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "작업 조회 실패", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        try:
            urls = request.data.get("urls")
            task_name = request.data.get("task_name")

            # CrontabSchedule 생성 또는 가져오기 (매일 오전 3시 16분)
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute='43',
                hour='8',
                day_of_week='*',
                day_of_month='*',
                month_of_year='*',
            )

            # PeriodicTask 생성
            PeriodicTask.objects.create(
                crontab=schedule,  # interval 대신 crontab 사용
                name=task_name,
                task='crawl.tasks.crawl_shorts',
                args=json.dumps([urls]),
            )

            return Response({"message": "주기적인 크롤링 작업이 등록되었습니다."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        try:
            PeriodicTask.objects.all().delete()
            return Response({"message": "모든 크롤링 작업 취소"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TaskDetailStatus(APIView):
    def get(self, request):
        try:
            task_id = request.data.get("task_id")
            result = AsyncResult(task_id, app=current_app)
            data = {
                "task_id": task_id,
                "status": result.status,       # PENDING, SUCCESS, FAILURE ...
                "result": result.result,       # 결과 값 (있다면)
                "date_done": getattr(result, 'date_done', None),
            }
            return Response(data, status=status.HTTP_200_OK)
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
        