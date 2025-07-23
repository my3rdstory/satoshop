from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json
from .models import Ranking, GamePlayHistory
from django.utils import timezone
import uuid

@login_required
def game_view(request):
    context = {
        'user_nickname': request.user.username
    }
    return render(request, 'game/selker/game.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def save_ranking(request):
    try:
        data = json.loads(request.body)
        ranking = Ranking.objects.create(
            nickname=data.get('nickname', 'Anonymous'),
            score=data.get('score', 0),
            wave=data.get('wave', 0),
            weapon_level=data.get('weapon_level', 0),
            play_time=data.get('play_time', 0)
        )
        return JsonResponse({
            'id': ranking.id,
            'rank': get_rank(ranking),
            'message': '랭킹이 저장되었습니다.'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@require_http_methods(["GET"])
def get_rankings(request):
    limit = int(request.GET.get('limit', 10))
    offset = int(request.GET.get('offset', 0))
    nickname = request.GET.get('nickname', None)
    
    rankings = Ranking.objects.all()
    if nickname:
        rankings = rankings.filter(nickname=nickname)
    
    total = rankings.count()
    rankings = rankings[offset:offset + limit]
    
    rankings_data = []
    for idx, ranking in enumerate(rankings, start=offset + 1):
        rankings_data.append({
            'id': ranking.id,
            'rank': idx,
            'nickname': ranking.nickname,
            'score': ranking.score,
            'wave': ranking.wave,
            'weapon_level': ranking.weapon_level,
            'play_time': ranking.play_time,
            'created_at': ranking.created_at.isoformat()
        })
    
    return JsonResponse({
        'rankings': rankings_data,
        'total': total
    })

@require_http_methods(["GET"])
def get_top_rankings(request):
    limit = int(request.GET.get('limit', 10))
    rankings = Ranking.objects.all()[:limit]
    
    rankings_data = []
    for idx, ranking in enumerate(rankings, start=1):
        rankings_data.append({
            'id': ranking.id,
            'rank': idx,
            'nickname': ranking.nickname,
            'score': ranking.score,
            'wave': ranking.wave,
            'weapon_level': ranking.weapon_level,
            'play_time': ranking.play_time,
            'created_at': ranking.created_at.isoformat()
        })
    
    return JsonResponse({'rankings': rankings_data})

def get_rank(ranking):
    return Ranking.objects.filter(score__gt=ranking.score).count() + 1

@csrf_exempt
@require_http_methods(["POST"])
def start_game(request):
    try:
        data = json.loads(request.body)
        session_id = str(uuid.uuid4())
        
        history = GamePlayHistory.objects.create(
            nickname=data.get('nickname', 'Anonymous'),
            started_at=timezone.now(),
            session_id=session_id
        )
        
        return JsonResponse({
            'session_id': session_id,
            'message': '게임이 시작되었습니다.'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def update_game(request):
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'error': '세션 ID가 필요합니다.'}, status=400)
        
        history = GamePlayHistory.objects.get(session_id=session_id)
        
        # 진행 상황 업데이트
        history.final_score = data.get('score', history.final_score)
        history.final_wave = data.get('wave', history.final_wave)
        history.final_weapon_level = data.get('weapon_level', history.final_weapon_level)
        history.enemies_killed = data.get('enemies_killed', history.enemies_killed)
        history.boss_killed = data.get('boss_killed', history.boss_killed)
        history.items_collected = data.get('items_collected', history.items_collected)
        
        history.save()
        
        return JsonResponse({'message': '게임 상태가 업데이트되었습니다.'})
    except GamePlayHistory.DoesNotExist:
        return JsonResponse({'error': '세션을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def end_game(request):
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'error': '세션 ID가 필요합니다.'}, status=400)
        
        history = GamePlayHistory.objects.get(session_id=session_id)
        
        # 최종 상태 업데이트
        history.ended_at = timezone.now()
        history.final_score = data.get('score', history.final_score)
        history.final_wave = data.get('wave', history.final_wave)
        history.final_weapon_level = data.get('weapon_level', history.final_weapon_level)
        history.enemies_killed = data.get('enemies_killed', history.enemies_killed)
        history.boss_killed = data.get('boss_killed', history.boss_killed)
        history.items_collected = data.get('items_collected', history.items_collected)
        history.is_completed = True
        
        history.save()
        
        return JsonResponse({
            'message': '게임이 종료되었습니다.',
            'play_duration': history.play_duration
        })
    except GamePlayHistory.DoesNotExist:
        return JsonResponse({'error': '세션을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
