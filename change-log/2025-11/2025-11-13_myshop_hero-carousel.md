## 개요
- 홈 히어로 영역을 다단 캐러셀 구조로 개편해 메시지·배경을 시간차로 노출하고, 좌/우 네비게이션과 인디케이터, 자동 롤링을 제공
- 장고 어드민에 "히어로 캐러셀 슬라이드" 모델을 추가해 배경 CSS·이미지, 오버레이, 템플릿 기반 HTML 콘텐츠, 전환 간격을 슬라이드별로 관리
- 기본 슬라이드를 데이터 마이그레이션으로 주입해 기존 텍스트/CTA/실시간 지표 카드가 동일한 형태로 노출되도록 보장

## 상세
1. `myshop/models.py`에 `HeroCarouselSlide` 모델을 정의하고 저장/삭제 시 홈 컨텍스트 캐시를 무효화하도록 구현, `myshop/migrations/0026_herocarouselslide.py`와 `0027_seed_hero_carousel.py`에서 스키마 및 기본 데이터를 생성.
2. `myshop/admin.py`에 슬라이드 전용 관리자 화면을 등록해 순서·활성화 토글, 배경·콘텐츠 편집, 작성/수정 시각 확인을 지원.
3. `myshop/views.py`에서 슬라이드를 템플릿으로 렌더링하는 `_build_hero_slides()`를 추가하고, 홈 컨텍스트에 `hero_slides`를 주입해 `myshop/templates/myshop/home.html`에서 새로운 캐러셀 마크업을 출력.
4. `static/myshop/css/home.css`와 `static/myshop/js/home.js`에 전용 스타일·스크립트를 추가해 페이드 전환, 자동 슬라이드, 인디케이터 및 키보드 포커스 안전성을 확보.
5. `README.md`에 히어로 캐러셀 관리 방법을 문서화해 운영자가 HTML/템플릿 조각과 배경 옵션을 쉽게 이해하도록 안내.

> ⚠️ 같은 날 Expert 랜딩 전용 캐러셀을 도입하면서 Myshop 홈 화면은 다시 정적 히어로 섹션으로 복원되었습니다.
