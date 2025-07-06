"""
Custom middleware for security headers
"""

class PermissionsPolicyMiddleware:
    """
    Permissions Policy 헤더를 추가하는 미들웨어
    Django admin의 unload 이벤트 경고 해결
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # meetup_checker 페이지는 카메라 접근 허용
        if 'meetup' in request.path and 'checker' in request.path:
            permissions_policy = (
                'accelerometer=(), '
                'autoplay=(), '
                'camera=*, '  # 카메라 접근 허용
                'display-capture=(), '
                'encrypted-media=(), '
                'geolocation=(), '
                'gyroscope=(), '
                'magnetometer=(), '
                'microphone=(), '
                'midi=(), '
                'payment=(), '
                'picture-in-picture=(), '
                'publickey-credentials-get=(), '
                'sync-xhr=(), '
                'usb=(), '
                'xr-spatial-tracking=(), '
                'unload=*'
            )
        else:
            # 기본 정책 (카메라 접근 차단)
            permissions_policy = (
                'accelerometer=(), '
                'autoplay=(), '
                'camera=(), '
                'display-capture=(), '
                'encrypted-media=(), '
                'geolocation=(), '
                'gyroscope=(), '
                'magnetometer=(), '
                'microphone=(), '
                'midi=(), '
                'payment=(), '
                'picture-in-picture=(), '
                'publickey-credentials-get=(), '
                'sync-xhr=(), '
                'usb=(), '
                'xr-spatial-tracking=(), '
                'unload=*'
            )
        
        response['Permissions-Policy'] = permissions_policy
        return response 