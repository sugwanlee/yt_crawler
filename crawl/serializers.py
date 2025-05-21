from rest_framework import serializers
from .models import Shorts
from django_celery_beat.models import PeriodicTask

# Shorts 테이블 시리얼라이저
class ShortsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shorts
        fields = "__all__"

# 주기 작업 테이블 시리얼리아저
class PeriodicTaskSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PeriodicTask
        fields = "__all__"

