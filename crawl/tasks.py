from celery import shared_task
from .crawler import get_info
from .models import Shorts
from .utils import send_slack_message
from dotenv import load_dotenv
import requests
import os
import time
from datetime import datetime

load_dotenv()

# 셀러리 작업 데코레이션
@shared_task
# 크롤링 작업 및 DB 저장 함수
def crawl_shorts(urls, task_name):
    try:
        # 크롤링 작업 함수
        print(f"작업 시작 : {urls}")
        start_time = datetime.now()
        send_slack_message(f"---------------------------------------------------------\n{start_time.strftime("%y-%m-%d %H:%M:%S")} : {task_name} 작업 중 . . .")
        data = get_info(urls)
        # 수집된 쇼츠 정보 차례대로 DB에 저장
        print(f"작업 완료 : {urls}")
        # 성공 슬랙 알람 메시지
        end_time = datetime.now()
        send_slack_message(f"{end_time.strftime('%y-%m-%d %H:%M:%S')} : {task_name} 작업 성공!\n작업시간 : {str(end_time - start_time)[:-7]}\n---------------------------------------------------------")
    except Exception as e:
        print(e)
        # 실패 슬랙 알람 메시지
        send_slack_message(f"{end_time.strftime('%y-%m-%d %H:%M:%S')} : {task_name} 작업 실패! 에러: {str(e)}\n---------------------------------------------------------")
        raise