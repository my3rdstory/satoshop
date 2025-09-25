"""Cache utilities for frequently accessed store data."""

from django.core.cache import cache

STORE_BROWSE_CACHE_KEY = "stores:browse:landing"
STORE_BROWSE_CACHE_TIMEOUT = 300  # 5 minutes


def get_store_browse_cache():
    """Return cached browse context if available."""
    return cache.get(STORE_BROWSE_CACHE_KEY)


def set_store_browse_cache(context):
    """Persist browse context for repeated access."""
    cache.set(STORE_BROWSE_CACHE_KEY, context, STORE_BROWSE_CACHE_TIMEOUT)


def invalidate_store_browse_cache():
    """Clear cached browse context."""
    cache.delete(STORE_BROWSE_CACHE_KEY)

