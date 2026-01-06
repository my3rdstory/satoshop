from django.urls import path

from . import views

app_name = "minihome"


urlpatterns = [
    path("", views.minihome_list, name="list"),
    path("<slug:slug>/", views.minihome_landing, name="landing"),
    path("<slug:slug>/gallery/add/", views.minihome_add_gallery_item, name="add_gallery_item"),
    path("<slug:slug>/gallery/update/", views.minihome_update_gallery_item, name="update_gallery_item"),
    path("<slug:slug>/gallery/delete/", views.minihome_delete_gallery_item, name="delete_gallery_item"),
    path("<slug:slug>/blog/add/", views.minihome_add_blog_post, name="add_blog_post"),
    path("<slug:slug>/blog/update/", views.minihome_update_blog_post, name="update_blog_post"),
    path("<slug:slug>/blog/delete/", views.minihome_delete_blog_post, name="delete_blog_post"),
    path("<slug:slug>/store/add/", views.minihome_add_store_item, name="add_store_item"),
    path("<slug:slug>/store/update/", views.minihome_update_store_item, name="update_store_item"),
    path("<slug:slug>/store/delete/", views.minihome_delete_store_item, name="delete_store_item"),
    path("<slug:slug>/preview/", views.minihome_preview, name="preview"),
    path("<slug:slug>/mng/", views.minihome_manage, name="manage"),
]
