from django.contrib import admin
from .models import Shorts

# Register your models here.

@admin.register(Shorts)
class ShortsAdmin(admin.ModelAdmin):
    list_display = ("channel_name", "video_title", "upload_date", "video_views", "subscriber_count", "stack_date")
    search_fields = ("channel_name", "video_title")
