from celery import shared_task
from .crawler import get_info
from .models import Shorts
from dotenv import load_dotenv
import requests
import os

load_dotenv()

# 슬랙 웹훅 URL
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# 슬랙 메시지 전달 함수
def send_slack_message(text):
    payload = {"text": text}
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        # 슬랙 메시지 전송 실패시 로그 남기기 (선택 사항)
        print(f"Slack 메시지 전송 실패: {e}")


# 셀러리 작업 데코레이션
@shared_task
# 크롤링 작업 및 DB 저장 함수
def crawl_shorts(urls, task_name):
    try:
        # 크롤링 작업 함수
        print(f"작업 시작 : {urls}")
        data = get_info(urls)
        # 수집된 쇼츠 정보 차례대로 DB에 저장
        for item in data:
            # 조회수에서 쉼표 제거하고 정수로 변환
            video_views = int(item["조회수"].replace(',', ''))
            
            Shorts.objects.create(
                stack_date = item["누적집계일"],
                channel_name = item["채널명"],
                video_title = item["영상 제목"],
                video_url = item["영상 링크"],
                upload_date = item["업로드일"],  # 이미 datetime이면 그대로
                video_views = video_views,  # 변환된 정수값 사용
                subscriber_count = item["구독자 수"]
            )
        print(f"작업 완료 : {urls}")
        # 성공 슬랙 알람 메시지
        send_slack_message(f"{task_name} 작업 성공!")
    except Exception as e:
        print(e)
        # 실패 슬랙 알람 메시지
        send_slack_message(f"{task_name} 작업 실패! 에러: {str(e)}")
        raise