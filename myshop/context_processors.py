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
            'DEBUG': settings.DEBUG,
        }
    except Exception:
        # 마이그레이션 전이나 오류 상황에서는 기본값 반환
        return {
            'site_settings': None,
            'documents': {},
            'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '1'),
            'DEBUG': settings.DEBUG,
        }

def opengraph_context(request):
    """
    오픈그래프 메타 태그를 자동으로 생성하는 컨텍스트 프로세서
    """
    site_settings = SiteSettings.get_settings()
    
    # 기본 오픈그래프 설정
    og_defaults = {
        'og_title': site_settings.site_title if site_settings else 'SatoShop',
        'og_description': site_settings.site_description if site_settings else '비트코인 라이트닝 결제 플랫폼',
        'og_type': 'website',
        'og_url': request.build_absolute_uri(),
        'og_image': site_settings.og_default_image if site_settings and site_settings.og_default_image else None,
        'og_site_name': site_settings.og_site_name if site_settings else 'SatoShop',
    }
    
    return {
        'og_defaults': og_defaults,
    }

def auto_opengraph_meta(request, page_type=None, **kwargs):
    """
    페이지 타입에 따라 자동으로 오픈그래프 메타 태그를 생성하는 헬퍼 함수
    
    사용법:
    # 뷰에서
    context['opengraph'] = auto_opengraph_meta(request, 'store_detail', store=store)
    
    # 템플릿에서
    {{ opengraph.title }}
    """
    site_settings = SiteSettings.get_settings()
    
    # URL 경로 기반 자동 감지
    if not page_type:
        path = request.path
        if '/stores/' in path and '/products/' not in path:
            if path.endswith('/create/') or '/create/' in path:
                page_type = 'store_create'
            elif '/browse/' in path:
                page_type = 'store_browse'
            elif '/my/' in path:
                page_type = 'my_stores'
            else:
                page_type = 'store_detail'
        elif '/products/' in path:
            if '/add/' in path:
                page_type = 'product_add'
            elif '/list/' in path:
                page_type = 'product_list'
            else:
                page_type = 'product_detail'
        elif path == '/':
            page_type = 'home'
    
    # 페이지 타입별 기본 설정
    page_configs = {
        'home': {
            'title': f"{site_settings.site_title} - {site_settings.site_description}" if site_settings else "SatoShop - 비트코인 라이트닝 결제 플랫폼",
            'description': site_settings.hero_description if site_settings and site_settings.hero_description else "누구나 쉽게 만드는 비트코인 온라인 스토어. 5분만에 스토어를 구축하고 라이트닝 네트워크로 즉시 결제받으세요.",
            'type': 'website'
        },
        'store_detail': {
            'title': f"{kwargs.get('store').store_name} - SatoShop" if kwargs.get('store') else "스토어 - SatoShop",
            'description': f"{kwargs.get('store').store_description[:100]}..." if kwargs.get('store') and kwargs.get('store').store_description else "SatoShop 스토어에서 비트코인으로 쇼핑하세요",
            'type': 'website',
            'image': kwargs.get('store').images.first().file_url if kwargs.get('store') and kwargs.get('store').images.exists() else None
        },
        'product_detail': {
            'title': f"{kwargs.get('product').title} - {kwargs.get('store').store_name}" if kwargs.get('product') and kwargs.get('store') else "상품 - SatoShop",
            'description': f"{kwargs.get('product').description[:100]}..." if kwargs.get('product') and kwargs.get('product').description else "SatoShop에서 비트코인으로 구매하세요",
            'type': 'product',
            'image': kwargs.get('product').images.first().file_url if kwargs.get('product') and hasattr(kwargs.get('product'), 'images') and kwargs.get('product').images.exists() else None
        },
        'store_browse': {
            'title': "스토어 탐색 - SatoShop",
            'description': "SatoShop에서 다양한 스토어를 탐색하고 비트코인으로 쇼핑하세요. 창의적인 상품과 서비스를 발견해보세요.",
            'type': 'website'
        },
        'store_create': {
            'title': "스토어 만들기 - SatoShop",
            'description': "SatoShop에서 나만의 비트코인 온라인 스토어를 5분 만에 만들어보세요. 코딩 없이 쉽게 시작하세요.",
            'type': 'website'
        },
        'my_stores': {
            'title': "내 스토어 관리 - SatoShop",
            'description': "SatoShop에서 내가 운영하는 스토어를 관리하고 설정을 변경하세요.",
            'type': 'website'
        },
        'product_list': {
            'title': f"{kwargs.get('store').store_name} 상품 목록 - SatoShop" if kwargs.get('store') else "상품 목록 - SatoShop",
            'description': f"{kwargs.get('store').store_name}의 다양한 상품들을 둘러보고 비트코인으로 결제하세요." if kwargs.get('store') else "다양한 상품들을 둘러보고 비트코인으로 결제하세요.",
            'type': 'website'
        },
        'product_add': {
            'title': f"{kwargs.get('store').store_name} 상품 추가 - SatoShop" if kwargs.get('store') else "상품 추가 - SatoShop",
            'description': f"{kwargs.get('store').store_name}에 새로운 상품을 등록하고 비트코인 라이트닝 결제로 판매를 시작하세요." if kwargs.get('store') else "새로운 상품을 등록하고 비트코인 라이트닝 결제로 판매를 시작하세요.",
            'type': 'website'
        }
    }
    
    # 기본 설정 가져오기
    config = page_configs.get(page_type, {
        'title': site_settings.site_title if site_settings else 'SatoShop',
        'description': site_settings.site_description if site_settings else '비트코인 라이트닝 결제 플랫폼',
        'type': 'website'
    })
    
    # 파라미터로 전달된 값으로 오버라이드
    for key, value in kwargs.items():
        if key in ['title', 'description', 'image', 'type'] and value:
            config[key] = value
    
    # 기본 이미지 설정
    if 'image' not in config or not config['image']:
        config['image'] = site_settings.og_default_image if site_settings and site_settings.og_default_image else None
    
    return {
        'title': config['title'],
        'description': config['description'],
        'type': config['type'],
        'image': config['image'],
        'url': request.build_absolute_uri(),
        'site_name': site_settings.og_site_name if site_settings else 'SatoShop',
    } 