from rest_framework import serializers
from youtube_crawling.models import YouTubeVideo, YouTubeProduct

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = YouTubeProduct
        fields = '__all__'

class YouTubeVideoSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)

    class Meta:
        model = YouTubeVideo
        fields = '__all__'
