"""
S3 호환 오브젝트 스토리지 설정 예시
이 파일을 참고해서 Django settings.py에 설정을 추가하세요.
"""

# ================================
# S3 오브젝트 스토리지 기본 설정
# ================================

# iwinv 오브젝트 스토리지 접속 정보
S3_ACCESS_KEY_ID = 'your-access-key-id'           # 액세스 키 ID
S3_SECRET_ACCESS_KEY = 'your-secret-access-key'   # 시크릿 액세스 키
S3_BUCKET_NAME = 'your-bucket-name'               # 버킷 이름
S3_ENDPOINT_URL = 'https://kr.object.iwinv.kr'    # iwinv 엔드포인트 URL
S3_REGION_NAME = 'kr-standard'                    # 리전 이름 (iwinv의 경우)

# ================================
# S3 추가 설정 (선택사항)
# ================================

# SSL 사용 여부
S3_USE_SSL = True

# 파일 덮어쓰기 여부 (False면 파일명에 숫자 추가)
S3_FILE_OVERWRITE = False

# 커스텀 도메인 (CDN 등을 사용하는 경우)
# S3_CUSTOM_DOMAIN = 'your-cdn-domain.com'

# ================================
# 파일 업로드 관련 설정
# ================================

# 최대 파일 크기 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# 허용되는 파일 확장자 (None이면 모든 확장자 허용)
ALLOWED_FILE_EXTENSIONS = [
    # 이미지
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
    # 문서
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.txt', '.rtf', '.odt', '.ods', '.odp',
    # 압축파일
    '.zip', '.rar', '.7z', '.tar', '.gz',
    # 기타
    '.csv', '.xml', '.json',
]

# 임시 파일 만료 시간 (시간 단위)
TEMP_FILE_EXPIRE_HOURS = 24

# ================================
# Django 기본 스토리지 설정 (선택사항)
# ================================

# 기본 파일 스토리지를 S3로 설정하려면 주석 해제
# DEFAULT_FILE_STORAGE = 'commons.storage.backends.S3Storage'

# 정적 파일도 S3에 저장하려면 주석 해제 (주의: 개발 환경에서는 권장하지 않음)
# STATICFILES_STORAGE = 'commons.storage.backends.S3Storage'

# ================================
# 환경 변수 사용 예시
# ================================

"""
실제 운영 환경에서는 민감한 정보를 환경 변수로 관리하는 것을 권장합니다.

.env 파일에 다음과 같이 설정:
```
S3_ACCESS_KEY_ID=your-access-key-id
S3_SECRET_ACCESS_KEY=your-secret-access-key
S3_BUCKET_NAME=your-bucket-name
S3_ENDPOINT_URL=https://kr.object.iwinv.kr
S3_REGION_NAME=kr-standard
```

settings.py에서 다음과 같이 사용:
```python
import os
from dotenv import load_dotenv

load_dotenv()

S3_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID')
S3_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL')
S3_REGION_NAME = os.getenv('S3_REGION_NAME', 'kr-standard')
```
"""

# ================================
# 추가 보안 설정
# ================================

# CORS 설정 (필요한 경우)
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]

# 파일 URL 만료 시간 (초 단위, 기본값 3600초=1시간)
S3_PRESIGNED_URL_EXPIRATION = 3600

# ================================
# 모니터링 및 로깅
# ================================

# S3 작업 로깅 설정
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/s3_storage.log',
        },
    },
    'loggers': {
        'commons.storage': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
} 