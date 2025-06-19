# SatoShop CSS 구조 가이드

## 📁 CSS 파일 구조

```
static/css/
├── bulma.min.css      # Bulma CSS 프레임워크
├── themes.css         # 라이트/다크 모드 테마 시스템
├── custom.css         # 전역 스타일 (레이아웃, 폰트, 특수 스타일)
├── components.css     # 재사용 가능한 컴포넌트 스타일
├── pages.css          # 페이지별 특화 스타일
└── easymde.min.css    # 마크다운 에디터 스타일
```

## 🎨 스타일 계층 구조

### 1. **themes.css** - 테마 시스템
- CSS 변수 정의 (라이트/다크 모드)
- 모든 Bulma 컴포넌트 테마 적용
- 일관된 색상 시스템
- 자동 테마 전환 지원

### 2. **custom.css** - 전역 기본 스타일
- 레이아웃 (Sticky Footer, 네비게이션)
- 폰트 설정 (Noto Sans KR)
- 테마 전환 버튼
- 특수 스타일링

### 3. **components.css** - 재사용 컴포넌트
- 카드 컴포넌트 (`.card-component`)
- 상품 카드 (`.product-card`)
- 스토어 카드 (`.store-card`)
- 폼 섹션 (`.form-section`)
- 정보 카드 (`.info-card`)
- 상태 표시 (`.status-*`)
- 검색 컴포넌트 (`.search-*`)

### 4. **pages.css** - 페이지별 특화 스타일
- 홈페이지 (`.home-*`)
- 스토어 탐색 (`.browse-*`)
- 계정 페이지 (`.account-*`)
- 주문/구매 (`.purchase-*`, `.checkout-*`)
- 에러 페이지 (`.not-found-*`, `.inactive-*`)

## 🔧 사용 방법

### 기본 템플릿 구조
```html
{% extends 'myshop/base.html' %}

{% block extra_css %}
<!-- 페이지별 추가 스타일이 필요한 경우에만 사용 -->
{% endblock %}
```

### 컴포넌트 클래스 사용 예시
```html
<!-- 상품 카드 -->
<div class="product-card">
  <img src="..." class="product-image" alt="...">
  <div class="discount-tag">20% 할인</div>
  <div class="price-badge">₿ 0.001</div>
</div>

<!-- 정보 카드 -->
<div class="info-card">
  <h3 class="info-card-title">
    <i class="fas fa-info-circle"></i>
    정보 제목
  </h3>
  <div class="info-item">
    <span class="info-label">라벨</span>
    <span class="info-value">값</span>
  </div>
</div>

<!-- 상태 표시 -->
<span class="status-indicator status-success">
  <i class="fas fa-check"></i>
  완료
</span>
```

## 🎯 마이그레이션 가이드

### 기존 인라인 스타일 → 컴포넌트 클래스

**Before (인라인 스타일):**
```html
{% block extra_css %}
<style>
  .my-card {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-color);
    transition: all 0.3s ease;
  }
</style>
{% endblock %}

<div class="my-card">...</div>
```

**After (컴포넌트 클래스):**
```html
{% block extra_css %}
<!-- 스타일은 components.css에서 로드됩니다 -->
{% endblock %}

<div class="card-component">...</div>
```

### 페이지별 클래스명 규칙

- **홈페이지**: `.home-*` (예: `.home-hero`, `.home-features-section`)
- **계정 페이지**: `.account-*` (예: `.account-card`, `.account-edit-menu`)
- **스토어 페이지**: `.store-*` (예: `.store-header`, `.store-card`)
- **주문 페이지**: `.purchase-*`, `.checkout-*`

## 🌙 테마 시스템 (라이트/다크 모드)

### 테마 전환 방식
`themes.css`에서 CSS 변수를 사용하여 라이트/다크 모드를 구현합니다:

```css
/* 라이트 모드 (기본) */
:root {
  --bg-primary: #ffffff;
  --text-primary: #2c2c2c;
  --bulma-primary: #f7931a;  /* 비트코인 오렌지 */
}

/* 다크 모드 */
[data-theme="dark"] {
  --bg-primary: #1a1a1a;
  --text-primary: #ffffff;
  --bulma-primary: #f7931a;  /* 동일한 브랜드 색상 유지 */
}
```

### 지원하는 컴포넌트
- 모든 Bulma 컴포넌트 (카드, 버튼, 네비게이션 등)
- 폼 요소 (입력 필드, 드롭다운, 체크박스)
- 테이블, 모달, 알림, 태그
- 커스텀 컴포넌트 (상품 카드, 정보 카드 등)

### 테마 전환 버튼
우측 하단의 플로팅 버튼으로 테마를 전환할 수 있습니다:
- 🌙 다크 모드로 전환
- ☀️ 라이트 모드로 전환
- 사용자 설정이 localStorage에 저장됨

## 📱 반응형 디자인

모든 컴포넌트는 모바일 우선으로 설계되었으며, 미디어 쿼리를 통해 반응형을 지원합니다:

```css
/* 모바일 (기본) */
.component { ... }

/* 태블릿 이상 */
@media (max-width: 768px) {
  .component { ... }
}
```

## ✅ 장점

1. **유지보수성**: 중복 코드 제거, 일관된 스타일
2. **성능**: CSS 파일 캐싱, 인라인 스타일 제거
3. **확장성**: 새로운 컴포넌트 쉽게 추가 가능
4. **일관성**: 디자인 시스템 기반 통일된 UI
5. **개발 효율성**: 재사용 가능한 컴포넌트

## 🎉 완료된 개선 사항

- [x] **테마 시스템 분리**: `themes.css`로 라이트/다크 모드 통합 관리
- [x] **인라인 스타일 제거**: 모든 템플릿의 `<style>` 태그 제거
- [x] **컴포넌트 모듈화**: 재사용 가능한 컴포넌트 클래스 정의
- [x] **페이지별 스타일 분리**: 각 페이지 특화 스타일 독립 관리
- [x] **알림 컴포넌트**: 통일된 알림 스타일 시스템
- [x] **인증 페이지 스타일**: 로그인/회원가입 페이지 통합 스타일
- [x] **계정 폼 스타일**: 비밀번호 변경 등 계정 관련 폼 스타일
- [x] **테마 전환 JavaScript**: 자동 테마 감지 및 전환 기능

## 🚀 향후 개선 사항

- [ ] CSS 압축 및 최적화
- [ ] 컴포넌트 문서화 확장  
- [ ] 스타일 가이드 페이지 추가
- [ ] CSS 변수 더 세분화
- [ ] 애니메이션 효과 개선 