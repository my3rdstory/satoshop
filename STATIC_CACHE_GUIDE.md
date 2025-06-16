# 정적 파일 해시 기반 캐시 무효화 가이드

## 개요

이 시스템은 CSS, JS 파일이 변경될 때 브라우저 캐시를 자동으로 무효화하기 위해 해시 기반 버전 관리를 제공합니다.

## 주요 기능

### 1. Django ManifestStaticFilesStorage
- 정적 파일 수집 시 자동으로 해시 기반 파일명 생성
- `style.css` → `style.a1b2c3d4.css`
- 매니페스트 파일(`staticfiles.json`)을 통한 파일 매핑 관리

### 2. 커스텀 템플릿 태그
- `{% load static_versioned %}` - 템플릿에서 로드
- `{% static_v 'css/style.css' %}` - 해시 기반 URL 생성
- `{% css_v 'style.css' %}` - CSS 파일 전용 (css/ 자동 추가)
- `{% js_v 'script.js' %}` - JS 파일 전용 (js/ 자동 추가)
- `{% static_hash 'css/style.css' %}` - 해시값만 반환

### 3. 관리 명령어
- `python manage.py show_static_hashes` - 파일 해시 정보 확인
- `python manage.py clear_static_cache` - 해시 캐시 지우기

## 설정

### settings.py
```python
# 정적 파일 저장소 설정 - 해시 기반 캐시 무효화
# DEBUG 모드에서는 기본 스토리지 사용, 프로덕션에서는 ManifestStaticFilesStorage 사용
if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# 백업용 시간 기반 버전 (기존 유지)
STATIC_VERSION = str(int(time.time()))
```

### 빌드 스크립트
```bash
# 정적 파일 수집 시 기존 파일 지우고 새로 생성
python manage.py collectstatic --noinput --clear
```

## 템플릿 사용법

### 기본 사용법
```html
{% load static_versioned %}

<!-- CSS 파일 -->
<link rel="stylesheet" href="{% css_v 'components.css' %}">
<link rel="stylesheet" href="{% static_v 'css/themes.css' %}">

<!-- JavaScript 파일 -->
<script src="{% js_v 'common.js' %}"></script>
<script src="{% static_v 'js/product-detail.js' %}"></script>

<!-- 해시값만 필요한 경우 -->
<script>
    const cssHash = '{% static_hash "css/components.css" %}';
    console.log('CSS 파일 해시:', cssHash);
</script>
```

### 기존 코드 마이그레이션
```html
<!-- 기존 -->
<link rel="stylesheet" href="{% static 'css/style.css' %}?v={{ STATIC_VERSION }}">

<!-- 새로운 방식 -->
<link rel="stylesheet" href="{% css_v 'style.css' %}">
```

## 관리 명령어 사용법

### 1. 해시 정보 확인
```bash
# 모든 파일의 해시 정보 확인
uv run python manage.py show_static_hashes

# CSS 파일만 확인
uv run python manage.py show_static_hashes --type css

# JS 파일만 확인
uv run python manage.py show_static_hashes --type js

# 상세 정보 포함 (파일 크기 등)
uv run python manage.py show_static_hashes --detailed
```

### 2. 캐시 지우기
```bash
# 모든 정적 파일 캐시 지우기
uv run python manage.py clear_static_cache --all

# 특정 패턴의 캐시만 지우기
uv run python manage.py clear_static_cache --pattern "css/*"
uv run python manage.py clear_static_cache --pattern "js/*"
```

## 환경별 동작 방식

### 개발 환경 (DEBUG=True)
- **사용 스토리지**: `StaticFilesStorage` (기본)
- **파일 제공**: Django 개발 서버가 직접 제공
- **캐시 무효화**: 파일 변경 시 즉시 반영
- **장점**: 개발 편의성, 빠른 피드백
- **단점**: 브라우저 캐시 문제 가능성

### 프로덕션 환경 (DEBUG=False)
- **사용 스토리지**: `ManifestStaticFilesStorage`
- **파일 제공**: 웹서버(nginx 등)가 정적 파일 제공
- **캐시 무효화**: 해시 기반 파일명으로 자동 무효화
- **장점**: 최적화된 캐시 관리, 성능 향상
- **단점**: collectstatic 실행 필요

## 동작 원리

### 1. ManifestStaticFilesStorage (프로덕션)
1. `collectstatic` 실행 시 각 파일의 내용을 기반으로 해시 생성
2. 해시가 포함된 새 파일명으로 복사 (`style.a1b2c3d4.css`)
3. `staticfiles.json` 매니페스트 파일에 원본 → 해시 파일명 매핑 저장
4. 템플릿에서 `{% static %}` 태그 사용 시 자동으로 해시 파일명 반환

### 2. 커스텀 템플릿 태그
1. ManifestStaticFilesStorage 활성화 시: Django 내장 기능 사용
2. 비활성화 시: 파일 내용 기반 MD5 해시 생성하여 쿼리 파라미터로 추가
3. 해시 값은 5분간 캐시되어 성능 최적화

## 장점

### 1. 자동 캐시 무효화
- 파일 내용이 변경되면 해시가 자동으로 변경됨
- 브라우저가 새 파일을 자동으로 다운로드

### 2. 성능 최적화
- 변경되지 않은 파일은 브라우저 캐시 활용
- 해시 계산 결과를 캐시하여 서버 부하 최소화

### 3. 배포 안정성
- 새 버전 배포 시 이전 버전 파일과 충돌 없음
- 점진적 배포 시에도 안정적 동작

## 주의사항

### 1. 첫 배포 시
```bash
# 정적 파일 수집 전 기존 파일 정리
uv run python manage.py collectstatic --clear --noinput
```

### 2. 개발 환경에서
- `DEBUG=True`일 때는 기본 StaticFilesStorage 사용 (개발 편의성)
- `DEBUG=False`일 때만 ManifestStaticFilesStorage 활성화 (프로덕션)
- 개발 중에는 파일 변경 시 즉시 반영, 프로덕션에서는 해시 기반 캐시 무효화

### 3. CDN 사용 시
- CDN 캐시도 함께 무효화 필요
- 해시 기반 파일명으로 자동 해결됨

## 문제 해결

### 1. 매니페스트 파일 오류
```bash
# 정적 파일 재수집
uv run python manage.py collectstatic --clear --noinput
```

### 2. 캐시 문제
```bash
# 해시 캐시 지우기
uv run python manage.py clear_static_cache --all
```

### 3. 파일을 찾을 수 없음
```bash
# 파일 해시 정보 확인
uv run python manage.py show_static_hashes --detailed
```

## 예제 출력

### show_static_hashes 명령어 출력 예시
```
📊 정적 파일 해시 정보 (all 파일)
================================================================================
📄 css/components.css                    | 🔑 a1b2c3d4 | 📦 29.0KB  
📄 css/themes.css                        | 🔑 e5f6g7h8 | 📦 16.0KB  
📄 js/common.js                          | 🔑 i9j0k1l2 | 📦 4.3KB   
📄 js/product-detail.js                  | 🔑 m3n4o5p6 | 📦 6.7KB   
================================================================================
✅ 총 4개의 파일 처리 완료
🔄 ManifestStaticFilesStorage가 활성화되어 있습니다.
📋 매니페스트 파일: /path/to/staticfiles/staticfiles.json
```

이 시스템을 통해 정적 파일의 효율적인 캐시 관리와 자동 무효화가 가능합니다. 