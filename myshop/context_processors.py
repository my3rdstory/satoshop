from .models import SiteSettings
from django.conf import settings
import hashlib
import json
import logging
import os
from django.core.cache import cache
import subprocess

logger = logging.getLogger(__name__)

def user_store(request):
    """사용자의 활성 스토어 정보를 컨텍스트에 추가"""
    context = {
        'user_has_active_store': False,
        'user_active_store': None,
    }
    
    if request.user.is_authenticated:
        # 삭제되지 않은 스토어 중에서 찾기
        from stores.models import Store
        active_store = Store.objects.filter(
            owner=request.user,
            deleted_at__isnull=True
        ).first()
        
        if active_store:
            context['user_has_active_store'] = True
            context['user_active_store'] = active_store
    
    return context


def get_file_hash(file_path):
    """파일의 MD5 해시를 계산"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    except (FileNotFoundError, IOError):
        return None

def get_static_version():
    """정적 파일의 버전을 동적으로 계산"""
    # 캐시 키
    cache_key = 'static_version'
    
    # 캐시에서 버전 확인 (1분간 캐시)
    cached_version = cache.get(cache_key)
    if cached_version:
        return cached_version
    
    version_sources = []
    
    # CSS/JS 파일들의 해시 계산
    static_files = [
        'static/css/custom.css',
        'static/js/common.js',
        # 주요 파일들만 포함
    ]
    
    for file_path in static_files:
        full_path = os.path.join(settings.BASE_DIR, file_path)
        file_hash = get_file_hash(full_path)
        if file_hash:
            version_sources.append(file_hash)
    
    # Git 커밋 해시 사용 (가능한 경우)
    try:
        git_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'], 
            cwd=settings.BASE_DIR,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()
        version_sources.append(git_hash)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # 버전 생성
    if version_sources:
        combined = ''.join(version_sources)
        version = hashlib.md5(combined.encode()).hexdigest()[:8]
    else:
        # 폴백: 현재 시간 기반
        import time
        version = str(int(time.time()))[-8:]
    
    # 캐시에 저장 (1분)
    cache.set(cache_key, version, 60)
    
    return version

def site_settings(request):
    """모든 템플릿에서 사이트 설정을 사용할 수 있도록 하는 컨텍스트 프로세서"""
    try:
        from .models import SiteSettings, DocumentContent
        site_settings_obj = SiteSettings.get_settings()
        active_documents = DocumentContent.get_active_documents()
        
        # 문서를 딕셔너리로 변환하여 쉽게 접근 가능하도록
        documents_dict = {doc.document_type: doc for doc in active_documents}
        
        return {
            'site_settings': site_settings_obj,
            'documents': documents_dict,
            'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '1'),
        }
    except Exception:
        # 마이그레이션 전이나 오류 상황에서는 기본값 반환
        return {
            'site_settings': None,
            'documents': {},
            'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '1'),
        } 