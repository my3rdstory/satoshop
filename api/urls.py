from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("v1/stores/", views.store_feed, name="store_feed"),
]
