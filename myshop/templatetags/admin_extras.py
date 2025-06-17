from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def get_site_settings():
    """사이트 설정을 가져오는 템플릿 태그"""
    try:
        from myshop.models import SiteSettings
        return SiteSettings.get_settings()
    except Exception:
        return None

@register.simple_tag
def admin_logo_or_text(site_settings, site_header, default_text):
    """관리자 로고 또는 텍스트를 반환하는 템플릿 태그"""
    if site_settings and site_settings.admin_logo_url:
        return mark_safe(f'<img src="{site_settings.admin_logo_url}" alt="{site_header or default_text}" style="max-height: 40px; vertical-align: middle;">')
    else:
        return site_header or default_text 