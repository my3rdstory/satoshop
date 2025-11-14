## 개요
- Expert 랜딩 페이지 상단을 캐러셀 구조로 재구성해 계약 설명/CTA를 여러 장으로 순환 노출하고, 좌우 네비게이션·인디케이터·자동 롤링을 지원
- 어드민에 "Expert 히어로 슬라이드" 모델을 추가해 배경 CSS·이미지·오버레이와 템플릿 기반 HTML 콘텐츠, 전환 간격을 슬라이드별로 관리
- 데이터 마이그레이션으로 기존 정적 히어로 콘텐츠를 기본 슬라이드로 주입해 즉시 동일한 UI가 출력되도록 보장

## 상세
1. `expert/models.py`에 `ExpertHeroSlide`를 정의하고, `expert/migrations/0015_expertheroslide.py`에서 스키마를 추가한 뒤 `0016_seed_expert_hero_slides.py`로 기본 슬라이드를 생성.
2. `expert/admin.py`에 슬라이드 전용 어드민을 등록해 순서/활성화 토글·배경/콘텐츠 편집·전환 간격 설정·메타 정보 열람을 지원.
3. `expert/views.py`에 `_build_expert_hero_slides()` 헬퍼를 추가하고 `ExpertLandingView` 컨텍스트에 `hero_slides`를 주입, `expert/templates/expert/direct_contract_start.html`을 캐러셀 마크업으로 교체.
4. `expert/static/expert/css/direct_contract_start.css`와 `expert/static/expert/js/direct_contract_start.js`에 전용 스타일/스크립트를 추가해 페이드 전환·자동 롤링·버튼/인디케이터 상호작용을 구현.
5. `README.md`에 Expert 캐러셀 관리 방법을 문서화하고, 기존 Myshop용 안내는 복원 사실을 명시해 혼선을 방지.
