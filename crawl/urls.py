from django.urls import path
from . import views

urlpatterns = [
    path('shorts/task/', views.CrawlShorts.as_view()),
]
