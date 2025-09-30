# LN 결제 프로세스 시나리오 (Blink API 제약 반영)

## 1. 목표 및 배경
- Blink API 기반 라이트닝 결제 흐름을 5단계로 분리해 사용자/관리자 모두가 어디에서 문제가 생겼는지 즉시 파악할 수 있도록 한다.
- `ln_payment` 앱에 결제 상태 머신과 공통 로직을 집약해 다른 상품 유형에도 재사용한다.
- Blink API가 제공하는 이벤트·상태 범위를 현실적으로 활용하고, 부족한 부분은 자체 로직과 UI 피드백으로 보완한다.

## 2. Blink API 제약 요약
- **인보이스 상태**: `lnInvoicePaymentStatus`(`InvoicePaymentStatus`)는 `PENDING`, `PAID`, `EXPIRED`만 제공한다. “QR 스캔 성공”이나 “사용자 잔액 부족” 같은 세부 오류는 알 수 없다.
- **결제 실패 사유**: `lnInvoicePaymentSend` 등에서 반환하는 오류는 문자열(`Error.code`, `Error.message`) 수준이므로 사용자 친화 문구는 자체 매핑이 필요하다.
- **실시간 이벤트**: GraphQL WebSocket(`lnInvoicePaymentStatus`, `myUpdates`)과 webhook(`receive.lightning`)만 공식 지원된다. SSE는 직접 구현해야 한다.
- **입금 확인**: `receive.lightning` webhook payload와 `Transaction.status`(`SUCCESS`, `PENDING`, `FAILURE`)로 상점 지갑 입금 여부를 확인할 수 있다. 사용자 지갑 차감 여부는 별도 이벤트로 제공되지 않는다.
- **인보이스 재발행/취소**: `lnInvoiceCancel` + `lnInvoiceCreate` 조합으로 처리한다. Blink가 인보이스 만료 알림을 주지 않으므로 타이머와 UI 제어는 앱에서 관리해야 한다.

## 3. 전체 흐름 개요
1. 배송정보 입력 후 간소화된 체크아웃 요약 화면에서 결제 버튼을 누르면 `ln_payment` 전용 라우트로 이동한다.
2. 단일 화면에서 5단계 진행 UI를 제공하고, 각 단계가 완료될 때마다 `PaymentTransaction`과 `PaymentStageLog`를 갱신한다.
3. 단계 상태는 WebSocket/SSE/폴링으로 실시간 갱신해 사용자에게 안내한다.
4. 최종 완료 시 주문을 저장하고 마이페이지·이메일 등을 업데이트한다.
5. 스토어 관리자 메뉴 “결제 정보 확인”에서 단계별 로그를 조회해 고객 응대 및 재처리에 활용한다.

## 4. 5단계 사용자 플로우 (UI 중심)
### 단계 1. 결제 준비 & 정보 확인
- **목표**: 배송정보 검증, 재고 soft lock 설정, 결제 요약을 사용자에게 보여주기.
- **백엔드**: 장바구니/재고 재검증 → 부족하면 사용자에게 품절 메시지 및 다른 행동 유도. 재고가 충분하면 `PaymentTransaction` 생성, soft lock(`OrderItemReservation` 등) 기록.
- **UI**: 배송지/상품/최종 금액/결제 수단 요약을 깔끔하게 배치. “결제 진행” CTA 버튼을 강조. 하단에는 “재고 확보 완료” 또는 “재고 확보 실패” 메시지를 표시.
- **실패 처리**: 소프트락 생성 실패 시 CTA 비활성화 및 안내 문구 노출.

### 단계 2. 인보이스 표시 & 결제 대기
- **백엔드**: `lnInvoiceCreate`로 인보이스 생성 → `paymentRequest`, `paymentHash`, 만료시각 저장. 필요 시 `lnInvoiceCancel` 후 재발행.
- **UI**:
  - 화면 상단 진행 표시줄에서 2단계를 활성화하고 1단계를 완료 처리.
  - 중앙에 QR 코드 + 텍스트 인보이스를 Tailwind 기반으로 크게 보여주고, 오른쪽/아래에 120초 타이머 카운트다운과 남은 시간 정보를 표시.
  - 버튼: “결제 취소”만 제공해 흐름을 단순화한다.
  - 상태 메시지: “라이트닝 지갑으로 스캔해주세요.” / “인보이스가 만료되어 재생성이 필요합니다.” 등 실시간 문구.
  - 인보이스 description에는 `제품명 / 수량 / 총액 / 결제자 id` 형식으로 메모를 작성해 Blink 지갑 기록을 구체화한다.
- **이벤트 처리**: WebSocket `lnInvoicePaymentStatus` 또는 폴링으로 상태 감시. `EXPIRED` 발생 시 자동으로 인보이스 폐기 후 UI에서 재생성 버튼 노출.

### 단계 3. 결제 확인 (사용자 송금 결과)
- **백엔드**: `lnInvoicePaymentStatus`에서 `PAID` 확인 → soft lock 유효성 재검증. mismatch 시 실패 처리 및 재시도 옵션 제공.
- **UI**:
  - 진행 표시줄에서 3단계 활성화. “결제 내역 확인 중…” 문구와 로딩 인디케이터 노출.
  - 성공 시 “결제가 정상적으로 확인되었습니다.” 문구와 체크 아이콘 표시.
  - 실패 또는 불확실 시 “결제가 완료되지 않았습니다. 다시 시도하거나 관리자에게 문의하세요.” 메시지 및 재시도 버튼 제공.
- **세부 안내**: Blink에서 구체적 이유를 주지 않으므로, 실패 문구는 포괄적으로 제공하고 필요 시 FAQ 링크나 문의 안내 포함.

### 단계 4. 입금 확인 (스토어 수취 확인)
- **백엔드**: `receive.lightning` webhook 또는 `myUpdates`/`transactionsByPaymentHash`로 `Transaction.status` 수신. `SUCCESS`면 입금 확정, `FAILURE`면 관리자 문의 안내, `PENDING`이면 지연 메시지 유지.
- **UI**:
  - 진행 표시줄에서 4단계 활성화. “스토어 지갑 입금 확인 중…” 텍스트와 로딩 인디케이터.
  - 성공 시 “스토어 입금이 확인되었습니다.”, 실패 시 “입금 확인 중 문제가 발생했습니다. 스토어에 문의해주세요.” 문구 표시.
  - 실패 시 스토어 연락처, 주문번호, 결제 시각 등을 함께 노출해 사용자 지원을 돕는다.
- **재고 처리**: 입금 확정 시 soft lock → 실제 재고 차감.

### 단계 5. 주문 저장 & 완료 안내
- **백엔드**: 주문 레코드 생성, 마이페이지 업데이트, 이메일 발송. `PaymentTransaction` 상태 `completed`로 변경 후 soft lock 제거.
- **UI**:
  - 진행 표시줄에서 마지막 단계 완료 상태로 표시.
  - “결제가 완료되었습니다.” 헤드라인과 함께 주문 요약, 배송 예정 정보, 고객 지원 안내, 마이페이지 링크, 홈으로 이동 버튼 등을 배치.
  - 하단에 “결제 정보 확인하기(스토어)” 버튼을 별도 제공해 상점 측 링크로 이동 가능하도록 한다(로그인 상태에 따라 조건부).

## 5. 예외 및 롤백 처리
- 단계 중 오류 발생 시 `PaymentTransaction.status`를 `failed`로 설정하고 `PaymentStageLog`에 stage/사유/세부 데이터를 기록.
- 2단계 이전 실패 → soft lock 즉시 해제. 3단계 이후 실패 → 재고 유지, 관리자 개입 필요 안내.
- 동일 주문에서 인보이스를 재발행할 수 있도록 `PaymentTransaction`과 `PaymentStageLog` 구조가 재시도 이력을 담도록 설계.

## 6. 데이터 모델 초안
- `PaymentTransaction`
  - `id`, `order_candidate_id`, `store_id`, `user_id`
  - `amount_sats`, `status`(`pending`, `processing`, `failed`, `completed` 등)
  - `current_stage`(1~5), `payment_hash`, `payment_request`, `expires_at`
  - `soft_lock_expires_at`, `metadata`(Blink 원본 JSON 등), `created_at`, `updated_at`
- `PaymentStageLog`
  - `transaction`, `stage`, `status`, `message`, `detail`, `created_at`
  - 재시도/인보이스 재발행/웹훅 수신 등 히스토리 기록
- `OrderItemReservation`
  - 상품별 soft lock 수량, 만료시각, 상태(`active`, `released`, `converted`) 관리

## 7. 비동기 통신 및 UI 지침
- WebSocket(Django Channels) 기반 push를 기본으로 고려하고, 대안으로 3~5초 폴링 + 상태 변경 시 브라우저 알림/토스트 대신 상단 안내 문구 업데이트.
- 진행 표시줄은 Tailwind 기반 컴포넌트로 만들고, 각 단계별로 색상/아이콘/애니메이션을 변경해 직관성을 높인다.
- 상태 문구는 간단하고 이해하기 쉬운 한글 문장으로 유지하며, Blink에서 세부 사유를 제공하지 않을 때는 포괄적인 메시지를 사용한다.
- 인보이스 재생성, 취소, 문의 등 사용자 행동 버튼은 항상 동일 위치에 배치해 혼란을 줄인다.
- 사용자가 "결제 취소"를 누르면 취소 안내 문구를 짧게 표시한 뒤 페이지를 자동 새로고침해 초기 상태로 돌아간다. (다음 결제를 바로 시작할 수 있도록 UX를 단순화)

## 8. 관리자/스토어 지원 기능
- 스토어 관리 > 주문 관리 하위 “결제 정보 확인” 메뉴에서 `PaymentTransaction`, 단계 로그, Blink `Transaction` 세부 정보, 오류 메시지를 확인.
- `FAILED`/지연 상태 주문을 필터링하고, 연락처/주문번호/결제 시간 등을 즉시 볼 수 있는 테이블/디테일 뷰 구성.
- 필요 시 관리자용 재시도(새 인보이스 발행), 환불 매뉴얼 등 추가 기능을 별도 문서로 정의.

## 9. 후속 과제 및 리스크
- Blink `receive.lightning` webhook 설정(https://dev.blink.sv/api/webhooks) 및 Svix 재시도 정책 모니터링이 필수.
- GraphQL WebSocket 연결은 `connection_init` payload에 `X-API-KEY` 포함이 필요하므로 인증 로직을 설계해야 한다.
- webhook 지연/미수신 대비 `transactionsByPaymentHash` 폴링 로직과 경보 체계를 마련한다.
- soft lock 만료/정리 작업은 스케줄러(Celery beat, cron 등)로 주기적으로 실행한다.
- Blink 오류 메시지가 표준화되어 있지 않으므로, 사용자 안내 문구/FAQ/문의 버튼을 충분히 제공한다.

### 수동 주문 복구 흐름
- 스토어 관리자의 **결제 정보 확인** 화면에서 모든 미완료 트랜잭션에 `주문 저장` 버튼이 노출된다. 이미 주문이 연결된 트랜잭션(`status=completed`)은 버튼이 숨겨진다.
- 배송지 정보와 장바구니 스냅샷이 남아 있는 경우, 결제/입금 단계 로그가 비어 있어도 복구를 시도하면 3·4단계 `PaymentStageLog`를 수동 완료 처리한 뒤 주문을 생성한다.
- 생성된 주문은 `manual_restored` 플래그와 `manual_restore_history`(복구 시각/담당자)를 트랜잭션 메타데이터에 남기고, 모든 주문 화면에서 `결제 완료(수동저장)` 라벨로 노출된다.
- 재고가 충분하면 정상 차감하고, 부족하면 재고 차감 없이 주문만 생성한다. 이때 부족한 상품은 `manual_stock_issues` 항목으로 기록돼 관리자 로그에서 추적할 수 있으며, UI 확인 대화상자에 “재고가 부족하면 차감 없이 주문만 생성” 안내를 표시한다.
- 복구 흐름 전체는 Django 메시지를 사용하지 않고 로그에만 남기므로, 운영 중에는 관리자 콘솔/서버 로그를 통해 실패 원인을 파악한다.
