from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from django_celery_beat.models import PeriodicTask
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
import pytz
from .swagger import (
    crawl_shorts_get, crawl_shorts_post, crawl_shorts_delete,
    shorts_data_get, shorts_data_delete
)
# 매일 오전 9시에 실행되는 크론 스케줄 만들기


class CrawlShorts(APIView):
    """
    유튜브 쇼츠 크롤링 작업 24시간 주기 반복 등록 api

    json 형태 {"urls" : list[str]}

    수집하는 항목 : 각 영상 당; 채널명, 영상 제목, 영상 링크, 업로드일, 조회수, 구독자 수
    """

    @crawl_shorts_get
    def get(self, request):
        try:
            # ORM으로 작업 조회
            tasks = PeriodicTask.objects.all()
            # 시리얼라이저로 직렬화
            serializer = PeriodicTaskSerializer(tasks, many=True)
            # 응답 반환
            return Response({"message": "모든 크롤링 작업 조회", "tasks": serializer.data}, status=status.HTTP_200_OK)
        # 에러 발생 시 예외 처리
        except Exception as e:
            # 에러 반환
            return Response({"message": "작업 조회 실패", "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @crawl_shorts_post
    def post(self, request):
        try:
            # body에서 urls 가져오기
            urls = request.data.get("urls")
            # body에서 task_name 가져오기
            task_name = request.data.get("task_name")
            minute = request.data.get("minute")
            hour = request.data.get("hour")

            # 작업 주기 설정 (매일 오전 n시 m분) 
            schedule, created = CrontabSchedule.objects.get_or_create(
                minute=minute,
                hour=hour,
                day_of_week='*',
                day_of_month='*',
                month_of_year='*',
                timezone=pytz.timezone('Asia/Seoul')
            )

            # 작업 등록
            PeriodicTask.objects.create(
                crontab=schedule,
                name=task_name,
                task='crawl.tasks.crawl_shorts',        # 실행될 함수
                args=json.dumps([urls, task_name]),
            )
            # 응답 반환
            return Response({"message": "주기적인 크롤링 작업이 등록되었습니다."}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @crawl_shorts_delete
    def delete(self, request):
        try:
            PeriodicTask.objects.all().delete()
            return Response({"message": "모든 크롤링 작업 취소"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# 미사용 api
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

# 쇼츠 정보 api
class ShortsData(APIView):

    @shorts_data_get
    def get(self, request):
        try:
            # ORM으로 모든 쇼츠 정보 조회
            shorts = Shorts.objects.all()
            # 시리얼라이저로 직렬화
            serializer = ShortsSerializer(shorts, many=True)
            # 응답 반환
            return Response({"message" : "수집된 쇼츠 정보들 조회 완료", "data" : serializer.data}, status=status.HTTP_200_OK)
        # 에러 발생 시 예외 처리
        except Exception as e:
            # 에러 반환
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @shorts_data_delete
    def delete(self, request):
        try:
            # ORM으로 모든 쇼츠 정보 조회
            Shorts.objects.all().delete()
            # 시리얼라이저로 직렬화
            return Response({"message": "수집된 모든 쇼츠 정보 삭제"}, status=status.HTTP_200_OK)
        # 에러 발생 시 예외 처리
        except Exception as e:
            # 에러 반환
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        