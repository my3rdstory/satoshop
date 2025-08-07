from django.urls import path
from . import views
from . import meme_views

app_name = 'boards'

urlpatterns = [
    # 공지사항 URL
    path('notice/', views.NoticeListView.as_view(), name='notice_list'),
    path('notice/<int:pk>/', views.NoticeDetailView.as_view(), name='notice_detail'),
    path('notice/create/', views.notice_create, name='notice_create'),
    path('notice/<int:pk>/edit/', views.notice_edit, name='notice_edit'),
    path('notice/<int:pk>/delete/', views.notice_delete, name='notice_delete'),
    
    # 댓글 URL
    path('notice/<int:notice_pk>/comment/', views.comment_create, name='comment_create'),
    path('comment/<int:comment_pk>/edit/', views.comment_edit, name='comment_edit'),
    path('comment/<int:comment_pk>/delete/', views.comment_delete, name='comment_delete'),
    
    # 밈 게시판 URL
    path('meme/', meme_views.MemeListView.as_view(), name='meme_list'),
    path('meme/<int:pk>/', meme_views.MemeDetailView.as_view(), name='meme_detail'),
    path('meme/create/', meme_views.meme_create, name='meme_create'),
    path('meme/<int:pk>/edit/', meme_views.meme_edit, name='meme_edit'),
    path('meme/<int:pk>/delete/', meme_views.meme_delete, name='meme_delete'),
    path('meme/upload/', meme_views.meme_upload_image, name='meme_upload_image'),
    path('meme/tags/', meme_views.get_tag_cloud, name='meme_tag_cloud'),
    path('meme/<int:pk>/stat/', meme_views.meme_increment_stat, name='meme_increment_stat'),
] 