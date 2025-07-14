"""
URL configuration for satoshop project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from myshop.views import service_worker_view, manifest_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myshop.urls')),
    path('accounts/', include('accounts.urls')),

    path('stores/', include('stores.urls')),
    path('products/', include('products.urls')),
    path('menu/', include('menu.urls')),
    path('orders/', include('orders.urls')),
    path('ln_payment/', include('ln_payment.urls')),
    path('boards/', include('boards.urls')),
    path('meetup/', include('meetup.urls')),
    path('lecture/', include('lecture.urls')),
    path('file/', include('file.urls')),
    path('media/', include('storage.urls')),  # 보안 강화된 이미지 서빙
    
    # PWA 관련 파일들을 루트에서 제공
    path('sw.js', service_worker_view, name='service_worker'),
    path('manifest.json', manifest_view, name='manifest'),
]

# 개발 환경에서 정적 파일 서빙
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# WhiteNoise가 정적 파일 서빙을 자동으로 처리합니다

# 에러 페이지 핸들러
handler404 = 'myshop.views.custom_404_view'
handler500 = 'myshop.views.custom_500_view'
