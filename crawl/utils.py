import requests
import os
from dotenv import load_dotenv

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