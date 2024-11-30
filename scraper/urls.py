from django.urls import path
from . import views

urlpatterns = [
    path('', views.scraper_view, name='scraper'),
]