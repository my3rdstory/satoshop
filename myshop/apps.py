from django.apps import AppConfig
from django.contrib import admin


class MyshopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myshop'
    verbose_name = '1. 사이트 설정'
    
    def ready(self):
        # 기본 admin 사이트 설정
        admin.site.site_header = "SatoShop 관리자"
        admin.site.site_title = "SatoShop Admin"
        admin.site.index_title = '사이트 관리 대시보드'
