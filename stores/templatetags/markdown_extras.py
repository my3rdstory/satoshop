from django import template
from django.utils.safestring import mark_safe
import markdown
import bleach
import re

register = template.Library()

@register.filter
def markdown_to_html(value):
    """마크다운 텍스트를 안전한 HTML로 변환 (링크, 이미지, 유튜브 자동 처리)"""
    if not value:
        return ""
    
    # 마크다운을 HTML로 변환
    html = markdown.markdown(
        value,
        extensions=[
            'markdown.extensions.tables',
            'markdown.extensions.fenced_code',
            'markdown.extensions.nl2br',
            'markdown.extensions.toc',
        ]
    )
    
    # 후처리: 일반 텍스트 URL을 링크나 이미지로 자동 변환
    html = auto_convert_plain_urls(html)
    
    # 후처리: 링크에 target="_blank" 추가
    html = add_target_blank_to_links(html)
    
    # 후처리: 이미지 URL 자동 변환 (마크다운으로 생성된 링크 처리)
    html = auto_convert_image_urls(html)
    
    # 후처리: 유튜브 링크 임베드
    html = embed_youtube_links(html)
    
    # XSS 방지를 위한 HTML 태그 허용 목록
    allowed_tags = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br', 'strong', 'em', 'u', 'i', 'b',
        'ul', 'ol', 'li',
        'blockquote', 'pre', 'code',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'a', 'img', 'iframe',
        'hr', 'div', 'span',
    ]
    
    allowed_attributes = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height', 'style'],
        'iframe': ['src', 'style', 'allowfullscreen'],
        'div': ['style'],
        'table': ['class'],
        'th': ['scope'],
        'td': ['colspan', 'rowspan'],
    }
    
    # HTML 정화
    clean_html = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )
    
    return mark_safe(clean_html)


def add_target_blank_to_links(html):
    """모든 링크에 target="_blank" 속성 추가"""
    # href 속성이 있는 a 태그를 찾아서 target 속성이 없으면 추가
    pattern = r'<a\s+([^>]*?href="[^"]*"[^>]*?)>'
    
    def replace_link(match):
        attributes = match.group(1)
        
        # 이미 target 속성이 있는지 확인
        if 'target=' in attributes:
            return match.group(0)
        
        # target="_blank" 추가
        return f'<a {attributes} target="_blank">'
    
    return re.sub(pattern, replace_link, html)


def auto_convert_image_urls(html):
    """이미지 확장자로 끝나는 URL을 자동으로 이미지 태그로 변환"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    
    # 1. 먼저 링크 태그 안의 이미지 URL 처리
    link_pattern = r'<a\s+[^>]*?href="([^"]*?(?:' + '|'.join(re.escape(ext) for ext in image_extensions) + r')(?:\?[^"]*?)?)"[^>]*?>(.*?)</a>'
    
    def replace_image_link(match):
        url = match.group(1)
        link_text = match.group(2).strip()
        
        # 링크 텍스트가 URL과 같거나 비어있으면 이미지로 변환
        if not link_text or link_text == url:
            return f'<div style="margin: 15px 0;"><img src="{url}" alt="이미지" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);"></div>'
        else:
            # 링크 텍스트가 다르면 원래 링크 유지
            return match.group(0)
    
    html = re.sub(link_pattern, replace_image_link, html, flags=re.DOTALL)
    
    # 2. 일반 텍스트에서 독립적인 이미지 URL 처리 (HTML 태그 밖에 있는 것만)
    # 줄 단위로 처리하여 HTML 태그가 있는 줄은 건드리지 않음
    lines = html.split('\n')
    processed_lines = []
    
    for line in lines:
        # HTML 태그가 포함된 라인은 건드리지 않음
        if '<' in line and '>' in line:
            processed_lines.append(line)
        else:
            # 일반 텍스트 라인에서만 이미지 URL 변환
            url_pattern = r'(https?://[^\s<>"]+(?:' + '|'.join(re.escape(ext) for ext in image_extensions) + r')(?:\?[^\s<>"]*)?)'
            
            def replace_standalone_image_url(match):
                url = match.group(1)
                return f'<div style="margin: 15px 0;"><img src="{url}" alt="이미지" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);"></div>'
            
            processed_line = re.sub(url_pattern, replace_standalone_image_url, line)
            processed_lines.append(processed_line)
    
    return '\n'.join(processed_lines)


def embed_youtube_links(html):
    """유튜브 링크를 반응형 임베드로 변환"""
    youtube_patterns = [
        r'<a\s+[^>]*href="(https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)[^"]*)"[^>]*>([^<]*)</a>',
        r'<a\s+[^>]*href="(https?://youtu\.be/([a-zA-Z0-9_-]+)[^"]*)"[^>]*>([^<]*)</a>',
        r'(https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)(?:[^\s<>"]*)?)',
        r'(https?://youtu\.be/([a-zA-Z0-9_-]+)(?:[^\s<>"]*)?)'
    ]
    
    def create_youtube_embed(video_id):
        return f'''
        <div style="margin: 20px 0;">
            <div style="position: relative; width: 100%; height: 0; padding-bottom: 56.25%; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);">
                <iframe 
                    src="https://www.youtube.com/embed/{video_id}" 
                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
                    allowfullscreen>
                </iframe>
            </div>
        </div>
        '''
    
    for pattern in youtube_patterns:
        def replace_youtube(match):
            if len(match.groups()) >= 2:
                video_id = match.group(2)
                return create_youtube_embed(video_id)
            return match.group(0)
        
        html = re.sub(pattern, replace_youtube, html)
    
    return html


def auto_convert_plain_urls(html):
    """일반 텍스트에서 URL을 자동으로 링크나 이미지로 변환"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    
    # URL 패턴 (http:// 또는 https://로 시작하는 URL)
    # 줄 끝의 </p> 태그도 함께 캡처
    url_pattern = r'(https?://[^\s<>"]+)(\s*</p>)?'
    
    def replace_url(match):
        url = match.group(1)
        closing_tag = match.group(2) if match.group(2) else ''
        
        # URL 끝에서 쿼리 파라미터나 프래그먼트 제거하여 확장자 확인
        url_path = url.split('?')[0].split('#')[0]
        url_lower = url_path.lower()
        
        # 이미지 확장자로 끝나는지 확인
        is_image = any(url_lower.endswith(ext) for ext in image_extensions)
        
        if is_image:
            return f'<div style="margin: 15px 0;"><img src="{url}" alt="이미지" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);"></div>{closing_tag}'
        else:
            return f'<a href="{url}" target="_blank">{url}</a>{closing_tag}'
    
    # URL 변환 적용
    result = re.sub(url_pattern, replace_url, html)
    return result 