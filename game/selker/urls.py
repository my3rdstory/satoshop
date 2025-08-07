from django.urls import path
from . import views

app_name = 'selker'
urlpatterns = [
    path('', views.game_view, name='game'),
    path('api/rankings/', views.save_ranking, name='save_ranking'),
    path('api/rankings/list/', views.get_rankings, name='get_rankings'),
    path('api/rankings/top/', views.get_top_rankings, name='get_top_rankings'),
    path('api/game/start/', views.start_game, name='start_game'),
    path('api/game/update/', views.update_game, name='update_game'),
    path('api/game/end/', views.end_game, name='end_game'),
]