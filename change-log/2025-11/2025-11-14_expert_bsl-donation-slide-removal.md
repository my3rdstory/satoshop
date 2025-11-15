## 개요
- 자동으로 주입된 “BSL 정기 후원” 캐러셀 슬라이드를 DB에서 제거하고, 향후에는 관리자가 어드민에서 직접 입력할 수 있도록 기본 데이터를 비워 둠

## 상세
1. `expert/migrations/0019_remove_bsl_donation_slide.py`에서 `ExpertHeroSlide` 중 “BSL 정기 후원 배너”를 삭제하도록 RunPython 마이그레이션을 추가해 기존 DB에서도 자동으로 슬라이드가 제거되도록 함.
