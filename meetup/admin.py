# meetup/admin.py - 새로운 모듈화된 구조
# 각 기능별로 분리된 admin 모듈들을 import

# 모든 admin 클래스들이 이 패키지를 통해 자동으로 등록됩니다
from .admin import *

# 기존의 모든 admin 클래스들은 admin/ 패키지 내의 별도 모듈들로 이동되었습니다:
#
# 📁 admin/
# ├── __init__.py              - 모든 모듈을 import하는 진입점
# ├── filters.py               - 커스텀 필터들 (HasParticipantsFilter 등)
# ├── meetup_admin.py          - Meetup 모델 관련 admin
# ├── meetup_image_admin.py    - MeetupImage 모델 admin  
# ├── meetup_option_admin.py   - MeetupOption, MeetupChoice 모델 admin
# ├── meetup_order_admin.py    - MeetupOrder, MeetupOrderOption 모델 admin
# └── meetup_participant_admin.py - 참가자 관리 admin (프록시 모델 포함)
#
# 🎯 장점:
# - 각 모듈은 독립적으로 관리되며, 기능별로 명확하게 분리
# - 코드 가독성 및 유지보수성 향상
# - 팀 개발 시 충돌 최소화
# - 필요한 모듈만 수정 가능
#
# 🔧 사용법:
# - 밋업 관련 수정: admin/meetup_admin.py
# - 주문 관련 수정: admin/meetup_order_admin.py  
# - 참가자 관리 수정: admin/meetup_participant_admin.py
# - 필터 수정: admin/filters.py








