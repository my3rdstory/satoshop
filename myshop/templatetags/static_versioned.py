import hashlib
import os
from django import template
from django.templatetags.static import static
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.core.cache import cache

register = template.Library()

def get_file_hash(file_path):
    """파일의 MD5 해시를 계산합니다. (백업용 - ManifestStaticFilesStorage 사용 권장)"""
    cache_key = f"static_hash_{file_path}"
    cached_hash = cache.get(cache_key)
    
    if cached_hash:
        return cached_hash
    
    # 정적 파일의 실제 경로 찾기
    absolute_path = find(file_path)
    if not absolute_path or not os.path.exists(absolute_path):
        # 파일을 찾을 수 없으면 기본 버전 사용
        return getattr(settings, 'STATIC_VERSION', '1')
    
    try:
        with open(absolute_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]  # 8자리 해시 사용
        
        # 캐시에 저장 (5분간)
        cache.set(cache_key, file_hash, 300)
        return file_hash
    except (IOError, OSError):
        # 파일 읽기 실패시 기본 버전 사용
        return getattr(settings, 'STATIC_VERSION', '1')

@register.simple_tag
def static_v(path):
    """
    정적 파일 URL에 해시 기반 버전 파라미터를 자동으로 추가하는 템플릿 태그
    
    주의: ManifestStaticFilesStorage 사용 시에는 기본 {% static %} 태그를 사용하세요.
    이 태그는 백업용으로만 유지됩니다.
    """
    static_url = static(path)
    
    # ManifestStaticFilesStorage 사용시 이미 해시가 포함되어 있으므로 그대로 반환
    if hasattr(settings, 'STATICFILES_STORAGE') and 'Manifest' in settings.STATICFILES_STORAGE:
        return static_url
    
    # 개별 파일 해시 생성 (백업용)
    file_hash = get_file_hash(path)
    return f"{static_url}?v={file_hash}"

@register.simple_tag
def static_hash(path):
    """파일의 해시값만 반환하는 템플릿 태그 (백업용)"""
    return get_file_hash(path)

@register.simple_tag
def css_v(path):
    """CSS 파일 전용 버전 관리 태그 (백업용)"""
    if not path.startswith('css/'):
        path = f'css/{path}'
    return static_v(path)

@register.simple_tag
def js_v(path):
    """JavaScript 파일 전용 버전 관리 태그 (백업용)"""
    if not path.startswith('js/'):
        path = f'js/{path}'
    return static_v(path) 