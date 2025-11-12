# SatoShop Expert - Architecture Draft

## 1. 목표
- 라이트닝 네트워크 기반 용역 계약(Expert) 워크플로우 제공
- 계약 생성부터 쌍방 서명, 지급 관리까지 단일 흐름으로 연결
- 기존 SatoShop 계정 및 라이트닝 인증 체계를 재사용하되, 독립된 UI/UX 제공

## 2. 도메인 개요
- **ExpertProfile**: 수행자(엑스퍼트) 등록 정보. 향후 엑스퍼트 목록/검색 기능 확장 대비.
- **Contract**: 계약 본문 및 전반 상태. 생성자, 제목, 해시, 진행 상태 등을 포함.
- **ContractParticipant**: 계약에 참여하는 의뢰자/수행자. 역할, 라이트닝 인증 식별자, 서명/동의 상태 보관.
- **ContractDetail**: 계약 본문/조건(마크다운 내용, 일정, 금액, 지불 방식 등) 중심 정보.
- **PaymentMilestone**: 분할 지급 조건 관리. 일괄 지급 시 단일 레코드로 통합 가능.
- **ContractAttachment**: 계약에 첨부된 PDF 등 부속서류. S3 등 외부 스토리지 연동 전제.
- **ContractMessage**: 계약 진행 중 채팅 로그. 실시간 WebSocket 채널과 연동되며, 계약서 PDF 생성 시 부속 문서로 첨부.
- **ContractChatSession**: 계약별 채팅 연결 정보를 관리(예: UUID 기반 룸, WebSocket 토큰).
- **ContractAuditLog**: 주요 이벤트(생성, 수정, 서명, 지급 확인 등)에 대한 추적 레코드.
- **ContractAccessToken**: 계약서 접근용 UUID 및 권한 제어.

## 3. 상태 흐름 (Contract.status)
1. `draft` – 생성자 작성 중
2. `pending_counterparty` – 한쪽이 확정, 상대방 확인 대기
3. `awaiting_signature` – 상대방도 조건 입력 완료, 최종 서명 대기
4. `signed` – 양측 서명 완료, 해시 확정/보관
5. `payment_pending` – 지급 단계 처리 중 (분할 포함)
6. `completed` – 모든 지급/확인 종료
7. `cancelled` – 계약 무효화

## 4. 주요 기능 흐름
1. **랜딩 페이지** (`/expert/`)
   - 서비스 소개, 직접 계약 생성 버튼, 엑스퍼트 선택 계약(준비중) UI.
2. **계약 생성 (직접)** (`/expert/contracts/new`)
   - 라이트닝 인증 확인 → 참가자 역할 선택 → 계약 본문/조건 입력.
   - 파일 첨부(최대 20개/파일당 10MB) 및 미리보기(HTMX).
   - 지불 조건: 일괄/분할. 분할 시 단계별 금액 합 검증.
   - 서명(드로잉) 캡처 → 저장 (향후 PNG/SVG 등으로 보관).
   - 진행 버튼 시 해시 생성, Contract + ContractDetail persist.
3. **상대방 초대/확정**
   - 계약 링크 공유 (UUID), 상대방 라이트닝 인증 후 접근.
   - 상대방 조건 확인/추가 정보 입력, 동의 체크 → 서명.
4. **계약 확정**
   - 양측 서명 시 최종 Contract 상태 전이, 계약서 PDF 생성/보관.
   - 이메일 발송 요청(비동기 작업 예정).
5. **지급 관리**
   - 수행자가 인보이스(라이트닝) 등록 → QR 자동 생성.
   - 의뢰자는 QR 스캔/결제 진행, 상태 업데이트(수행자 확인 포함).

## 5. 기술 선택
- **프론트엔드**: Bulma + HTMX + Vanilla JS (요구사항 기반). 독립 `expert/base.html`.
- **스토리지**: 기존 `storage` 앱 재사용(첨부 파일). 추후 S3 설정 연계.
- **PDF/서명**: 초기 버전은 플레이스홀더/기본 구조, 추후 실제 PDF 렌더러 통합.
- **채팅**: Django Channels(WebSocket) 기반 실시간 통신. 개발/테스트 환경에서는 InMemoryChannelLayer, 운영에서는 Redis Channel Layer 사용을 전제.
- **PDF/채팅 아카이브**: ReportLab 기반 간단 PDF 렌더링으로 계약/채팅 로그를 첨부 문서화.
- **이메일**: Django 이메일 백엔드를 사용하며, Gmail SMTP 계정(어드민 설정)으로 계약 확정 시 자동 발송.

## 6. 초기 개발 범위 (1차 스프린트)
1. 앱 스캐폴딩 및 URL 구조 확립.
2. 핵심 모델 (Contract, ContractParticipant, ContractDetail, PaymentMilestone, ContractAttachment) 마이그레이션.
3. 직접 계약 생성 UI 기본 골격 + 최소 유효 필드 저장.
4. 계약 미리보기/미완성 상태 관리(HTMX 기반 저장 전 검증).
5. 계약 접근 제어(라이트닝 인증 유저만 접근) 기본 훅.

## 7. 향후 고려사항
- 라이트닝 인증 연동 및 세션 만료 처리.
- 채팅 기능 실시간성 향상(WebSocket) 여부 검토.
- 계약서 PDF 템플릿/표준 문구 관리자 설정.
- 이메일 발송을 위한 비동기 큐/작업자 구성.
- BSL 해시 중계/검증 로직 구체화.
