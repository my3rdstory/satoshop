def add_no_cache_headers(headers, path, url):
    """
    개발 환경에서 정적 파일에 no-cache 헤더를 추가하는 함수
    """
    from django.conf import settings
    
    if settings.DEBUG:
        headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        headers['Pragma'] = 'no-cache'
        headers['Expires'] = '0'
    
    return headers 