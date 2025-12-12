from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path("v1/", views.api_index, name="api_index"),
    path("v1/docs/", views.api_docs, name="api_docs"),
    path("v1/stores/", views.store_feed, name="store_feed"),
    path("v1/stores/<str:store_id>/owner/", views.store_owner_info, name="store_owner_info"),
]
