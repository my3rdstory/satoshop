from django.urls import path

from . import views

app_name = "minihome"


urlpatterns = [
    path("<slug:slug>/", views.minihome_landing, name="landing"),
    path("<slug:slug>/preview/", views.minihome_preview, name="preview"),
    path("<slug:slug>/mng/", views.minihome_manage, name="manage"),
]
