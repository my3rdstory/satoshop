from django.urls import path, re_path
from . import views

app_name = 'storage'

urlpatterns = [
    # S3 파일 프록시 서빙
    re_path(r'^s3/(?P<file_path>.+)$', views.serve_s3_file, name='serve_s3_file'),
    
    # 리다이렉트 방식 (백업용)
    re_path(r'^s3-redirect/(?P<file_path>.+)$', views.serve_s3_file_redirect, name='serve_s3_file_redirect'),
] 