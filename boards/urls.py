from django.urls import path
from . import views

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
] 