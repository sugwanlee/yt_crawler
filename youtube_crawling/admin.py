from django.contrib import admin
from .models import YouTubeVideo, YouTubeProduct

# 제품 정보를 영상 상세 페이지에서 함께 보기 위해 Inline 설정
class YouTubeProductInline(admin.TabularInline):
    model = YouTubeProduct
    extra = 0  # 추가 폼 안 보이게

@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'channel_name', 'upload_date', 'view_count', 'product_count')
    search_fields = ('title', 'channel_name')
    inlines = [YouTubeProductInline]

@admin.register(YouTubeProduct)
class YouTubeProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'product_price', 'product_image_link', 'product_merchant', 'product_merchant_link')
