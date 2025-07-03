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
        
        # Permissions Policy 헤더 추가
        # unload 이벤트를 모든 오리진에서 허용하여 Django admin 호환성 보장
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