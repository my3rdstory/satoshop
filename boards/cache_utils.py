"""Cache helpers for boards app views."""

from django.core.cache import cache

NOTICE_LIST_CACHE_PREFIX = "boards:notice:list"
NOTICE_DETAIL_CACHE_PREFIX = "boards:notice:detail"
NOTICE_LIST_VERSION_KEY = "boards:notice:list:version"
NOTICE_DETAIL_VERSION_KEY = "boards:notice:detail:version"
NOTICE_LIST_CACHE_TIMEOUT = 300  # 5 minutes
NOTICE_DETAIL_CACHE_TIMEOUT = 300  # 5 minutes

MEME_LIST_CACHE_PREFIX = "boards:meme:list"
MEME_DETAIL_CACHE_PREFIX = "boards:meme:detail"
MEME_LIST_VERSION_KEY = "boards:meme:list:version"
MEME_DETAIL_VERSION_KEY = "boards:meme:detail:version"
MEME_LIST_CACHE_TIMEOUT = 180  # 3 minutes
MEME_DETAIL_CACHE_TIMEOUT = 180  # 3 minutes


def _ensure_version(key):
    version = cache.get(key)
    if version is None:
        version = 1
        cache.set(key, version, None)
    return version


def _bump_version(key):
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 2, None)
        return 2


def _build_versioned_key(prefix, version_key, suffix):
    version = _ensure_version(version_key)
    return f"{prefix}:v{version}:{suffix}"


def get_notice_list_cache(suffix):
    return cache.get(_build_versioned_key(NOTICE_LIST_CACHE_PREFIX, NOTICE_LIST_VERSION_KEY, suffix))


def set_notice_list_cache(suffix, data):
    cache.set(
        _build_versioned_key(NOTICE_LIST_CACHE_PREFIX, NOTICE_LIST_VERSION_KEY, suffix),
        data,
        NOTICE_LIST_CACHE_TIMEOUT,
    )


def invalidate_notice_list_cache():
    _bump_version(NOTICE_LIST_VERSION_KEY)


def get_notice_detail_cache(pk):
    return cache.get(_build_versioned_key(NOTICE_DETAIL_CACHE_PREFIX, NOTICE_DETAIL_VERSION_KEY, pk))


def set_notice_detail_cache(pk, data):
    cache.set(
        _build_versioned_key(NOTICE_DETAIL_CACHE_PREFIX, NOTICE_DETAIL_VERSION_KEY, pk),
        data,
        NOTICE_DETAIL_CACHE_TIMEOUT,
    )


def invalidate_notice_detail_cache():
    _bump_version(NOTICE_DETAIL_VERSION_KEY)


def get_meme_list_cache(suffix):
    return cache.get(_build_versioned_key(MEME_LIST_CACHE_PREFIX, MEME_LIST_VERSION_KEY, suffix))


def set_meme_list_cache(suffix, data):
    cache.set(
        _build_versioned_key(MEME_LIST_CACHE_PREFIX, MEME_LIST_VERSION_KEY, suffix),
        data,
        MEME_LIST_CACHE_TIMEOUT,
    )


def invalidate_meme_list_cache():
    _bump_version(MEME_LIST_VERSION_KEY)


def get_meme_detail_cache(pk):
    return cache.get(_build_versioned_key(MEME_DETAIL_CACHE_PREFIX, MEME_DETAIL_VERSION_KEY, pk))


def set_meme_detail_cache(pk, data):
    cache.set(
        _build_versioned_key(MEME_DETAIL_CACHE_PREFIX, MEME_DETAIL_VERSION_KEY, pk),
        data,
        MEME_DETAIL_CACHE_TIMEOUT,
    )


def invalidate_meme_detail_cache():
    _bump_version(MEME_DETAIL_VERSION_KEY)

