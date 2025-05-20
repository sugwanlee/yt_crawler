from celery import shared_task
from .crawler import get_info
from .models import Shorts
import requests

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"

def send_slack_message(text):
    payload = {"text": text}
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        # 슬랙 메시지 전송 실패시 로그 남기기 (선택 사항)
        print(f"Slack 메시지 전송 실패: {e}")



@shared_task
def crawl_shorts(urls):
    try:
        data = get_info(urls)
        print(f"작업 시작 : {urls}")
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
        print(f"작업 완료 : {urls}")
        send_slack_message(f"✅ 작업 성공!")
    except Exception as e:
        print(e)
        send_slack_message(f"❌ 작업 실패! 에러: {str(e)}")
        raise