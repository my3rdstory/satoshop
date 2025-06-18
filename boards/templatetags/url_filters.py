import re
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()

@register.filter
def urlize_target_blank(text):
    """
    텍스트에서 URL을 찾아 target="_blank"가 포함된 링크로 변환
    """
    if not text:
        return text
    
    # 이미 HTML 태그가 포함된 텍스트라면 그대로 반환
    if '<' in text and '>' in text:
        return text
    
    # URL 패턴 정규식
    url_pattern = re.compile(
        r'(https?://[^\s<>"\']+)',
        re.IGNORECASE
    )
    
    # HTML 이스케이프 후 URL 변환
    escaped_text = escape(text)
    
    def replace_url(match):
        url = match.group(1)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
    
    result = url_pattern.sub(replace_url, escaped_text)
    
    return mark_safe(result) 