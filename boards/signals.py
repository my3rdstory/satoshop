"""Signal handlers for cache invalidation in boards app."""

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .cache_utils import (
    invalidate_meme_detail_cache,
    invalidate_meme_list_cache,
    invalidate_notice_detail_cache,
    invalidate_notice_list_cache,
)
from .models import MemePost, MemeTag, Notice, NoticeComment


@receiver(post_save, sender=Notice)
@receiver(post_delete, sender=Notice)
def invalidate_notice_cache(sender, **kwargs):
    update_fields = kwargs.get('update_fields')
    if update_fields:
        if set(update_fields) == {'views'}:
            return

    invalidate_notice_list_cache()
    invalidate_notice_detail_cache()


@receiver(post_save, sender=NoticeComment)
@receiver(post_delete, sender=NoticeComment)
def invalidate_notice_comment_cache(sender, **kwargs):
    invalidate_notice_detail_cache()


@receiver(post_save, sender=MemePost)
@receiver(post_delete, sender=MemePost)
def invalidate_meme_cache(sender, **kwargs):
    invalidate_meme_list_cache()
    invalidate_meme_detail_cache()


@receiver(post_save, sender=MemeTag)
@receiver(post_delete, sender=MemeTag)
def invalidate_meme_tag_cache(sender, **kwargs):
    invalidate_meme_list_cache()
    invalidate_meme_detail_cache()


@receiver(m2m_changed, sender=MemePost.tags.through)
def invalidate_meme_tags_relationship_cache(sender, **kwargs):
    invalidate_meme_list_cache()
    invalidate_meme_detail_cache()
