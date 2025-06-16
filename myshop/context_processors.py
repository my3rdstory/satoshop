from .models import SiteSettings
from django.conf import settings

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

def site_settings(request):
    """모든 템플릿에서 사이트 설정을 사용할 수 있도록 하는 컨텍스트 프로세서"""
    try:
        site_settings_obj = SiteSettings.get_settings()
        return {
            'site_settings': site_settings_obj,
            'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '1'),
        }
    except Exception:
        # 마이그레이션 전이나 오류 상황에서는 기본값 반환
        return {
            'site_settings': None,
            'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '1'),
        } 