from background_task import background
from .crawler import get_info
from .models import Shorts


@background(schedule=0)
def crawl_shorts(urls):
    try:
        data = get_info(urls)
    except Exception as e:
        print(e)
        raise
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