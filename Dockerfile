FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    xauth \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

# Chrome 설치
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 파일 복사
COPY . /app/

# Python 경로 설정
ENV PYTHONPATH=/app

# 셀레니움 환경 변수 설정
ENV DISPLAY=:99
ENV PYTHONUNBUFFERED=1

# 포트 설정
EXPOSE 8000

# 실행 명령
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"] 