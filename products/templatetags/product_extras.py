from django import template
import markdown
from markdown.extensions import codehilite, fenced_code, tables
import re
from urllib.parse import urlparse, parse_qs

register = template.Library()

@register.filter
def markdown_render(text):
    """Markdown 텍스트를 HTML로 변환 (링크, 이미지, 유튜브 자동 처리)"""
    if not text:
        return ''
    
    # Markdown 확장 기능 설정
    extensions = [
        'markdown.extensions.fenced_code',
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
        'markdown.extensions.codehilite',
        'markdown.extensions.sane_lists',
    ]
    
    extension_configs = {
        'markdown.extensions.codehilite': {
            'css_class': 'highlight',
            'use_pygments': True,
        }
    }
    
    # 먼저 일반 텍스트 URL을 임시 플레이스홀더로 변환 (마크다운 처리 전)
    text = preprocess_urls(text)
    
    # Markdown을 HTML로 변환
    md = markdown.Markdown(
        extensions=extensions,
        extension_configs=extension_configs,
        safe_mode=False
    )
    
    html = md.convert(text)
    
    # 후처리: 임시 플레이스홀더를 실제 링크/이미지/유튜브로 변환
    html = postprocess_urls(html)
    
    # 후처리: 링크에 target="_blank" 추가
    html = add_target_blank_to_links(html)
    
    # 후처리: 취소선 처리
    html = process_strikethrough(html)
    
    # HTML 구조 정리 (p 태그 안의 div 태그 문제 해결)
    html = fix_html_structure(html)
    
    return html


def preprocess_urls(text):
    """마크다운 처리 전에 일반 텍스트 URL을 임시 플레이스홀더로 변환"""
    import uuid
    
    # URL 패턴들
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)(?:[^\s<>"]*)?',
        r'https?://youtu\.be/([a-zA-Z0-9_-]+)(?:[^\s<>"]*)?'
    ]
    
    placeholders = {}
    
    # 1. 유튜브 링크 처리
    for pattern in youtube_patterns:
        def replace_youtube(match):
            video_id = match.group(1)
            placeholder = f"__YOUTUBE_PLACEHOLDER_{uuid.uuid4().hex}__"
            placeholders[placeholder] = create_youtube_embed(video_id)
            return placeholder
        
        text = re.sub(pattern, replace_youtube, text)
    
    # 2. 이미지 URL 처리 (마크다운 이미지가 아닌 일반 텍스트 URL만)
    # 마크다운 이미지 패턴을 피하기 위해 negative lookbehind 사용
    image_pattern = r'(?<!\]\()(?<!\]\s\()https?://[^\s<>"]+(?:' + '|'.join(re.escape(ext) for ext in image_extensions) + r')(?:\?[^\s<>"]*)?'
    
    def replace_image(match):
        url = match.group(0)
        placeholder = f"__IMAGE_PLACEHOLDER_{uuid.uuid4().hex}__"
        placeholders[placeholder] = f'<div style="margin: 15px 0;"><img src="{url}" alt="이미지" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);"></div>'
        return placeholder
    
    text = re.sub(image_pattern, replace_image, text)
    
    # 3. 일반 링크 처리 (이미지나 유튜브가 아닌 URL)
    # 마크다운 링크와 이미 처리된 URL들을 피함
    general_url_pattern = r'(?<!\]\()(?<!\]\s\()(?<!__YOUTUBE_PLACEHOLDER_)(?<!__IMAGE_PLACEHOLDER_)https?://[^\s<>"]+(?![a-f0-9]{32}__)'
    
    def replace_general_url(match):
        url = match.group(0)
        # 이미지나 유튜브 URL이 아닌지 확인
        url_lower = url.lower()
        is_image = any(url_lower.split('?')[0].split('#')[0].endswith(ext) for ext in image_extensions)
        is_youtube = 'youtube.com/watch' in url_lower or 'youtu.be/' in url_lower
        
        if not is_image and not is_youtube:
            placeholder = f"__LINK_PLACEHOLDER_{uuid.uuid4().hex}__"
            placeholders[placeholder] = f'<a href="{url}" target="_blank">{url}</a>'
            return placeholder
        
        return url
    
    text = re.sub(general_url_pattern, replace_general_url, text)
    
    # 플레이스홀더 정보를 텍스트에 저장 (나중에 복원하기 위해)
    text += f"\n\n<!-- PLACEHOLDERS: {placeholders} -->"
    
    return text


def postprocess_urls(html):
    """플레이스홀더를 실제 HTML로 변환"""
    import ast
    
    # 플레이스홀더 정보 추출
    placeholder_match = re.search(r'<!-- PLACEHOLDERS: ({.*?}) -->', html, re.DOTALL)
    if not placeholder_match:
        return html
    
    try:
        placeholders = ast.literal_eval(placeholder_match.group(1))
        
        # 플레이스홀더 주석 제거
        html = re.sub(r'\n\n<!-- PLACEHOLDERS: .*? -->', '', html, flags=re.DOTALL)
        
        # 플레이스홀더를 실제 HTML로 교체
        for placeholder, replacement in placeholders.items():
            html = html.replace(placeholder, replacement)
            
    except (ValueError, SyntaxError):
        # 플레이스홀더 파싱 실패 시 원본 반환
        html = re.sub(r'\n\n<!-- PLACEHOLDERS: .*? -->', '', html, flags=re.DOTALL)
    
    return html


def fix_html_structure(html):
    """잘못된 HTML 구조 수정 (p 태그 안의 div 태그 등)"""
    # p 태그 안의 div 태그를 p 태그 밖으로 이동
    def fix_p_div(match):
        p_content = match.group(1)
        
        # div 태그들을 찾아서 분리
        div_pattern = r'(<div[^>]*>.*?</div>)'
        divs = re.findall(div_pattern, p_content, re.DOTALL)
        
        if divs:
            # div를 제거한 p 태그 내용
            p_content_clean = re.sub(div_pattern, '', p_content, flags=re.DOTALL).strip()
            
            result = ''
            if p_content_clean:
                result += f'<p>{p_content_clean}</p>'
            
            # div들을 p 태그 밖에 추가
            for div in divs:
                result += div
            
            return result
        
        return match.group(0)
    
    html = re.sub(r'<p>(.*?)</p>', fix_p_div, html, flags=re.DOTALL)
    
    return html


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


def process_strikethrough(html):
    """취소선 (~~text~~) 처리"""
    # ~~로 감싸진 텍스트를 <del> 태그로 변환
    pattern = r'~~([^~]+)~~'
    return re.sub(pattern, r'<del>\1</del>', html)


def create_youtube_embed(video_id):
    """유튜브 임베드 HTML 생성"""
    return f'''<div style="margin: 20px 0;">
    <div style="position: relative; width: 100%; height: 0; padding-bottom: 56.25%; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);">
        <iframe 
            src="https://www.youtube.com/embed/{video_id}" 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
            allowfullscreen>
        </iframe>
    </div>
</div>''' 