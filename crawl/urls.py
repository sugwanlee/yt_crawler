from django.urls import path
from . import views


urlpatterns = [
    # 셀러리 작업 관리 api
    path('task/', views.CrawlShorts.as_view()),
    # 셀러리 완료 작업 api 미사용중
    # path('shorts/task/status/', views.TaskDetailStatus.as_view()),

    # 수집된 쇼츠 정보 관리 api
    path('', views.ShortsData.as_view()),
]
