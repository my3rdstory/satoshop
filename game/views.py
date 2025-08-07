from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static

@login_required
def game_list(request):
    games = [
        {
            'title': 'To the Selker!',
            'description': '2D 탑뷰 서바이버 디펜스 게임',
            'url': '/minigame/selker/',
            'thumbnail': static('game/images/to-the-selker-cover.png'),
        }
    ]
    return render(request, 'game/game_list.html', {'games': games})
