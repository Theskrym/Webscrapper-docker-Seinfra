from django.urls import path
from scraper.views import scraper_view, progress_stream

urlpatterns = [
    path('scraper/', scraper_view, name='scraper'),
    path('scraper/progress/', progress_stream, name='progress'),
]