# LN 결제 프로세스 구현 TODO

## 백엔드 핵심
- [x] PaymentTransaction / PaymentStageLog / OrderItemReservation 모델 설계 및 마이그레이션
- [x] Blink GraphQL/WebSocket/Webhook 연결 서비스 정리 (API 키 로딩, connection_init, 재시도 정책 포함)
- [x] Soft lock 생성/만료/전환 로직 구현 및 스케줄러 작업 등록
- [x] 단계별 상태 머신 서비스 구현 (stage 1~5 전환, 재시도/실패 처리, 로그 남기기)
- [x] Webhook 수신 뷰 및 시그니처 검증, transactionsByPaymentHash 폴링 백업 로직 추가

## 프런트엔드(UI)
- [x] 결제 진행 라우트 템플릿/뷰/JS 작성 (Tailwind 진행 표시줄, 실시간 안내 문구, 타이머 포함)
- [x] WebSocket/SSE/폴링 기반 상태 갱신 모듈 구성 및 사용자 액션(재생성/취소/문의) 버튼 처리
- [x] 완료 화면/에러 안내 화면 UX 작성, FAQ/문의 링크 연결

## 관리자/스토어 기능
- [x] “결제 정보 확인” 메뉴 신설 및 리스트/디테일 뷰 구현 (단계 로그/트랜잭션 정보 표시)
- [x] 실패/지연 주문 필터링 및 연락처 안내 UI 구성

## 문서/운영
- [x] README 및 운영 문서에 Blink webhook 설정, WebSocket 인증 절차, 재시도 정책 업데이트
- [x] 배포/환경 변수 점검 (BLINK API 키, 웹훅 엔드포인트, Celery/Redis 설정 등)

## 현재 진행 작업
- [ ] renewal_ln_payment 브랜치에서 meetup 결제 워크플로우 구조 분석
- [ ] 상품 결제 단계 재사용을 위한 공통화/리팩터링 범위 정리
- [ ] 필요한 모델/서비스/템플릿 변경안 작성
