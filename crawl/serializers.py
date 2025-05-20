from rest_framework import serializers
from .models import Shorts
from background_task.models import Task, CompletedTask
import requests
import json

class ShortsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shorts
        fields = "__all__"

class TaskSerializer(serializers.ModelSerializer):

    valid_urls = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = "__all__"

    def get_valid_urls(self, obj):
        urls = json.loads(obj.task_params)[0][0]
        for url in urls:
            response = requests.get(url)
            if response.status_code == 200 and "video unavailable" not in response.text.lower() and "존재하지 않는 채널입니다." not in response.text.lower() and "youtube" in url and "channel" in url:
                continue
            else:
                return False
        return True
    
class CompletedTaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompletedTask
        fields = "__all__"

