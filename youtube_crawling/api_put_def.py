from youtube_crawling.models import YouTubeVideo, YouTubeProduct
import pandas as pd
import logging


# ----------------------------- ⬇️ logging 설정 -----------------------------

logger = logging.getLogger(__name__)  # logger.info(), logger.warning()만 써야해용

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
                        "product_merchant_link": row.get('url')
                    }
                )
        logger.info(f"🔁 영상 정보 업데이트 완료: {video_id}")
        return 1

    except YouTubeVideo.DoesNotExist:
        logger.warning(f"❌ 해당 video_id에 대한 영상이 없습니다: {video_id}")
        return 0