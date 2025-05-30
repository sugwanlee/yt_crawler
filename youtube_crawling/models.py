from django.db import models

class YouTubeVideo(models.Model):
    video_id = models.CharField(max_length=255, unique=True)
    extracted_date = models.DateField()
    upload_date = models.DateField()
    channel_name = models.CharField(max_length=255)
    subscriber_count = models.BigIntegerField(default=0)
    title = models.CharField(max_length=500)
    view_count = models.BigIntegerField(default=0)
    video_url = models.URLField(max_length=500, unique=True)
    product_count = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['extracted_date']),
            models.Index(fields=['upload_date']),
            models.Index(fields=['channel_name']),
        ]

    def __str__(self):
        return self.title


class YouTubeProduct(models.Model):
    video = models.ForeignKey(YouTubeVideo, on_delete=models.CASCADE, related_name='products')
    product_name = models.CharField(max_length=500)
    product_price = models.BigIntegerField(default=0)
    product_image_link = models.URLField(max_length=500, blank=True)
    product_merchant = models.CharField(max_length=255, blank=True)
    product_merchant_link = models.URLField(max_length=500, blank=True)

    class Meta:
        unique_together = ('video', 'product_name')
        indexes = [
            models.Index(fields=['product_price']),
            models.Index(fields=['product_merchant']),
        ]

    def __str__(self):
        return f"{self.product_name} (₩{self.product_price:,})"