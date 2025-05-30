# Auto YouTube Scraper

YouTube 데이터를 자동으로 수집하는 Django 기반 웹 애플리케이션입니다.

## 프로젝트 문서

프로젝트 상세 문서는 [여기](https://www.notion.so/1fa618b2be8b80a0b003f4c312269120?pvs=4)에서 확인할 수 있습니다.

## 기능

- YouTube 동영상 데이터 자동 수집
- Selenium을 이용한 웹 크롤링
- 수집된 데이터 DB 저장
- REST API를 이용한 작업 등록 및 데이터 관리

## 기술 스택

- Python
- Django
- Django REST Framework
- Celery
- Celery Beat
- Selenium
- BeautifulSoup4
- Pandas
- SQLite3

## 설치 방법

1. 프로젝트 클론
```bash
git clone [repository-url]
cd auto_yt_scraper
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

4. 데이터베이스 마이그레이션
```bash
python manage.py migrate
```

5. 개발 서버 실행
```bash
python manage.py runserver
```

## 프로젝트 구조

```
auto_yt_scraper/
├── crawl/                   # 크롤링 앱
│   ├── migrations/           # DB 마이그레이션 파일
│   ├── __init__.py
│   ├── admin.py              # 관리자 페이지 설정
│   ├── apps.py               # 앱 설정
│   ├── crawler.py            # 크롤링 로직
│   ├── models.py             # DB 모델
│   ├── serializers.py        # 시리얼라이저
│   ├── tasks.py              # Celery 작업 --- 워커 작동부
│   ├── tests.py              
│   ├── urls.py               # URL 라우팅
│   └── views.py              # 뷰 로직
├── config/                   # 프로젝트 설정
│   ├── __init__.py
│   ├── celery.py             # Celery 설정
│   ├── settings.py           # 프로젝트 설정
│   ├── urls.py               # 메인 URL 설정
│   ├── asgi.py               # ASGI 설정
│   └── wsgi.py               # WSGI 설정
├── venv/                    # 가상환경
├── .dockerignore            # 도커 이그노어
├── .gitignore               # 깃 이그노어
├── Dockerfile               # 도커 설정
├── README.md                # 프로젝트 간단 설명
├── db.sqlite3               # SQLite DB -- 테스트용 DB
├── docker-compose.yml       # 도커 컴포즈 설정
├── manage.py                # Django 관리 스크립트
└── requirements.txt         # 파이썬 패키지 의존성
```
