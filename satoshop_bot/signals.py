import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from stores.models import BahPromotionRequest

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
