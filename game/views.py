from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def game_list(request):
    games = [
        {
            'title': 'To the Selker!',
            'description': '2D 탑뷰 서바이버 디펜스 게임',
            'url': '/minigame/selker/',
            'thumbnail': None,
        }
    ]
    return render(request, 'game/game_list.html', {'games': games})
