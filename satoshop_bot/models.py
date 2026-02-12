from django.db import models


class DiscordBot(models.Model):
    """디스코드 봇 설정"""

    name = models.CharField(max_length=120, default='satoshop', verbose_name='봇 이름')
    application_id = models.CharField(max_length=40, blank=True, verbose_name='애플리케이션 ID')
    public_key = models.CharField(
        max_length=128,
        blank=True,
        verbose_name='인터랙션 공개키',
        help_text='디스코드 Developer Portal의 Public Key(16진수)',
    )
    token = models.CharField(max_length=220, verbose_name='봇 토큰')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시각')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정 시각')

    class Meta:
        verbose_name = '디스코드 봇'
        verbose_name_plural = '디스코드 봇'

    def __str__(self) -> str:
        return self.name

    @classmethod
    def get_active_bot(cls):
        return cls.objects.filter(is_active=True).order_by('-updated_at').first()


class DiscordChannel(models.Model):
    """디스코드 채널 설정"""

    bot = models.ForeignKey(
        DiscordBot,
        on_delete=models.CASCADE,
        related_name='channels',
        verbose_name='연결 봇',
    )
    server_name = models.CharField(max_length=120, blank=True, verbose_name='서버 이름')
    channel_name = models.CharField(max_length=120, blank=True, verbose_name='채널 이름')
    channel_id = models.CharField(max_length=40, verbose_name='채널 ID')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시각')

    class Meta:
        verbose_name = '디스코드 채널'
        verbose_name_plural = '디스코드 채널'
        constraints = [
            models.UniqueConstraint(fields=['bot', 'channel_id'], name='unique_discord_bot_channel'),
        ]
        ordering = ['-created_at']

    def __str__(self) -> str:
        label_parts = [part for part in [self.server_name, self.channel_name] if part]
        label = ' / '.join(label_parts) if label_parts else self.channel_id
        return f"{self.bot.name} - {label}"
