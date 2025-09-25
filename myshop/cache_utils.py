"""Utilities for local in-memory caching within the myshop app."""

from django.core.cache import cache

HOME_CONTEXT_CACHE_KEY = "myshop:home:context"
HOME_CONTEXT_CACHE_TIMEOUT = 300  # 5 minutes


def get_home_context_from_cache():
    """Return cached home context if available."""
    return cache.get(HOME_CONTEXT_CACHE_KEY)


def set_home_context_cache(context):
    """Persist home context in cache for repeated access."""
    cache.set(HOME_CONTEXT_CACHE_KEY, context, HOME_CONTEXT_CACHE_TIMEOUT)


def invalidate_home_context_cache():
    """Invalidate cached home context."""
    cache.delete(HOME_CONTEXT_CACHE_KEY)

