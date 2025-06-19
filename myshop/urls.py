from django.urls import path
from . import views

app_name = 'myshop'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/exchange-rate/', views.get_exchange_rate, name='get_exchange_rate'),
    path('api/convert-currency/', views.convert_currency, name='convert_currency'),
    path('webhook/update-exchange-rate/', views.update_exchange_rate_webhook, name='update_exchange_rate_webhook'),
    path('document/<str:doc_type>/', views.document_view, name='document'),
    path('offline/', views.offline_view, name='offline'),
] 