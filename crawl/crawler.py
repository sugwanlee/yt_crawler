import pandas as pd
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
# 크롬 옵션 설정
options = Options()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--start-maximized")
options.add_argument("--disable-gpu")
options.add_argument("--headless=new")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

# 조회수와 업로드 날짜 추출
def get_views_and_upload_date(url):
    # 웹 드라이버 초기화
    driver = webdriver.Chrome(options=options)

    # 웹 페이지 로드 대기
    wait = WebDriverWait(driver, 10)

    # 웹 페이지 로드
    driver.get(url)
    
    # 영상 상세정보 클릭
    search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "yt-shorts-video-title-view-model.ytShortsVideoTitleViewModelHostClickable")))
    search_box.click()
    
    # 페이지가 로드될 때까지 잠시 대기
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#title yt-formatted-string")))
    
    # BS4로 렌더링된 HTML 파싱
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 1) 제목 추출
    # div#title 안의 yt-formatted-string 전체 텍스트
    title_elem = soup.select_one("div#title yt-formatted-string")
    title = title_elem.get_text(strip=True)

    # 2) 조회수 추출 (aria-label에 '조회수' 포함)
    views_elem = soup.find(lambda tag: tag.has_attr("aria-label") and "조회수" in tag["aria-label"])
    views = int(views_elem["aria-label"].replace("조회수 ", "").replace("회", "").strip().replace(",", ""))

    # 3) 업로드 날짜 추출 (aria-label에 마침표 두 번 이상)
    date_elem = soup.find(
        lambda tag: tag.has_attr("aria-label") and tag["aria-label"].count(".") >= 2
    )
    try:
        raw = date_elem["aria-label"]
        # "2025. 5. 2." -> ["2025", "5", "2"]
        parts = [p.strip() for p in raw.replace(".", "").split()]
        year, month, day = parts

        # 두 자리 포맷 적용
        month = month.zfill(2)
        day   = day.zfill(2)

        upload_date = f"{year}-{month}-{day}"  # -> "2025-05-02"
    except TypeError as e:
        print(f"[에러] {url} 처리 중 날짜 문제 발생: {e}")
        upload_date = datetime.now().strftime("%Y-%m-%d")
        print("오늘 날짜로 처리")
    driver.close()
    return title, views, upload_date


def get_channel_info(url):
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    driver.get(url)

    channel_name = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='page-header']/yt-page-header-renderer/yt-page-header-view-model/div/div[1]/div/yt-dynamic-text-view-model/h1/span"))).text
    subscribers = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='page-header']/yt-page-header-renderer/yt-page-header-view-model/div/div[1]/div/yt-content-metadata-view-model/div[2]/span[1]"))).text
    subscribers = subscribers.replace("구독자 ", "").replace("명", "")

    if '만' in subscribers:
        num = float(subscribers.replace('만', ''))
        subscribers = int(num * 10_000)
    
    # '천' 단위
    elif '천' in subscribers:
        num = float(subscribers.replace('천', ''))
        subscribers = int(num * 1_000)
    
    # 그 외: 이미 정수 문자열
    else:
        subscribers = int(subscribers)
    
    driver.close()
    return channel_name, subscribers

# 채널 내 모든 Shorts 영상 링크 추출
def get_shorts_urls(url):
    # 웹 드라이버 초기화
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        # 채널 페이지 로드
        driver.get(url)
        
        # 스크롤 일시정지 시간
        SCROLL_PAUSE_TIME = 2

        # Shorts 영상 링크 저장 집합
        shorts_urls = set()

        # 스크롤 높이
        last_height = driver.execute_script("return document.documentElement.scrollHeight")

        while True:
            # 스크롤 내리기
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")

            # 페이지 로드 완료 대기
            WebDriverWait(driver, SCROLL_PAUSE_TIME).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # Shorts 영상 링크 추출 
            elements = driver.find_elements(By.XPATH, "//*[@id='content']/ytm-shorts-lockup-view-model-v2/ytm-shorts-lockup-view-model/a")
            for element in elements:
                shorts_urls.add(element.get_attribute("href"))

            # 스크롤 높이 업데이트
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            print(f"현재 수집된 Shorts 개수: {len(shorts_urls)}")

            # 스크롤 높이가 변경되지 않았으면 종료
            if new_height == last_height:
                WebDriverWait(driver, SCROLL_PAUSE_TIME).until(
                    lambda d: d.execute_script("return document.documentElement.scrollHeight") == new_height
                )
                break
            last_height = new_height

        return list(shorts_urls)
    finally:
        driver.close()

# 추출일과 누적집계일 설정
current_time = datetime.now().strftime("%Y-%m-%d")
stack_time = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# 채널 내 모든 Shorts 영상 정보 추출
def get_info(urls):
    # 추출 데이터 저장 리스트
    data = []

    # 각 채널에 대해 반복
    for url in urls:
        url = f'{url}/shorts/'
        # 채널 정보 추출
        try:
            channel_name, subscribers = get_channel_info(url)
            
            # Shorts 영상 링크 추출
            shorts_urls = get_shorts_urls(url)
            
            channel_name, subscribers = get_channel_info(url)
            shorts_urls = get_shorts_urls(url)
        except Exception as e:
            print(f'작업실패 : {e}')
            raise


        # 각 Shorts 영상에 대해 반복
        for shorts_url in shorts_urls:
            try:
                # 영상 상세정보 추출
                title, views, upload_date = get_views_and_upload_date(shorts_url)
                data.append({
                    "누적집계일" : stack_time,
                    "추출일": current_time,
                    "채널명": channel_name,
                    "영상 제목": title,
                    "영상 링크": shorts_url,
                    "업로드일": upload_date,
                    "조회수": views,
                    "구독자 수": subscribers
                })
                print(f'{title} 완료')
                
            except Exception :
                print(f"[에러] {shorts_url} 처리 중 크롤링 문제 발생")
                for i in range(3):
                    try:
                        title, views, upload_date = get_views_and_upload_date(shorts_url)
                        data.append({
                            "누적집계일" : stack_time,
                            "추출일": current_time,
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
    return data