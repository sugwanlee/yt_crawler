from celery import shared_task
from youtube_crawling.crawler import crawl_channel_videos
import logging, time, datetime, urllib.parse, os

logger = logging.getLogger(__name__)

@shared_task
def crawl_channels_task(urls, *args, **kwargs):

    today_str = datetime.datetime.now().strftime("%Y%m%d")

    for url in urls:
        try:
            logger.info(f"🚀 채널 시작: {url}")
            
            # 크롤링 시작 전 충분한 대기 시간 확보
            logger.info("⏳ 페이지 로딩 대기 중...")
            time.sleep(5)  # 5초로 증가
            
            crawl_channel_videos(url)
            
            logger.info(f"✅ 채널 완료: {url}")
            
            # 다음 채널 크롤링 전 대기
            logger.info("⏳ 다음 채널 크롤링 전 대기 중...")
            time.sleep(5)  # 5초로 증가
            
        except Exception as e:
            logger.error(f"❌ 오류 발생 - {url}: {e}")
            logger.error("상세 에러:", exc_info=True)
