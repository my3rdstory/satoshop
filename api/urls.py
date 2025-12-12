from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("v1/", views.api_index, name="api_index"),
    path("v1/explorer/", views.api_explorer, name="api_explorer"),
    path("v1/stores/", views.store_feed, name="store_feed"),
]
