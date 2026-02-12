import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from stores.models import BahPromotionRequest

from .discord_commands import fetch_bot_guild_ids, sync_discord_application_commands
from .models import DiscordBot
from .services import notify_bah_promotion_request

logger = logging.getLogger(__name__)


@receiver(post_save, sender=BahPromotionRequest)
def send_bah_promotion_request_notification(sender, instance: BahPromotionRequest, created: bool, **kwargs) -> None:
    if getattr(instance, '_skip_discord_notification', False):
        return

    is_new = getattr(instance, '_discord_is_new', created)

    def _send():
        try:
            notify_bah_promotion_request(instance, is_new=is_new)
        except Exception:
            logger.exception('BAH 홍보요청 디스코드 알림 전송 중 오류 발생', extra={'request_id': instance.id})

    transaction.on_commit(_send)


@receiver(post_save, sender=DiscordBot)
def sync_discord_commands_on_bot_save(sender, instance: DiscordBot, **kwargs) -> None:
    """디스코드 봇 설정 저장 시 슬래시 명령어를 자동 동기화한다."""
    if not instance.is_active:
        return
    if not instance.application_id or not instance.token:
        logger.info(
            "디스코드 명령어 자동 동기화 생략(application_id/token 누락) bot_id=%s",
            instance.id,
        )
        return

    def _sync():
        try:
            guild_ids = fetch_bot_guild_ids(instance)
            summary = sync_discord_application_commands(
                instance,
                guild_ids=guild_ids,
                sync_global=False,
                clear_global_when_guild_only=True,
            )
            logger.info(
                "디스코드 명령어 자동 동기화 완료 bot_id=%s global=%s cleared=%s guilds=%s",
                instance.id,
                summary.get("global_count"),
                summary.get("global_cleared"),
                len(summary.get("guild_results") or []),
            )
        except Exception:
            logger.exception("디스코드 명령어 자동 동기화 실패 bot_id=%s", instance.id)

    transaction.on_commit(_sync)
