from django.urls import path, include
from . import views

app_name = 'game'

urlpatterns = [
    path('', views.game_list, name='game_list'),
    path('selker/', include('game.selker.urls')),
]