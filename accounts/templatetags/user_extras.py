from django import template
from django.utils.html import format_html

register = template.Library()

@register.filter
def friendly_display_name(user):
    """사용자명을 더 친근하게 표시"""
    if hasattr(user, 'lightning_profile') and user.lightning_profile:
        # 라이트닝 사용자인 경우
        username = user.username
        
        # 자동 생성된 friendly username인 경우 더 좋게 포맷팅
        if '_' in username:
            parts = username.split('_')
            if len(parts) == 2:
                adjective, noun = parts[0], parts[1]
                # 첫 글자 대문자로 만들어서 더 보기 좋게
                display_name = f"{adjective.title()} {noun.title()}"
                return format_html(
                    '<span class="lightning-user">{}</span> '
                    '<span class="text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 px-2 py-1 rounded-full ml-2">'
                    '<i class="fas fa-bolt mr-1"></i>Lightning'
                    '</span>',
                    display_name
                )
        
        # 일반적인 라이트닝 사용자명
        return format_html(
            '{} '
            '<span class="text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 px-2 py-1 rounded-full ml-2">'
            '<i class="fas fa-bolt mr-1"></i>Lightning'
            '</span>',
            username
        )
    
    # 일반 사용자
    return user.username

@register.filter
def is_lightning_user(user):
    """라이트닝 사용자인지 확인"""
    return hasattr(user, 'lightning_profile') and user.lightning_profile 