from django.urls import path
from . import views

urlpatterns = [
    path('shorts/', views.CrawlShorts.as_view()),
]
