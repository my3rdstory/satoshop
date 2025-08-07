from django.contrib import admin
from django.db.models import Avg, Count, Sum, Max
from django.utils.html import format_html
from .models import Ranking, GamePlayHistory

@admin.register(Ranking)
class RankingAdmin(admin.ModelAdmin):
    list_display = ['rank_display', 'nickname', 'score', 'wave', 'weapon_level', 'play_time', 'created_at']
    list_filter = ['created_at', 'wave', 'weapon_level']
    search_fields = ['nickname']
    ordering = ['-score', '-wave', 'created_at']
    readonly_fields = ['created_at']
    
    def rank_display(self, obj):
        # 점수 기준으로 순위 계산
        rank = Ranking.objects.filter(score__gt=obj.score).count() + 1
        return f"#{rank}"
    
    rank_display.short_description = '순위'


@admin.register(GamePlayHistory)
class GamePlayHistoryAdmin(admin.ModelAdmin):
    list_display = ['nickname', 'started_at_display', 'play_duration_display', 'final_score', 
                    'final_wave', 'final_weapon_level', 'enemies_killed', 'boss_killed', 
                    'items_collected', 'status_display']
    list_filter = ['is_completed', 'started_at', 'final_wave', 'final_weapon_level']
    search_fields = ['nickname', 'session_id']
    ordering = ['-started_at']
    readonly_fields = ['session_id', 'started_at', 'ended_at', 'play_duration']
    date_hierarchy = 'started_at'
    
    def started_at_display(self, obj):
        return obj.started_at.strftime('%Y-%m-%d %H:%M:%S')
    started_at_display.short_description = '시작 시간'
    
    def play_duration_display(self, obj):
        return obj.play_duration_formatted
    play_duration_display.short_description = '플레이 시간'
    
    def status_display(self, obj):
        if obj.is_completed:
            return format_html('<span style="color: green;">✓ 종료</span>')
        else:
            return format_html('<span style="color: orange;">● 진행중</span>')
    status_display.short_description = '상태'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs
    
    def changelist_view(self, request, extra_context=None):
        # 통계 정보 추가
        queryset = self.get_queryset(request)
        completed_games = queryset.filter(is_completed=True)
        
        stats = completed_games.aggregate(
            total_games=Count('id'),
            avg_score=Avg('final_score'),
            max_score=Max('final_score'),
            avg_wave=Avg('final_wave'),
            max_wave=Max('final_wave'),
            avg_play_time=Avg('play_duration'),
            total_enemies=Sum('enemies_killed'),
            total_bosses=Sum('boss_killed'),
            total_items=Sum('items_collected')
        )
        
        # 평균 플레이 시간 포맷팅
        if stats['avg_play_time']:
            avg_minutes = int(stats['avg_play_time']) // 60
            avg_seconds = int(stats['avg_play_time']) % 60
            stats['avg_play_time_formatted'] = f"{avg_minutes}분 {avg_seconds}초"
        else:
            stats['avg_play_time_formatted'] = "0분 0초"
        
        extra_context = extra_context or {}
        extra_context['stats'] = stats
        
        return super().changelist_view(request, extra_context=extra_context)
    
