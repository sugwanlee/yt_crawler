import pandas as pd
import time
import os
from .models import Shorts
from .utils import send_slack_message
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from datetime import datetime, timedelta
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
import time
import re

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
def get_driver():
    service = Service('/usr/bin/chromedriver')
    return webdriver.Chrome(service=service, options=options)

def get_views_and_upload_date(url, max_retries=10):
    attempt = 0
    while attempt < max_retries:
        driver = get_driver()
        wait = WebDriverWait(driver, 10)
        try:
            driver.get(url)

            # 클릭하기 전에 제목 가져오기
            title_elem = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ytShortsVideoTitleViewModelShortsVideoTitle")))

            if not title_elem:
                raise Exception("제목 정보를 찾을 수 없음")
            
            title = title_elem.text if title_elem else "[제목 없음]"

            search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "yt-shorts-video-title-view-model.ytShortsVideoTitleViewModelHostClickable")))
            search_box.click()

            # 페이지가 로드될 때까지 잠시 대기
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#title yt-formatted-string")))

            # BS4로 렌더링된 HTML 파싱
            soup = BeautifulSoup(driver.page_source, "html.parser")

            # 조회수 추출
            views_elem = soup.find(lambda tag: tag.has_attr("aria-label") and "조회수" in tag["aria-label"])
            views = views_elem["aria-label"].replace("조회수 ", "").replace("회", "").strip() if views_elem else "0"

            # 업로드 날짜 추출
            date_elem = soup.find(
                lambda tag: tag.has_attr("aria-label") and 
                (tag["aria-label"].count(".") >= 2 or "시간 전" in tag["aria-label"] or "분 전" in tag["aria-label"]) and 
                tag.find_parent("factoid-renderer") is not None
            )

            if not date_elem:
                raise Exception("날짜 정보를 찾을 수 없음")

            raw = date_elem["aria-label"]

            if "시간 전" in raw:
                hours = int(raw.replace("시간 전", "").strip())
                upload_date = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d")
            elif "분 전" in raw:
                minutes = int(raw.replace("분 전", "").strip())
                upload_date = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d")
            else:
                parts = [p.strip() for p in raw.replace(".", "").split()]
                year, month, day = parts
                month = month.zfill(2)
                day = day.zfill(2)
                upload_date = f"{year}-{month}-{day}"

            return title, views, upload_date

        except Exception as e:
            print(f"[에러] {url} 시도 {attempt + 1}/{max_retries}: {e}")
            attempt += 1
            time.sleep(1)  # 재시도 전 대기

        finally:
            driver.quit()

    # 모든 시도 실패
    raise Exception(f"[실패] {url} 모든 재시도 실패")

def get_channel_info(url):
    driver = get_driver()
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(url)

        channel_name = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='page-header']/yt-page-header-renderer/yt-page-header-view-model/div/div[1]/div/yt-dynamic-text-view-model/h1/span"))).text
        try:
            subscribers = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='page-header']/yt-page-header-renderer/yt-page-header-view-model/div/div[1]/div/yt-content-metadata-view-model/div[2]/span[1]"))).text
            
            subscribers = subscribers.replace("구독자 ", "").replace("명", "")
            if '만' in subscribers:
                num = float(subscribers.replace('만', ''))
                subscribers = int(num * 10_000)
            elif '천' in subscribers:
                num = float(subscribers.replace('천', ''))
                subscribers = int(num * 1_000)
            else:
                subscribers = int(subscribers)
        except TimeoutException:
            subscribers = "정보없음"
        
        return channel_name, subscribers
    finally:
        driver.quit()

def get_shorts_urls(url):
    driver = get_driver()
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(url)
        shorts_urls = set()
        last_urls_count = 0
        retry_count = 0
        max_retries = 2
        max_scroll_retries = 3

        while retry_count < max_retries:
            scroll_retries = 0

            while scroll_retries < max_scroll_retries:
                try:
                    # 요소 재조회
                    elements = driver.find_elements(By.XPATH, "//*[@id='content']/ytm-shorts-lockup-view-model-v2/ytm-shorts-lockup-view-model/a")
                    current_urls = set()

                    for elem in elements:
                        try:
                            href = elem.get_attribute("href")
                            if href and "shorts" in href:
                                current_urls.add(href)
                        except StaleElementReferenceException:
                            continue  # 무시하고 다음 요소로

                    shorts_urls.update(current_urls)

                    # 새로 추가된 URL이 없으면 retry 증가
                    if len(shorts_urls) == last_urls_count:
                        retry_count += 1
                    else:
                        retry_count = 0
                        last_urls_count = len(shorts_urls)
                        print(f"현재 수집된 Shorts 개수: {len(shorts_urls)}")

                    # 스크롤 전 높이 저장
                    last_height = driver.execute_script("return document.documentElement.scrollHeight")

                    # 스크롤 실행
                    driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                    time.sleep(1)  # DOM 안정화 대기

                    # 스크롤 완료 여부 확인
                    def is_scroll_complete(driver):
                        current_height = driver.execute_script("return document.documentElement.scrollHeight")
                        scroll_position = driver.execute_script("return window.pageYOffset + window.innerHeight")
                        return current_height > last_height or scroll_position >= current_height

                    try:
                        WebDriverWait(driver, 2).until(is_scroll_complete)
                        break  # 스크롤 완료, 내부 재시도 루프 탈출
                    except TimeoutException:
                        print("스크롤이 완료되지 않아 재시도합니다...")
                        scroll_retries += 1

                except Exception as e:
                    print(f"알 수 없는 에러 발생: {e}")
                    scroll_retries += 1

        return list(shorts_urls)

    finally:
        driver.quit()

stack_time = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%y%m%d-%H%M")
crawl_time = datetime.now().strftime("%Y-%m-%d")
file_name = f"shorts_info_{current_time}.csv"

def get_info(urls):
    data = []
    for url in urls:
        url = f'{url}/shorts'
        
        
        channel_name, subscribers = get_channel_info(url)
        shorts_urls = get_shorts_urls(url)

        for shorts_url in shorts_urls:
            try:
                title, views, upload_date = get_views_and_upload_date(shorts_url)
                data.append({
                    "누적집계일": stack_time,
                    "추출일": crawl_time,
                    "채널명": channel_name,
                    "영상 제목": title,
                    "영상 링크": shorts_url,
                    "업로드일": upload_date,
                    "조회수": views,
                    "구독자 수": subscribers
                })
                print(f'{title} 완료')
            except Exception:
                print(f"[에러] {shorts_url} 처리 중 크롤링 문제 발생")
                for i in range(3):
                    try:
                        title, views, upload_date = get_views_and_upload_date(shorts_url)
                        data.append({
                            "누적집계일": stack_time,
                            "추출일": crawl_time,
                            "채널명": channel_name,
                            "영상 제목": title,
                            "영상 링크": shorts_url,
                            "업로드일": upload_date,
                            "조회수": views,
                            "구독자 수": subscribers
                        })
                        print(f'{title} 재시도 성공')
                        break
                    except Exception as e:
                        print(f"[에러] {shorts_url} 재시도 중 문제 발생")
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
        print(f'{channel_name} 완료')

        send_slack_message(f'{channel_name} 수집 완료')
    return data