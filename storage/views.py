"""
Storage 앱의 뷰들
"""

import logging
import mimetypes
import urllib.parse
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .backends import S3Storage

logger = logging.getLogger(__name__)


def check_referer_allowed(request):
    """
    Referer 헤더를 검증하여 허용된 도메인에서의 요청인지 확인
    핫링킹(외부 사이트에서 이미지 직접 사용) 방지
    """
    # 핫링크 보호가 비활성화된 경우 모든 요청 허용
    if not getattr(settings, 'HOTLINK_PROTECTION_ENABLED', True):
        logger.debug("핫링크 보호 비활성화됨 - 모든 요청 허용")
        return True
    
    referer = request.META.get('HTTP_REFERER', '')
    
    # Referer가 없는 경우 (직접 접근, 북마크, 일부 브라우저 설정 등)
    if not referer:
        logger.debug("Referer 헤더 없음 - 직접 접근으로 간주하여 허용")
        return True
    
    # 허용된 도메인 목록
    allowed_domains = [
        request.get_host(),  # 현재 요청 도메인
        'localhost',
        '127.0.0.1',
    ]
    
    # ALLOWED_HOSTS 설정에서 추가 도메인 가져오기
    if hasattr(settings, 'ALLOWED_HOSTS'):
        for host in settings.ALLOWED_HOSTS:
            if host and host != '*':  # 와일드카드 제외
                allowed_domains.append(host)
    
    # 설정에서 추가 허용 도메인 가져오기
    if hasattr(settings, 'HOTLINK_ALLOWED_DOMAINS'):
        for domain in settings.HOTLINK_ALLOWED_DOMAINS:
            if domain and domain.strip():
                allowed_domains.append(domain.strip())
    
    # Referer URL에서 도메인 추출
    try:
        from urllib.parse import urlparse
        referer_domain = urlparse(referer).netloc
        
        # 포트 번호 제거 (예: localhost:8011 -> localhost)
        referer_domain_clean = referer_domain.split(':')[0]
        
        # 허용된 도메인과 비교
        for allowed_domain in allowed_domains:
            allowed_domain_clean = allowed_domain.split(':')[0]
            if (referer_domain == allowed_domain or 
                referer_domain_clean == allowed_domain_clean or
                referer_domain.endswith('.' + allowed_domain_clean)):
                logger.debug(f"허용된 도메인에서 접근: {referer_domain}")
                return True
        
        logger.warning(f"허용되지 않은 도메인에서 접근 시도: {referer} (도메인: {referer_domain})")
        return False
        
    except Exception as e:
        logger.error(f"Referer 검증 중 오류: {e}")
        # 오류 발생 시 안전하게 허용 (서비스 중단 방지)
        return True


@require_http_methods(["GET"])
@cache_control(max_age=3600, public=True)  # 1시간 캐싱
@vary_on_headers('Accept-Encoding', 'Referer')  # Referer 헤더도 캐시 키에 포함
def serve_s3_file(request, file_path):
    """
    S3 파일을 안전하게 프록시하는 뷰
    AWS Access Key ID 등 민감한 정보 노출을 방지
    Referer 헤더 검증으로 핫링킹 방지
    """
    try:
        # Referer 헤더 검증 (핫링킹 방지)
        if not check_referer_allowed(request):
            logger.warning(f"핫링킹 차단: {request.META.get('HTTP_REFERER', 'Unknown')} -> {file_path}")
            return HttpResponse(
                "접근이 거부되었습니다. 이 이미지는 외부 사이트에서 사용할 수 없습니다.",
                status=403,
                content_type='text/plain; charset=utf-8'
            )
        
        # 파일 경로 디코딩
        decoded_path = urllib.parse.unquote(file_path)
        logger.debug(f"S3 파일 요청: {decoded_path}")
        
        # S3 스토리지 인스턴스 생성
        storage = S3Storage()
        
        # 파일 존재 확인
        if not storage.exists(decoded_path):
            logger.warning(f"S3 파일을 찾을 수 없음: {decoded_path}")
            raise Http404("파일을 찾을 수 없습니다.")
        
        # 파일 내용 읽기
        file_obj = storage._open(decoded_path)
        file_content = file_obj.read()
        
        # Content-Type 추정
        content_type = mimetypes.guess_type(decoded_path)[0] or 'application/octet-stream'
        
        # HTTP 응답 생성
        response = HttpResponse(file_content, content_type=content_type)
        
        # 캐싱 헤더 설정
        response['Cache-Control'] = 'public, max-age=3600'
        response['Content-Length'] = len(file_content)
        
        # 추가 보안 헤더
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        logger.info(f"S3 파일 서빙 성공: {decoded_path} ({len(file_content)} bytes)")
        return response
        
    except Http404:
        raise
    except Exception as e:
        logger.error(f"S3 파일 서빙 실패: {file_path} - {e}")
        raise Http404("파일을 가져올 수 없습니다.")


@require_http_methods(["GET"])
def serve_s3_file_redirect(request, file_path):
    """
    S3 파일로 리다이렉트하는 뷰 (임시 사용)
    프록시 방식에 문제가 있을 때 사용
    """
    try:
        # Referer 헤더 검증 (리다이렉트 방식에서도 적용)
        if not check_referer_allowed(request):
            logger.warning(f"핫링킹 차단 (리다이렉트): {request.META.get('HTTP_REFERER', 'Unknown')} -> {file_path}")
            return HttpResponse(
                "접근이 거부되었습니다. 이 이미지는 외부 사이트에서 사용할 수 없습니다.",
                status=403,
                content_type='text/plain; charset=utf-8'
            )
        
        # 파일 경로 디코딩
        decoded_path = urllib.parse.unquote(file_path)
        
        # S3 스토리지 인스턴스 생성
        storage = S3Storage()
        
        # 파일 존재 확인
        if not storage.exists(decoded_path):
            raise Http404("파일을 찾을 수 없습니다.")
        
        # pre-signed URL 생성 (짧은 만료 시간)
        presigned_url = storage.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': storage.bucket_name, 'Key': decoded_path},
            ExpiresIn=300  # 5분
        )
        
        return HttpResponseRedirect(presigned_url)
        
    except Http404:
        raise
    except Exception as e:
        logger.error(f"S3 파일 리다이렉트 실패: {file_path} - {e}")
        raise Http404("파일을 가져올 수 없습니다.") 
