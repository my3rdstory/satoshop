from django.db import models
from django.utils import timezone

class Ranking(models.Model):
    nickname = models.CharField(max_length=50, verbose_name='닉네임')
    score = models.IntegerField(verbose_name='점수')
    wave = models.IntegerField(default=0, verbose_name='웨이브')
    weapon_level = models.IntegerField(default=0, verbose_name='무기 레벨')
    play_time = models.IntegerField(default=0, verbose_name='플레이 시간(초)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 일시')
    
    class Meta:
        verbose_name = '랭킹'
        verbose_name_plural = '랭킹 목록'
        ordering = ['-score', '-wave', 'created_at']
    
    def __str__(self):
        return f"{self.nickname} - {self.score}점"


class GamePlayHistory(models.Model):
    nickname = models.CharField(max_length=50, verbose_name='닉네임')
    started_at = models.DateTimeField(verbose_name='시작 시간')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='종료 시간')
    final_score = models.IntegerField(default=0, verbose_name='최종 점수')
    final_wave = models.IntegerField(default=1, verbose_name='최종 웨이브')
    final_weapon_level = models.IntegerField(default=1, verbose_name='최종 무기 레벨')
    play_duration = models.IntegerField(default=0, verbose_name='플레이 시간(초)')  # 계산된 값
    enemies_killed = models.IntegerField(default=0, verbose_name='처치한 적 수')
    boss_killed = models.IntegerField(default=0, verbose_name='처치한 보스 수')
    items_collected = models.IntegerField(default=0, verbose_name='획득한 아이템 수')
    is_completed = models.BooleanField(default=False, verbose_name='정상 종료')
    session_id = models.CharField(max_length=100, unique=True, verbose_name='세션 ID')
    
    class Meta:
        verbose_name = '게임플레이 히스토리'
        verbose_name_plural = '게임플레이 히스토리'
        ordering = ['-started_at']
    
    def __str__(self):
        status = '진행중' if not self.is_completed else '종료'
        return f"{self.nickname} - {self.started_at.strftime('%Y-%m-%d %H:%M')} ({status})"
    
    def save(self, *args, **kwargs):
        # 플레이 시간 자동 계산
        if self.ended_at and self.started_at:
            delta = self.ended_at - self.started_at
            self.play_duration = int(delta.total_seconds())
        super().save(*args, **kwargs)
    
    @property
    def play_duration_formatted(self):
        """MM:SS 형식으로 플레이 시간 반환"""
        minutes = self.play_duration // 60
        seconds = self.play_duration % 60
        return f"{minutes:02d}:{seconds:02d}"
