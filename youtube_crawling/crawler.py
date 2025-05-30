# --------- 프로젝트에서 import한 목록 ---------------
from youtube_crawling.models import YouTubeVideo, YouTubeProduct
# --------- selenium에서 import한 목록 ---------------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# --------- webdriver에서 import한 목록 ---------------
from webdriver_manager.chrome import ChromeDriverManager
from contextlib import contextmanager # 드라이버 관리하는 태그
# --------- 그 외 크롤링 코드를 위해 import한 목록 ---------------
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Union, Dict, Optional
from urllib.parse import urlparse, unquote, parse_qsl
from django.db import transaction
import pandas as pd
import logging, time, re, json, os, urllib.parse


# ----------------------------- ⬇️ logging 설정 -----------------------------

logger = logging.getLogger(__name__)  # logger.info(), logger.warning()만 써야해용

# --------- driver 한 번으로 정의 ---------------
@contextmanager
def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")           # 샌드박스 비활성화 (보안 기능 해제)
    options.add_argument("--disable-dev-shm-usage")# 공유 메모리 사용 비활성화
    options.add_argument("--disable-gpu")          # GPU 하드웨어 가속 비활성화
    options.add_argument("--disable-extensions")   # 크롬 확장 프로그램 비활성화
    options.add_argument("--disable-infobars")     # 정보 표시줄 비활성화
    options.add_argument("--start-maximized")      # 브라우저 최대화
    options.add_argument("--disable-notifications")# 알림 비활성화
    options.add_argument('--ignore-certificate-errors')  # 인증서 오류 무시
    options.add_argument('--ignore-ssl-errors')    # SSL 오류 무시
    # User-Agent 설정
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    logger.info("🟢 ChromeDriver 실행")
    try:
        yield driver
    except Exception as e:
        logger.error(f"❌ WebDriver 예외 발생: {e}", exc_info=True)
        raise
    finally:
        driver.quit()
        logger.info("🛑 ChromeDriver 종료")


# ---------------------- ⬇️ URL 정리하는 함수 추가 ----------------------
def clean_youtube_url(url: str) -> str:
    """YouTube URL을 정리하는 함수"""
    try:
        # URL에서 'watch?v=' 부분이 중복되는지 확인
        if url.count('watch?v=') > 1:
            # 마지막 'watch?v=' 이후의 부분만 가져옴
            video_id = url.split('watch?v=')[-1]
            return f'https://www.youtube.com/watch?v={video_id}'
        return url
    except Exception as e:
        logger.error(f"❌ URL 정리 중 에러 발생: {e}")
        return url


# ----------------------------- ⬇️ 유튜브 채널의 영상 전부 가지고 오는 함수 -----------------------------
def get_all_video_ids(driver, channel_url):
    logger.info(f"🔍 채널 영상 ID 수집 시작: {channel_url}")

    try:
        videos_url = channel_url.rstrip('/') + "/videos"
        driver.get(videos_url)
        time.sleep(3)  # 페이지 로딩을 위한 대기 시간 증가

        video_urls = set()
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        
        SCROLL_PAUSE_TIME = 3
        MAX_RETRIES = 5
        retries = 0

        while True:
            # 스크롤 다운
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(SCROLL_PAUSE_TIME)
            
            # 영상 링크 수집
            elements = driver.find_elements(By.CSS_SELECTOR, 'a#video-title-link')
            for elem in elements:
                href = elem.get_attribute("href")
                if href and "watch?v=" in href:
                    # URL 정리 함수 적용
                    cleaned_url = clean_youtube_url(href)
                    video_urls.add(cleaned_url)

            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            if new_height == last_height:
                retries += 1
                if retries >= MAX_RETRIES:
                    break
            else:
                retries = 0
            last_height = new_height

        video_count = len(video_urls)
        if video_count > 0:
            logger.info(f"✅ 총 {video_count}개의 영상 URL 수집 완료")
        else:
            logger.warning("⚠️ 수집된 영상이 없습니다")

        return list(video_urls)
    except Exception as e:
        logger.error(f"❌ 영상 ID 수집 중 에러 발생: {e}")
        return []

# ----------------------------- ⬇️ element의 text 추출하는 유틸 함수 -----------------------------
def safe_get_text(element, default=""):
    try:
        return element.text.strip()
    except Exception:
        return default


# ---------------------- ⬇️ 조회수 텍스트에서 숫자만 추출 (예: 조회수 1,234회 -> 1234) ----------------------
def parse_view_count(text: str) -> int:
    try:
        if not text:
            return 0
        # 조회수와 회를 제거하고 숫자와 소수점, 단위(만)만 남김
        cleaned = text.replace("조회수", "").replace("회", "").replace(",", "").strip()
        
        # 백 단위가 있는 경우
        if "천" in cleaned:
            number = float(cleaned.replace("천", ""))
            return int(number * 1000)
        # 만 단위가 있는 경우
        elif "만" in cleaned:
            number = float(cleaned.replace("만", ""))
            return int(number * 10000)
        
        return int(cleaned)
    except ValueError as e:
        logger.warning(f"⚠️ 조회수 파싱 실패: '{text}', 이유: {e}")
        return 0


# -------------- ⬇️ 구독자 수 텍스트를 숫자 형태로 변환 (예: 1.2만명 -> 12000) ------------------
def parse_subscriber_count(text: str) -> int:
    try:
        if not text:
            return 0
        text = text.replace("구독자", "").replace("명", "").replace(",", "").strip()
        
        if "천" in text:
            number = float(text.replace("천", ""))
            return int(number * 1000)
        elif "만" in text:
            number = float(text.replace("만", ""))
            return int(number * 10000)
        elif "억" in text:
            number = float(text.replace("억", ""))
            return int(number * 100000000)
        
        return int(text) if text.strip().isdigit() else 0
    except Exception as e:
        logger.error(f"❌ 구독자 수 변환 실패: {text}, 에러: {e}")
        return 0
    
    
# ---------------------- ⬇️ 가격 텍스트를 정수로 변환하는 함수 추가 ----------------------
def parse_price(price_text: str) -> int:
    try:
        if not price_text or pd.isna(price_text):
            return 0
        # '₩' 기호와 쉼표 제거 후 숫자만 추출
        cleaned_price = re.sub(r'[₩,\s]', '', price_text)
        # 숫자가 있는 경우에만 변환
        if re.search(r'\d', cleaned_price):
            return int(re.sub(r'[^\d]', '', cleaned_price))
        return 0
    except Exception as e:
        logger.warning(f"⚠️ 가격 변환 실패: {price_text}, 에러: {e}")
        return 0


# ---------------------- ⬇️ 날짜를 YYYY-MM-DD 형식으로 변환 ----------------------
def format_date(date_str: str) -> datetime:
    """날짜 문자열을 datetime 객체로 변환"""
    try:
        if match := re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?', date_str):
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day))
        elif match := re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_str):
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day))
        elif match := re.search(r'(\d{4})(\d{2})(\d{2})', date_str):
            year, month, day = match.groups()
            return datetime(int(year), int(month), int(day))
        else:
            logger.warning(f"⚠️ 날짜 형식을 인식할 수 없음: {date_str}, 현재 날짜 사용")
            return datetime.now()
    except Exception as e:
        logger.error(f"❌ 날짜 변환 실패: {date_str}, 에러: {e}")
        return datetime.now()


# ---------------------- ⬇️ 설명란의 불필요한 줄바꿈 제거 ----------------------
def clean_description(text: str) -> str:
    if not text:
        return ""
    # 연속된 줄바꿈을 하나로 통일
    text = re.sub(r'\n\s*\n', '\n', text)
    # 앞뒤 공백 제거
    return text.strip()


# ---------------------- ⬇️ 제품 개수 텍스트에서 숫자 추출 (예: 5개 제품) ----------------------
def parse_product_count(text: str) -> Union[int, None]:
    try:
        if match := re.search(r'(\d+)\s*개\s*제품', text):
            return int(match.group(1))
    except:
        logger.warning(f"⚠️ 제품 개수 못 찾았는뎅??")
    return None

# ---------------------- ⬇️ 더보기 클릭 및 더보기란 텍스트 추출 ----------------------
def click_description(driver) -> str:
    try:
        # 스크롤을 내림으로써 버튼이 로드되도록 유도
        body = driver.find_element(By.TAG_NAME, 'body')
        for _ in range(3):
            body.send_keys(Keys.END)
            time.sleep(1)
        # 더보기 버튼 클릭 시도 (2가지 selector)
        try:
            expand_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "#expand"))
            )
            driver.execute_script("arguments[0].click();", expand_button)
            logger.info("더보기 버튼 클릭 성공")
        except Exception:
            logger.info("더보기 버튼 없음 또는 클릭 실패, 무시하고 진행")

        selectors = [
            "#description-text-container",
            "#description-inline-expander"
        ]
        for selector in selectors:
            try:
                elem = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                desc = elem.text.strip()
                if desc:
                    return desc
            except Exception:
                logger.debug(f"'{selector}'로 설명란 추출 실패, 다음 시도")
        logger.warning("더보기란에 설명이 없음")
        return "더보기란에 설명 없음"
        
    except Exception as e:
        logger.error(f"❌ 설명 추출 실패: {e}", exc_info=True)
        return "더보기란에 설명 없음"
    
    
#--------------------------------------- 제품 정보 추출 -------------------------------------
def extract_products_from_dom(driver, soup: BeautifulSoup) -> list[dict]:
    products = []
    try:
        # 더보기 버튼 클릭 시도
        try:
            more_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#expand"))
            )
            driver.execute_script("arguments[0].click();", more_button)
            logger.info("✅ 더보기 버튼 클릭 성공")
            time.sleep(2)  # 제품 정보가 로드될 때까지 대기
        except Exception as e:
            logger.info(f"더보기 버튼 클릭 실패 (이미 펼쳐져 있을 수 있음): {e}")

        # 제품 아이템 찾기 - 여러 셀렉터 시도
        product_selectors = [
            "#items > ytd-merch-shelf-item-renderer",
            "ytd-merch-shelf-renderer #items ytd-merch-shelf-item-renderer",
            "#merch-shelf #items ytd-merch-shelf-item-renderer",
            "ytd-merch-shelf-renderer ytd-merch-shelf-item-renderer",
            "#product-items ytd-merch-shelf-item-renderer"
        ]
        
        product_items = []
        for selector in product_selectors:
            product_items = soup.select(selector)
            if product_items:
                logger.info(f"✅ 제품 아이템 찾음: {selector}")
                break
                
        total_items = len(product_items)
        logger.info(f"총 {total_items}개의 제품 아이템을 찾았습니다.")

        '''250526 제품 정보 추출 수정'''
        for item in product_items:
            try:
                product_info = {}

                # 제품명 추출 - 여러 셀렉터 시도
                title_selectors = [
                    ".product-item-title",
                    ".title",
                    "h3",
                    "yt-formatted-string.title"
                ]
                
                title_text = None
                for selector in title_selectors:
                    title_elem = item.select_one(selector)
                    if title_elem and (title_text := title_elem.get_text(strip=True)):
                        product_info["title"] = title_text
                        logger.info(f"✅ 제품명 추출 성공: {title_text}")
                        break
                
                if not title_text:
                    logger.warning("⚠️ 제품명을 찾을 수 없어 다음 아이템으로 넘어갑니다")
                    continue

                # 제품 링크 추출 - 여러 셀렉터 시도
                link_selectors = [
                    ".product-item-description",
                    "a.yt-simple-endpoint",
                    "a[href]"
                ]
                
                product_url = None
                for selector in link_selectors:
                    link_elem = item.select_one(selector)
                    if link_elem:
                        if 'href' in link_elem.attrs:
                            product_url = link_elem['href']
                        else:
                            product_url = link_elem.get_text(strip=True)
                        if product_url:
                            product_info["url"] = product_url
                            logger.info(f"✅ 제품 링크 추출 성공: {product_url}")
                            break

                # 가격 추출 - 여러 셀렉터 시도
                price_selectors = [
                    ".product-item-price",
                    ".price",
                    "span.price",
                    "yt-formatted-string.price"
                ]
                
                price_text = None
                for selector in price_selectors:
                    price_elem = item.select_one(selector)
                    if price_elem and (price_text := price_elem.get_text(strip=True)):
                        product_info["price"] = price_text
                        logger.info(f"✅ 제품 가격 추출 성공: {price_text}")
                        break
                
                if not price_text:
                    logger.warning("⚠️ 가격 정보를 찾을 수 없어 다음 아이템으로 넘어갑니다")
                    continue

                # 250527 이미지 URL 추출 - 모든 이미지 URL에서 shopping? 포함된 것만 필터링
                try:
                    # 모든 이미지 URL 수집
                    all_img_urls = []
                    for img in soup.find_all('img'):
                        src = img.get('src', '')
                        if 'shopping?' in src:
                            all_img_urls.append(src)
                    
                    # 현재 제품에 해당하는 이미지 URL 찾기
                    if all_img_urls:
                        product_info["imageUrl"] = all_img_urls[0]
                        logger.info(f"✅ 쇼핑 이미지 URL 추출 성공: {all_img_urls[0]}")
                    else:
                        logger.warning("⚠️ shopping?을 포함한 이미지 URL을 찾을 수 없습니다")
                        product_info["imageUrl"] = ""
                        
                except Exception as e:
                    logger.error(f"❌ 이미지 URL 추출 중 에러 발생: {str(e)}")
                    product_info["imageUrl"] = ""

                # 판매처 추출 - 여러 셀렉터 시도
                merchant_selectors = [
                    ".product-item-merchant-text",
                    ".merchant",
                    "span.merchant",
                    "yt-formatted-string.merchant"
                ]
                
                merchant_text = None
                for selector in merchant_selectors:
                    merchant_elem = item.select_one(selector)
                    if merchant_elem and (merchant_text := merchant_elem.get_text(strip=True)):
                        merchant_name = merchant_text.replace("!", "").strip()
                        product_info["merchant"] = merchant_name
                        logger.info(f"✅ 판매처 추출 성공: {merchant_name}")
                        break

                # 제품명과 가격이 있는 경우만 저장
                if "title" in product_info and "price" in product_info:
                    products.append(product_info)
                    logger.info(f"✅ 제품 정보 추출 완료: {product_info['title']} ({product_info['price']})")

            except Exception as e:
                logger.error(f"❌ 제품 정보 추출 중 에러 발생: {str(e)}")
                continue

        logger.info(f"총 {len(products)}개의 제품 정보 추출 완료")
        return products

    except Exception as e:
        logger.error(f"❌ 전체 제품 추출 중 에러 발생: {e}")
        return []

# ---------------------- ⬇️ 영상 기본 정보: 제목, 채널명, 구독자 수, 조회수, 업로드일, 제품 개수 ----------------------
def base_youtube_info(driver, video_url: str) -> pd.DataFrame:
    logger.info("Crawling video: %s", video_url)
    today_str = datetime.today().strftime('%Y%m%d')

    try:
        driver.get(video_url)
        # 250525 페이지 로딩 대기 시간 증가
        time.sleep(5)  # 3초에서 5초로 증가
        
        # 페이지 스크롤을 여러 번 수행하여 동적 컨텐츠 로드
        for _ in range(5):  # 3회에서 5회로 증가
            driver.execute_script("window.scrollTo(0, window.scrollY + 500);")
            time.sleep(3)  # 2초에서 3초로 증가
        
        wait = WebDriverWait(driver, 20)
        
        # 250523 더보기 버튼 클릭 시도 (여러 셀렉터 시도)
        expand_button_selectors = [
            "tp-yt-paper-button#expand", "#expand", "#expand-button", "#more",
            "ytd-button-renderer#more", "ytd-expander#description [aria-label='더보기']",
            "ytd-expander[description-collapsed] #expand"
        ]
        
        for selector in expand_button_selectors:
            try:
                more_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                driver.execute_script("arguments[0].click();", more_button)
                logger.info(f"더보기 버튼 클릭 성공: {selector}")
                time.sleep(3)  # 더보기 클릭 후 컨텐츠 로드 대기
                break
            except:
                continue
                
        # 250523 제품 섹션 선택지 추가
        product_selectors = [
            "ytd-product-metadata-badge-renderer", "ytd-merch-shelf-renderer",
            "ytd-product-item-renderer","#product-shelf", "#product-list",
            "ytd-merch-product-renderer", "#product-items", ".product-item",
            "#content ytd-metadata-row-container-renderer",
            "ytd-metadata-row-renderer", "#product-section"
        ]
        
        for selector in product_selectors:
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                logger.info(f"제품 섹션 찾음: {selector}")
                break
            except:
                continue
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        soup_file_path = "/Users/mac/Desktop/minmin/intern/crawling_auto_code/soup_files"
        
        # soup_files 디렉토리가 없으면 생성
        if not os.path.exists(soup_file_path):
            os.makedirs(soup_file_path)
            
        # 현재 날짜를 YYYYMMDD 형식으로 가져오기
        today_str = datetime.now().strftime("%y%m%d")
        
        # 오늘 날짜의 파일들을 찾아서 가장 큰 번호 찾기
        existing_files = [f for f in os.listdir(soup_file_path) if f.endswith(f"_{today_str}.txt")]
        current_number = 1

        # 메타데이터 추출
        video_id = video_url.split("v=")[-1]
        
        '''250522 제목 (여러 선택자 시도)'''
        title_selectors = [
            "h1.title yt-formatted-string",
            "h1.title",
            "#title h1",
            "#container h1.style-scope.ytd-watch-metadata"
        ]
        title = None
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    break
        title = title or "제목 없음"
        logger.info(f"제목: {title}")

        '''250522 채널명 (여러 선택자 시도)'''
        channel_selectors = [
            "ytd-channel-name yt-formatted-string#text a",
            "ytd-channel-name a",
            "#channel-name a"
        ]
        channel_name = None
        for selector in channel_selectors:
            channel_tag = soup.select_one(selector)
            if channel_tag:
                channel_name = channel_tag.text.strip()
                break
        channel_name = channel_name or "채널 없음"

        '''250522 구독자 수'''
        sub_selectors = [
            "yt-formatted-string#owner-sub-count",
            "#subscriber-count"
        ]
        subscriber_count = None
        for selector in sub_selectors:
            sub_tag = soup.select_one(selector)
            if sub_tag:
                subscriber_count = sub_tag.text.strip()
                break
        subscriber_count = subscriber_count or "구독자 수 없음"

        '''250522 조회수'''
        view_selectors = [
            "span.view-count",
            "#view-count",
            "ytd-video-view-count-renderer"
        ]
        view_count = None
        for selector in view_selectors:
            view_tag = soup.select_one(selector)
            if view_tag:
                view_count = view_tag.text.strip()
                break
        view_count = view_count or "조회수 없음"

        '''250522 업로드일'''
        date_selectors = [
            "#info-strings yt-formatted-string",
            "#upload-info .date",
            "ytd-video-primary-info-renderer yt-formatted-string.ytd-video-primary-info-renderer:not([id])"
        ]
        upload_date = None
        for selector in date_selectors:
            date_tag = soup.select_one(selector)
            if date_tag:
                upload_date = date_tag.text.strip()
                break
        upload_date = upload_date or "날짜 없음"

        '''250522 설명란'''
        desc_selectors = [
            "ytd-expander#description yt-formatted-string",
            "#description",
            "#description-inline-expander",
            "#description-text-container"
        ]
        description = None
        for selector in desc_selectors:
            desc_tag = soup.select_one(selector)
            if desc_tag:
                description = desc_tag.text.strip()
                if description:
                    break
        description = description or "설명 없음"
        logger.info(f"설명 길이: {len(description)} 글자")

        '''250522 제품 개수'''
        # HTML에서 제품 개수 직접 추출 시도
        try:
            product_count_elem = soup.select_one("yt-formatted-string#info")
            if product_count_elem:
                text_content = product_count_elem.get_text()
                # "n개 제품" 패턴 찾기
                if match := re.search(r'(\d+)개\s*제품', text_content):
                    product_count = int(match.group(1))
                    logger.info(f"✅ HTML에서 제품 개수 추출 성공: {product_count}개")
                else:
                    product_count = 0
                    logger.warning("⚠️ HTML에서 제품 개수를 찾을 수 없음")
            else:
                product_count = 0
                logger.warning("⚠️ 제품 개수 요소를 찾을 수 없음")
        except Exception as e:
            logger.error(f"❌ HTML에서 제품 개수 추출 실패: {e}")
            product_count = 0

        # 제품 정보 추출
        products = extract_products_from_dom(driver, soup)
        if products is None:
            products = []
            
        # HTML에서 추출한 제품 개수가 0이고, 실제 제품이 있는 경우에만 실제 개수 사용
        if product_count == 0 and products:
            product_count = len(products)
            logger.info(f"✅ 실제 추출된 제품 개수 사용: {product_count}개")
        
        logger.info(f"✅ 최종 제품 개수: {product_count}개")

        # 기본 데이터 세트
        base_data = []
        
        # 250523 제품이 있는 경우, 각 제품별로 row 생성
        if products:
            for product in products:
                row_data = {
                    "youtube_id": video_id,
                    "title": title,
                    "channel_name": channel_name,
                    "subscribers": subscriber_count,
                    "view_count": view_count,
                    "upload_date": upload_date,
                    "extracted_date": today_str,
                    "video_url": video_url,
                    "description": description,
                    "product_count": product_count,  # HTML에서 추출한 제품 개수 사용
                    "product_name": product.get("title", ""),
                    "product_price": product.get("price", ""),
                    "product_image_url": product.get("imageUrl", ""),
                    "product_merchant_url": product.get("url", ""),
                    "product_merchant": product.get("merchant", "")
                }
                base_data.append(row_data)
        else:
            # 제품이 없는 경우 기본 정보만 저장
            base_data.append({
                "youtube_id": video_id,
                "title": title,
                "channel_name": channel_name,
                "subscribers": subscriber_count,
                "view_count": view_count,
                "upload_date": upload_date,
                "extracted_date": today_str,
                "video_url": video_url,
                "description": description,
                "product_count": product_count,
                "product_name": "",
                "product_price": "",
                "product_image_url": "",
                "product_merchant_url": "",
                "product_merchant": ""
            })

        logger.info(f"📦 수집된 데이터 행 개수: {len(base_data)}")
        return pd.DataFrame(base_data)
    
    except Exception as e:
        logger.error(f"❌ base_youtube_info 예외: {e}", exc_info=True)
        return pd.DataFrame()

# ----------------------------------------------- ⬇️ 유튜브 영상 URL 접속 후 데이터 수집 수행 -----------------------------------------------

def collect_video_data(driver, video_id: str, index: int = None, total: int = None) -> pd.DataFrame:
    # URL 정리
    base_url = clean_youtube_url(f"https://www.youtube.com/watch?v={video_id}")
    
    try:
        driver.get(base_url)
        if index is not None and total is not None:
            logger.info(f"\n📹 ({index}/{total}) 크롤링 중: {video_id}")

        df = base_youtube_info(driver, base_url)

        logger.info(f"📦 수집된 제품 개수: {len(df)}")
        if df.empty:
            logger.warning(f"⚠️ 데이터프레임이 비어 있음: {video_id}")

        return df
    
    except Exception as e:
            logger.error(f"❌ 예외 발생 - collect_video_data(): {video_id} | 에러: {e}")
            return None

# ------------------------------------- ⬇️ 크롤링된 유튜브 영상을 조회하고 수정하는 코드 ------------------------------
def update_youtube_data_to_db(dataframe: pd.DataFrame) -> int:
    if dataframe.empty:
        return 0

    video_id = dataframe.iloc[0]['video_id']
    
    try:
        video = YouTubeVideo.objects.get(video_id=video_id)
        row = dataframe.iloc[0]

        # 기존 영상 정보 업데이트
        video.extracted_date = row['extracted_date']
        video.upload_date = row['upload_date']
        video.channel_name = row['channel_name']
        video.subscriber_count = row['subscriber_count']
        video.video_url = row['video_url']
        video.title = row['title']
        video.view_count = row['view_count']
        video.product_count = row['product_count']
        video.description = row['description']
        video.save()

        # 기존 제품 정보 삭제 후 새로 저장
        video.products.all().delete()

        # pd.DataFrame == dataframe
        for _, row in dataframe.iterrows():
            product_name = row.get('product_name')
            if product_name and pd.notna(product_name):
                product, created = YouTubeProduct.objects.update_or_create(
                    video=video,
                    product_name=row.get('title', '제품 없음'),
                    defaults={
                        "product_price": row.get('price'),
                        "product_image_link": row.get('imageUrl'),
                        "product_merchant_link": row.get('url'),
                        "product_merchant": row.get('merchant', '')
                    }
                )
        logger.info(f"🔁 영상 정보 업데이트 완료: {video_id}")
        return 1

    except YouTubeVideo.DoesNotExist:
        logger.warning(f"❌ 해당 video_id에 대한 영상이 없습니다: {video_id}")
        return 0

# ------------------------------------- ⬇️ 채널 URL에서 고유한 ID 추출 (예: UCxxxx 또는 @handle 형식) ------------------------------
def get_channel_id_from_url(channel_url):
    parsed = urlparse(channel_url)
    parts = parsed.path.strip("/").split("/")
    return parts[-1] if parts else "unknown_channel"

# ------------------------------------- ⬇️ 채널 이름을 YouTube 채널 페이지에서 가져옴 ------------------------------
def get_channel_name(driver, channel_url):
    driver.get(channel_url)
    driver.implicitly_wait(5)
    try:
        title_element = driver.find_element("xpath", '//meta[@property="og:title"]')
        channel_name = title_element.get_attribute("content")
        # URL 디코딩된 채널명 반환
        decoded_name = urllib.parse.unquote(channel_name)
        return decoded_name  # slugify 제거하여 한글 유지
    except Exception as e:
        logger.warning(f"⚠️ 채널명 추출 실패: {e}")
        return "unknown_channel"

# ------------------------------------- ⬇️ URL 유효성 검사 및 정리 ------------------------------
def validate_url(url: str) -> str:
    try:
        if not url:
            return ""
        # URL 스키마가 없는 경우 추가
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        # URL 인코딩
        return urllib.parse.quote(url, safe=':/?=&')
    except Exception as e:
        logger.error(f"❌ URL 검증 실패: {url}, 에러: {e}")
        return ""
    
# ------------------------------------- ⬇️ DB에 저장하는 함수 ------------------------------
def save_to_db(data: pd.DataFrame):
    if data is None or data.empty:
        logger.warning("⚠️ 저장할 데이터가 없습니다.")
        return 0

    saved_count = 0
    updated_count = 0
    
    try:
        with transaction.atomic():
            for video_id, video_group in data.groupby('youtube_id'):
                if not video_id:
                    logger.warning("⚠️ video_id 없음, 건너뜁니다")
                    continue

                first_row = video_group.iloc[0]
                
                try:
                    # 날짜 변환
                    extracted_date = format_date(first_row.get("extracted_date", ""))
                    upload_date = format_date(first_row.get("upload_date", ""))
                    
                    # 숫자 데이터 변환
                    subscriber_count = parse_subscriber_count(first_row.get("subscribers", "0"))
                    view_count = parse_view_count(first_row.get("view_count", "0"))
                    
                    # HTML에서 추출한 제품 개수 사용 (첫 번째 행에서만 가져옴)
                    product_count = int(first_row.get("product_count", 0))
                    logger.info(f"✅ 비디오 {video_id}의 제품 개수: {product_count}개")
                    
                    # URL 검증
                    video_url = validate_url(first_row.get("video_url", ""))
                    
                    # 영상 정보 생성 또는 업데이트
                    video_obj, created = YouTubeVideo.objects.update_or_create(
                        video_id=video_id,
                        defaults={
                            "extracted_date": extracted_date,
                            "upload_date": upload_date,
                            "channel_name": first_row.get("channel_name", ""),
                            "subscriber_count": subscriber_count,
                            "title": first_row.get("title", ""),
                            "view_count": view_count,
                            "video_url": video_url,
                            "product_count": product_count,  # HTML에서 추출한 제품 개수 사용
                            "description": clean_description(first_row.get("description", "")),
                        }
                    )

                    if created:
                        logger.info(f"✨ 새로운 영상 생성: {video_id}")
                    else:
                        logger.info(f"🔄 기존 영상 업데이트: {video_id}")
                        updated_count += 1

                    # 기존 제품 정보 삭제
                    video_obj.products.all().delete()
                    
                    # 제품 정보 처리
                    for _, row in video_group.iterrows():
                        product_name = row.get("product_name", "").strip()
                        if product_name:
                            try:
                                price = parse_price(row.get("product_price", "0"))
                                product_image_link = validate_url(row.get("product_image_url", ""))
                                product_merchant_link = validate_url(row.get("product_merchant_url", ""))
                                
                                product, created = YouTubeProduct.objects.update_or_create(
                                    video=video_obj,
                                    product_name=product_name,
                                    defaults={
                                        "product_price": price,
                                        "product_image_link": product_image_link,
                                        "product_merchant": row.get("product_merchant", ""),
                                        "product_merchant_link": product_merchant_link
                                    }
                                )
                                saved_count += 1
                                if created:
                                    logger.info(f"✨ 새로운 제품 정보 저장: {product_name} (가격: {price:,}원)")
                                else:
                                    logger.info(f"🔄 기존 제품 정보 업데이트: {product_name} (가격: {price:,}원)")
                            except Exception as e:
                                logger.error(f"❌ 제품 정보 저장 중 에러 발생 ({product_name}): {e}")
                                continue
                except Exception as e:
                    logger.error(f"❌ 영상 정보 처리 중 에러 발생 ({video_id}): {e}")
                    continue

    except Exception as e:
        logger.error(f"❌ DB 저장 중 에러 발생: {e}", exc_info=True)
        return 0

    logger.info(f"✅ 총 {updated_count}개의 영상이 업데이트되었고, {saved_count}개의 제품이 저장되었습니다.")
    return saved_count

# ------------------------------------- ⬇️ CSV용으로 데이터 전처리하는 함수 ------------------------------
def preprocess_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['view_count'] = df['view_count'].apply(parse_view_count)
    df['subscribers'] = df['subscribers'].apply(parse_subscriber_count)
    df['product_price'] = df['product_price'].apply(parse_price)
    df['description'] = df['description'].apply(clean_description)
    df['upload_date'] = df['upload_date'].apply(format_date)
    df['extracted_date'] = df['extracted_date'].apply(format_date)
    return df

# ------------------------------------- ⬇️ CSV로 저장하는 함수 ------------------------------
# def save_to_csv(df: pd.DataFrame, directory: str, channel_name: str) -> str:
#     df = preprocess_df(df)
#     try:
#         today_str = datetime.now().strftime("%Y%m%d")
        
#         # 디렉토리가 없으면 생성
#         os.makedirs(directory, exist_ok=True)

#         # URL 인코딩된 채널명을 디코딩
#         decoded_channel_name = urllib.parse.unquote(channel_name)
        
#         # 채널명에서 특수문자 제거하고 공백을 언더스코어로 변경
#         safe_channel_name = "".join(c for c in decoded_channel_name.replace(" ", "_") if c.isalnum() or c in ('_',)).rstrip()

#         # 해당 날짜와 채널 이름의 기존 파일 확인
#         pattern = f"[0-9]{{2}}_{safe_channel_name}_{today_str}.csv"
#         existing_files = [
#             f for f in os.listdir(directory)
#             if re.match(pattern, f)
#         ]

#         # 다음 번호 결정
#         if not existing_files:
#             next_number = 1
#         else:
#             numbers = []
#             for f in existing_files:
#                 try:
#                     num = int(f.split('_')[0])
#                     numbers.append(num)
#                 except (ValueError, IndexError):
#                     continue
#             next_number = max(numbers, default=0) + 1

#         # 파일명 생성
#         file_name = f"{next_number:02d}_{safe_channel_name}_{today_str}.csv"
#         file_path = os.path.join(directory, file_name)

#         # CSV 저장
#         df.to_csv(file_path, index=False, encoding='utf-8-sig')
#         logger.info(f"💾 CSV 저장 완료: {file_path}")
#         return file_path
        
#     except Exception as e:
#         logger.error(f"❌ CSV 저장 실패: {e}", exc_info=True)
#         return None


# ------------------------------------- ⬇️ 유튜브 채널의 전체 크롤링을 실행하는 함수 ------------------------------
def crawl_channel_videos(channel_url: str):
    with create_driver() as driver:
        video_ids = get_all_video_ids(driver, channel_url)

        total = len(video_ids)
        if total == 0:
            logger.warning("❌ 채널에서 수집된 영상 ID가 없습니다.")
            return
        
        logger.info(f"총 {total}개 영상 크롤링 시작")
        all_data = pd.DataFrame()

        for i, video_id in enumerate(video_ids, start=1):
            try:
                logger.info(f"\n🔍 ({i}/{total}) 영상 크롤링 시작: {video_id}")
                df = collect_video_data(driver, video_id)
                if df is not None and not df.empty:
                    all_data = pd.concat([all_data, df], ignore_index=True)
                    save_to_db(df)
                    logger.info(f"✅ ({i}/{total}) 영상 크롤링 완료: {video_id}")
            except Exception as e:
                logger.error(f"❌ ({i}/{total}) 영상 크롤링 중 에러 발생: {video_id}, 에러: {e}", exc_info=True)

        # if not all_data.empty:
        #     try:
        #         # 채널명 가져오기
        #         channel_name = get_channel_name(driver, channel_url)
                
        #         # CSV 저장
        #         csv_path = save_to_csv(all_data, save_path, channel_name)
        #         if csv_path:
        #             logger.info(f"✅ CSV 파일 저장 완료: {csv_path}")
        #         else:
        #             logger.error("❌ CSV 파일 저장 실패")
        #     except Exception as e:
        #         logger.error(f"❌ CSV 저장 중 에러 발생: {e}", exc_info=True)
        # else:
        #     logger.warning("⚠️ 크롤링 결과 데이터 없음")

# ------------------------------------- ⬇️ 크롤링 메인 실행부 ------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    urls = [
        "https://www.youtube.com/@%EC%B9%A1%EC%B4%89",
    ]

    for url in urls:
        try:
            logger.info(f"🚀 채널 크롤링 시작: {url}")
            crawl_channel_videos(url)
            logger.info(f"✅ 채널 크롤링 완료: {url}")

        except Exception as e:
            logger.warning(f"❌ 채널 크롤링 중 오류 발생: {url} - {e}")
        
        time.sleep(1)  # 각 채널 간 1초 쉬었다가 다음 채널 실행
