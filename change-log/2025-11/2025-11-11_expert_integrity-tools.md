# Expert 계약 위변조 방지 도구 및 디지털 서명

## 배경
- 최종 계약서 PDF가 외부에서 임의로 수정되더라도 동일한 파일인지 증빙할 수 있는 도구가 없어 운영자가 수작업으로 비교해야 했음.
- 디지털 인증서 기반 서명이 없어 PDF 뷰어에서 즉시 위변조 여부를 확인할 수 없었음.

## 변경 사항
- `DirectContractDocument`에 `final_pdf_hash` 필드를 추가하고 계약 완료 시 SHA-256 해시를 계산해 저장, 기존 레코드도 데이터 마이그레이션으로 채움.
- `/expert/contracts/direct/verify/` 경로에 위변조 검증 도구를 추가하여 계약 보관함 옆 메뉴에서 업로드한 PDF와 저장된 해시를 비교할 수 있도록 함.
- pyHanko 기반 디지털 서명 파이프라인을 도입해 `EXPERT_SIGNER_CERT_*` 환경 변수로 PKCS#12 인증서를 설정하면 최종 PDF에 전자서명을 자동 삽입함.
- 해시 비교/서명 관련 안내를 README에 정리하고 Render 배포 시 비밀 정보로 인증서를 관리하는 절차를 문서화함.
- `.env.local`에 서명용 환경 변수를 기본 포함시키고, Render 빌드 스크립트가 `scripts/render_setup_signer.sh`를 통해 base64 값을 `/tmp/expert-signer.p12`로 복원하도록 자동화함.

## 검증
- `uv run python manage.py migrate` 후 기존 계약 상세에서 `final_pdf_hash`가 비어 있지 않은지 확인.
- `/expert/contracts/direct/verify/`에서 계약을 선택하고 원본 PDF를 업로드했을 때 “원본과 일치합니다.” 메시지가 표시되는지 검증.
- 같은 화면에서 PDF를 임의 편집 후 업로드하면 해시 불일치 경고가 뜨는지 확인.
- `EXPERT_SIGNER_CERT_*` 값을 설정한 뒤 새 계약을 체결하면 Adobe Reader에서 전자서명이 “유효”로 표시되는지 확인.
