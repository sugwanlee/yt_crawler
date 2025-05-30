import json, logging
from rest_framework import viewsets
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from django_celery_beat.models import PeriodicTask, CrontabSchedule

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from ..models import YouTubeVideo, YouTubeProduct
from youtube_crawling.serializers.video_ids_serializers import YouTubeVideoSerializer, ProductSerializer
from youtube_crawling.crawler import collect_video_data, save_to_db
from youtube_crawling.api_put_def import update_youtube_data_to_db

from youtube_crawling.tasks import crawl_channel_videos

# ------------------------------------- ⬇️ 크롤링 자동화 딸깍 클래스 -------------------------------

class ChannelCrawlTriggerView(APIView):
    
    @swagger_auto_schema(
        operation_summary="자동 크롤링할 유튜브 URL 목록 입력",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'urls': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='자동 크롤링할 유튜브 채널 URL 목록을 입력해주세요.',
                ),
                'task_name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='작업 이름을 입력해주세요.',
                ),
                'minute': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='실행할 분을 입력해주세요 (0-59)',
                ),
                'hour': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='실행할 시간을 입력해주세요 (0-23)',
                ),
            },
            required=['urls', 'task_name', 'minute', 'hour'],
            example={
                'urls': ["https://www.youtube.com/channel/example1", "https://www.youtube.com/channel/example2"],
                'task_name': "daily_crawl_task",
                'minute': "0",
                'hour': "9"
            }
        ),
        responses={202: '크롤링이 시작되었습니다.'}
    )
    def post(self, request):
        urls = request.data.get("urls")
        if not urls:
            return Response({"error": "urls를 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        task_name = request.data.get("task_name")
        if not task_name:
            return Response({"error": "task_name을 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        minute = request.data.get("minute")
        if not minute:
            return Response({"error": "minute를 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        hour = request.data.get("hour")
        if not hour:
            return Response({"error": "hour를 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        schedule, created = CrontabSchedule.objects.get_or_create(
            minute=minute,
            hour=hour,
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )

        task_path = 'youtube_crawling.tasks.crawl_channels_task'

        PeriodicTask.objects.create(
            crontab=schedule,
            name=task_name,
            task=task_path,        # 실행될 함수
            args=json.dumps([urls, task_name]),
        )

        return Response({"message": f"{len(urls)}개의 크롤링이 시작되었습니다."}, status=202)
    
    
    @swagger_auto_schema(
        operation_summary="크롤링한 유튜브 영상 전체 조회")
    
    def get(self, request):
        """전체 영상 목록 조회"""
        queryset = YouTubeVideo.objects.all().order_by('-extracted_date')
        serializer = YouTubeVideoSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ------------------------------------- ⬇️ API CRUD 클래스 (전체 작업)-------------------------------
class YoutubeLongFormCrawlAPIView(APIView):

    @swagger_auto_schema(
        operation_summary="크롤링할 다수의 유튜브 영상 ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'video_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='크롤링할 유튜브 영상 ID 리스트를 입력해주세요.',
                ),
            },
            required=['video_ids'],
            example={
                'video_ids': ['youtube id 1', 'youtube id 2','youtube id 3']
            }
        ),
        responses={201: '성공적으로 저장된 영상 개수와 실패한 ID 리스트 반환'}
    )
    
# ------------------------------------- ⬇️ API POST 함수(성공한 동영상 수, 실패한 영상 video_id 출력)-------------------------------
    def post(self, request):
        video_ids = request.data.get("video_ids", [])
        if not video_ids:
            return Response({"error": "video_ids를 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        
        # 크롬 옵션 설정
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--headless=new")
        options.add_argument("--log-level=3")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--lang=ko-KR")  # 한국어 설정
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        options.add_experimental_option("prefs", {
            "intl.accept_languages": "ko,ko-KR"
        })
        saved_count = 0
        failed_ids = []

        service = Service('/usr/bin/chromedriver')
        with webdriver.Chrome(service=service, options=options) as driver:

            for index, vid in enumerate(video_ids, start=1):
                try:
                    df = collect_video_data(driver, vid, index=index, total=len(video_ids))
                    if df is not None and not df.empty:
                        save_to_db(df)
                        saved_count += 1
                    else:
                        failed_ids.append(vid)
                except Exception as e:
                    print(f"[❌ 오류] {vid} 처리 중: {e}")
                    failed_ids.append(vid)

        return Response({
            "message": f"{saved_count}개 영상 저장 완료",
            "failed_ids": failed_ids
        }, status=status.HTTP_201_CREATED)
    
# ------------------------------------- ⬇️ API GET 함수 (전체 영상 목록 조회)-------------------------------
    @swagger_auto_schema(
        operation_summary="크롤링한 유튜브 영상 전체 조회")
    
    def get(self, request):
        """전체 영상 목록 조회"""
        queryset = YouTubeVideo.objects.all().order_by('-extracted_date')
        serializer = YouTubeVideoSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# ------------------------------------- ⬇️ API DELETE 함수 (video_id로 삭제)-------------------------------
    @swagger_auto_schema(
        operation_summary="크롤링한 유튜브 영상 전체 삭제",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'video_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='삭제할 유튜브 영상 ID 리스트',
                ),
            },
            required=['video_ids'],
            example={
                'video_ids': ['id1', 'id2']
            }
        ),
        responses={200: '삭제된 영상 수'}
    )
    def delete(self, request):
        video_ids = request.data.get("video_ids", [])
        if not video_ids:
            return Response({"error": "video_ids를 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        deleted, _ = YouTubeVideo.objects.filter(video_id__in=video_ids).delete()
        return Response({"message": f"{deleted}개 영상 삭제 완료"}, status=status.HTTP_200_OK)
    
# ------------------------------------- ⬇️ API PUT 함수(영상 video_id로 삭제)-------------------------------
    @swagger_auto_schema(
        operation_summary="유튜브 영상 정보 업데이트",
        operation_description="video_id를 기반으로 유튜브 영상을 크롤링하여 DB에 저장된 정보를 최신화합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'video_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='업데이트할 유튜브 영상 ID',
                ),
            },
            required=['video_id'],
            example={'video_id': 'dQw4w9WgXcQ'}
        ),
        responses={
        200: openapi.Response(
            description="업데이트된 영상 정보",
            examples={
                "application/json": {
                    "message": "업데이트 완료",
                    "video_id": "dQw4w9WgXcQ",
                    "title": "New Video Title",
                    "view_count": "123456",
                    "subscriber_count": "1.23M",
                    # ...생략
                }
            }
        ),
        500: openapi.Response(description="업데이트 실패 메시지")
        }
    )
    def put(self, request):
        video_id = request.data.get("video_id")
        if not video_id:
            return Response({"error": "video_id를 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)


        # 크롬 옵션 설정
        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--headless=new")
        options.add_argument("--log-level=3")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--lang=ko-KR")  # 한국어 설정
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        options.add_experimental_option("prefs", {
            "intl.accept_languages": "ko,ko-KR"
        })
        service = Service('/usr/bin/chromedriver')
        try:
            with webdriver.Chrome(service=service, options=options) as driver:
                df = collect_video_data(driver, video_id)
                update_youtube_data_to_db(df)
            return Response({"message": f"{video_id} 업데이트 완료"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"{video_id} 업데이트 실패: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ---------------------- ⬇️ API GET 함수 (특정 영상 한 개 조회) ---------------------------------------------
class YouTubeVideoOneAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="유튜브 영상 1개 정보 조회 ",
        operation_description="video_id로 특정 유튜브 영상 조회",
        manual_parameters=[
            openapi.Parameter(
                'video_id', openapi.IN_PATH,
                description="유튜브 영상 video_id",
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: YouTubeVideoSerializer(),
            404: '영상이 존재하지 않습니다.'
        }
    )
    def get(self, request, video_id):
        try:
            video = YouTubeVideo.objects.get(video_id=video_id)
        except YouTubeVideo.DoesNotExist:
            return Response({"detail": "해당 영상이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = YouTubeVideoSerializer(video)
        return Response(serializer.data, status=status.HTTP_200_OK)

# ---------------------- ⬇️ API DELETE 함수 (특정 영상 한 개 삭제) ---------------------------------------------

    @swagger_auto_schema(
        operation_summary="유튜브 영상 1개 삭제",
        operation_description="video_id로 특정 유튜브 영상 삭제",
        manual_parameters=[
            openapi.Parameter(
                'video_id', openapi.IN_PATH,
                description="삭제할 유튜브 영상 video_id",
                type=openapi.TYPE_STRING
            )
        ],
        responses={
            200: "삭제 성공 메시지",
            404: "영상이 존재하지 않습니다."
        }
    )
    def delete(self, request, video_id):
        try:
            video = YouTubeVideo.objects.get(video_id=video_id)
            video.delete()
            return Response({"message": f"{video_id} 삭제 완료"}, status=status.HTTP_200_OK)
        except YouTubeVideo.DoesNotExist:
            return Response({"error": "해당 영상이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)
        
# ---------------------- ⬇️ API PATCH 함수 (특정 영상 한 개의 컬럼 하나하나 수정) ---------------------------------------------

    @swagger_auto_schema(
        operation_summary="크롤링된 유튜브 영상 정보 수동 수정",
        operation_description="특정 영상의 특정 컬럼 수정하기",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'video_id': openapi.Schema(type=openapi.TYPE_STRING, description='수정할 영상 ID'),
                'extracted_date' : openapi.Schema(type=openapi.TYPE_STRING, description='추출일 변경'),
                'upload_date' : openapi.Schema(type=openapi.TYPE_STRING, description='영상 업로드일 변경'),
                'channel_name' : openapi.Schema(type=openapi.TYPE_STRING, description='채널명 변경'),
                'subscriber_count' : openapi.Schema(type=openapi.TYPE_STRING, description='구독자 수 변경'),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='새로운 제목'),
                'view_count': openapi.Schema(type=openapi.TYPE_INTEGER, description='조회 수 변경'),
                'video_url': openapi.Schema(type=openapi.TYPE_STRING, description='영상 링크 변경'),
                'product_count' : openapi.Schema(type=openapi.TYPE_STRING, description='제품 수 변경'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='설명 변경')
            },
            required=['video_id'],
            example={
                'video_id': '',
                'extracted_date': 'YYYYMMDD',
                'upload_date': 'YYYYMMDD',
                'channel_name': '',
                'subscriber_count': '',
                'title': '',
                'view_count': 1400,
                'video_url': 'url을 따옴표 없이 넣어주세요',
                'product_count': '',
                'description': '',
            }
        ),
        responses={200: '수정 성공', 404: '영상 없음'}
    )
    def patch(self, request):
        allowed_fields = [
        'extracted_date', 'upload_date', 'channel_name', 'subscriber_count',
        'title', 'view_count', 'video_url', 'product_count', 'description'
    ]

        video_id = request.data.get("video_id")
        if not video_id:
            return Response({"error": "video_id를 제공해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            video = YouTubeVideo.objects.get(video_id=video_id)

            updated = False
            for field in allowed_fields:
                if field in request.data:
                    setattr(video, field, request.data[field])
                    updated = True

            if updated:
                video.save()
                return Response({"message": f"{video_id} 수정 완료"})
            else:
                return Response({"message": "수정할 필드가 제공되지 않았습니다."}, status=400)

        except YouTubeVideo.DoesNotExist:
            return Response({"error": "해당 영상이 존재하지 않습니다."}, status=404)

class YouTubeVideoViewSet(viewsets.ModelViewSet):
    queryset = YouTubeVideo.objects.all().order_by('-extracted_date')
    serializer_class = YouTubeVideoSerializer

class YouTubeProductViewSet(viewsets.ModelViewSet):
    queryset = YouTubeProduct.objects.all().order_by('video_id')
    serializer_class = ProductSerializer    