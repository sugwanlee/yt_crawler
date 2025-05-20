from django.urls import path
from . import views


urlpatterns = [
    # '/shorts/task/' 로 들어오면 views.py 의 CrawlShorts 클래스에서 api 처리
    path('shorts/task/', views.CrawlShorts.as_view()),
    path('shorts/task/status/', views.TaskDetailStatus.as_view()),
    path('shorts/', views.ShortsData.as_view())
]
