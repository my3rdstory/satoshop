from __future__ import annotations

import logging
from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import WikiEntry
from .services import delete_entry_embedding, refresh_entry_embedding

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WikiEntry)
def handle_wiki_entry_save(sender: type[WikiEntry], instance: WikiEntry, **kwargs: Any) -> None:
    refresh_entry_embedding(instance.pk)


@receiver(post_delete, sender=WikiEntry)
def handle_wiki_entry_delete(sender: type[WikiEntry], instance: WikiEntry, **kwargs: Any) -> None:
    delete_entry_embedding(instance.pk)
