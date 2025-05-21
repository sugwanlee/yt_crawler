# Auto YouTube Scraper

YouTube 데이터를 자동으로 수집하는 Django 기반 웹 애플리케이션입니다.

## 프로젝트 문서

프로젝트 상세 문서는 [여기](https://www.notion.so/1fa618b2be8b80a0b003f4c312269120?pvs=4)에서 확인할 수 있습니다.

## 기능

- YouTube 동영상 데이터 자동 수집
- Selenium을 이용한 웹 크롤링
- 수집된 데이터 Django DB 저장
- REST API 제공

## 기술 스택

- Python
- Django
- Django REST Framework
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
├── config/             # 프로젝트 설정
├── crawl/              # 크롤링 앱
│   ├── crawler.py     # 크롤링 로직
│   ├── models.py      # 데이터 모델
│   └── views.py       # API 뷰
├── venv/              # 가상환경
├── manage.py          # Django 관리 스크립트
├── requirements.txt   # 의존성 패키지
└── db.sqlite3         # SQLite 데이터베이스
```
