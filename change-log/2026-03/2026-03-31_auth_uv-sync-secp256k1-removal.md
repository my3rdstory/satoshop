# secp256k1 네이티브 의존성 제거

## 요약
- `uv sync`가 `secp256k1` 빌드 단계에서 `pkg-config` 요구로 실패하던 문제를 해소했다.
- Nostr(BIP340)와 LNURL-auth(ECDSA) 서명 검증을 공용 순수 파이썬 유틸로 옮겼다.
- 빌드 스크립트와 설치 문서를 새 의존성 구조에 맞춰 정리했다.

## 상세 변경
- `myshop/crypto.py` 신규
  - Nostr x-only 공개키 검증
  - BIP340 Schnorr 서명 검증
  - secp256k1 ECDSA digest 검증
- `api/nostr_auth.py`
  - 공개키 정규화/챌린지 서명 검증을 공용 유틸 호출로 변경
- `accounts/nostr_service.py`
  - 웹 로그인 이벤트 서명 검증을 공용 BIP340 유틸로 변경
- `accounts/lnurl_service.py`
  - LNURL-auth 서명 검증을 `ecdsa` 기반 공용 유틸로 변경
- `pyproject.toml`
  - `secp256k1` 제거, `ecdsa` 추가
- `build.sh`
  - `secp256k1` 재설치 분기 제거, `ecdsa` 확인으로 정리
- `README.md`
  - 새 설치 메모와 의존성 설명 반영

## 운영 메모
- 이번 변경은 마이그레이션이 필요 없다.
- 수동 검증 시에는 `uv sync` 후 Nostr 로그인과 LNURL 로그인 흐름을 각각 한 번씩 확인하면 된다.
