# 오픈그래프 컴포넌트 사용 가이드

SatoShop에서 오픈그래프 메타 태그를 효율적으로 관리하기 위한 컴포넌트 시스템입니다.

## 🎯 목적

- **중복 제거**: 모든 페이지에서 반복되는 오픈그래프 코드 제거
- **중앙 관리**: 한 곳에서 오픈그래프 설정 관리
- **쉬운 사용**: 간단한 문법으로 페이지별 커스터마이징
- **자동화**: 페이지 타입에 따른 자동 설정

## 📁 파일 구조

```
myshop/
├── templatetags/
│   ├── __init__.py
│   └── opengraph_tags.py          # 커스텀 템플릿 태그
├── templates/myshop/components/
│   ├── opengraph_meta.html        # 오픈그래프 컴포넌트 (고급)
│   └── simple_opengraph.html      # 간단한 오픈그래프 컴포넌트
└── context_processors.py          # 컨텍스트 프로세서 (자동화)
```

## 🚀 사용 방법

### 방법 1: 간단한 Include 컴포넌트 (추천)

가장 간단하고 직관적인 방법입니다.

#### 기본 사용법

```django
{% extends 'myshop/base.html' %}

{% block title %}페이지 제목 - SatoShop{% endblock %}

<!-- 오픈그래프 설정 -->
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title="페이지 제목 - SatoShop" description="페이지 설명" %}
{% endblock %}
```

#### 동적 데이터 사용

```django
<!-- 스토어 페이지 -->
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title=store.store_name|add:" - SatoShop" description=store.store_description image=store.images.first.file_url %}
{% endblock %}

<!-- 제품 페이지 -->
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title=product.title|add:" - "|add:store.store_name description=product.description type="product" image=product.images.first.file_url %}
{% endblock %}
```

### 방법 2: 커스텀 템플릿 태그 (고급)

더 많은 기능과 자동화를 원할 때 사용합니다.

#### 설정

`myshop/templates/myshop/base.html`에 추가:

```django
{% load static %}
{% load opengraph_tags %}  <!-- 추가 -->
```

#### 사용법

```django
{% extends 'myshop/base.html' %}

<!-- 자동 오픈그래프 (페이지 타입 기반) -->
{% block opengraph_meta %}
  {% auto_opengraph_meta "store_detail" %}
{% endblock %}

<!-- 커스텀 파라미터와 함께 -->
{% block opengraph_meta %}
  {% auto_opengraph_meta "product_detail" title=product.title description=product.description %}
{% endblock %}
```

### 방법 3: 컨텍스트 프로세서 (완전 자동화)

뷰에서 자동으로 오픈그래프 데이터를 생성합니다.

#### 뷰에서 사용

```python
from myshop.context_processors import auto_opengraph_meta

def store_detail_view(request, store_id):
    store = get_object_or_404(Store, store_id=store_id)
    
    context = {
        'store': store,
        'opengraph': auto_opengraph_meta(request, 'store_detail', store=store)
    }
    return render(request, 'stores/store_detail.html', context)
```

#### 템플릿에서 사용

```django
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title=opengraph.title description=opengraph.description image=opengraph.image %}
{% endblock %}
```

## 📝 페이지별 사용 예시

### 홈페이지

```django
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title=site_settings.site_title|add:" - "|add:site_settings.site_description description=site_settings.hero_description %}
{% endblock %}
```

### 스토어 상세 페이지

```django
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title=store.store_name|add:" - SatoShop" description=store.store_description|truncatewords:30 image=store.images.first.file_url %}
{% endblock %}
```

### 제품 상세 페이지

```django
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title=product.title|add:" - "|add:store.store_name description=product.description|truncatewords:30 type="product" image=product.images.first.file_url %}
{% endblock %}
```

### 스토어 생성 페이지

```django
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title="스토어 만들기 - SatoShop" description="SatoShop에서 나만의 비트코인 온라인 스토어를 5분 만에 만들어보세요." %}
{% endblock %}
```

## 🔧 컴포넌트 파라미터

`simple_opengraph.html` 컴포넌트는 다음 파라미터를 받습니다:

| 파라미터 | 필수 | 기본값 | 설명 |
|---------|------|--------|------|
| `title` | ❌ | `site_settings.site_title` | 페이지 제목 |
| `description` | ❌ | `site_settings.site_description` | 페이지 설명 |
| `type` | ❌ | `website` | 오픈그래프 타입 (`website`, `product` 등) |
| `image` | ❌ | `site_settings.og_default_image` | 이미지 URL |

## 🎨 기존 페이지 마이그레이션

기존 페이지들을 새로운 컴포넌트로 변경하는 방법:

### Before (기존 방식)

```django
<!-- Open Graph Meta Tags -->
{% block og_title %}{{ store.store_name }} - SatoShop{% endblock %}
{% block og_description %}{{ store.store_description|truncatewords:30 }}{% endblock %}
{% block og_type %}website{% endblock %}
{% block og_image %}{{ store.images.first.file_url }}{% endblock %}

<!-- Twitter Card Meta Tags -->
{% block twitter_title %}{{ store.store_name }} - SatoShop{% endblock %}
{% block twitter_description %}{{ store.store_description|truncatewords:30 }}{% endblock %}
{% block twitter_image %}{{ store.images.first.file_url }}{% endblock %}
```

### After (새로운 방식)

```django
<!-- 오픈그래프 설정 -->
{% block opengraph_meta %}
  {% include 'myshop/components/simple_opengraph.html' with title=store.store_name|add:" - SatoShop" description=store.store_description|truncatewords:30 image=store.images.first.file_url %}
{% endblock %}
```

## ✅ 장점

1. **코드 중복 제거**: 13줄 → 3줄로 단축
2. **중앙 관리**: 한 곳에서 오픈그래프 구조 변경 가능
3. **일관성**: 모든 페이지에서 동일한 구조 보장
4. **유지보수**: 새로운 메타 태그 추가 시 컴포넌트만 수정
5. **자동 fallback**: 파라미터가 없으면 자동으로 기본값 사용

## 🔄 마이그레이션 계획

1. **1단계**: 새로운 컴포넌트 생성 (완료)
2. **2단계**: 기존 베이스 템플릿에 `opengraph_meta` 블록 추가
3. **3단계**: 각 페이지별로 점진적 마이그레이션
4. **4단계**: 기존 오픈그래프 블록들 제거

## 🚨 주의사항

- 기존 `{% block og_title %}` 등의 블록과 새로운 `{% block opengraph_meta %}` 블록을 동시에 사용하지 마세요
- 이미지 URL은 절대 경로를 사용하세요
- 설명은 160자 이내로 제한하세요 (`|truncatewords:30` 사용 권장)

## 📚 참고 자료

- [Open Graph Protocol](https://ogp.me/)
- [Twitter Cards](https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards)
- [Django Template Tags](https://docs.djangoproject.com/en/stable/howto/custom-template-tags/) 