from rest_framework import serializers
from .models import Shorts
from django_celery_beat.models import PeriodicTask

class ShortsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shorts
        fields = "__all__"

class PeriodicTaskSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PeriodicTask
        fields = "__all__"

