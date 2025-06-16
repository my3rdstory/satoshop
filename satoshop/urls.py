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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('myshop.urls')),
    path('accounts/', include('accounts.urls')),

    path('stores/', include('stores.urls')),
    path('products/', include('products.urls')),
    path('orders/', include('orders.urls')),
    path('ln_payment/', include('ln_payment.urls')),
    path('media/', include('storage.urls')),  # 보안 강화된 이미지 서빙
]

# WhiteNoise가 정적 파일 서빙을 자동으로 처리합니다
