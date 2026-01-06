from django.urls import path

from . import views

app_name = "minihome"


urlpatterns = [
    path("", views.minihome_list, name="list"),
    path("<slug:slug>/", views.minihome_landing, name="landing"),
    path("<slug:slug>/gallery/add/", views.minihome_add_gallery_item, name="add_gallery_item"),
    path("<slug:slug>/blog/add/", views.minihome_add_blog_post, name="add_blog_post"),
    path("<slug:slug>/preview/", views.minihome_preview, name="preview"),
    path("<slug:slug>/mng/", views.minihome_manage, name="manage"),
]
