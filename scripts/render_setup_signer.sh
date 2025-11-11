#!/usr/bin/env bash
# Render/로컬 공통: EXPERT_SIGNER_CERT_BASE64 값을 파일로 복원하고 경로를 노출한다.

set -euo pipefail

CERT_PATH=${EXPERT_SIGNER_CERT_PATH:-}
CERT_BASE64=${EXPERT_SIGNER_CERT_BASE64:-}

# base64 값이 없으면 아무 작업 없음
if [ -z "$CERT_BASE64" ]; then
  exit 0
fi

# 기본 경로가 없으면 /tmp 이하에 생성
if [ -z "$CERT_PATH" ]; then
  CERT_PATH="/tmp/expert-signer.p12"
fi

export EXPERT_SIGNER_CERT_PATH="$CERT_PATH"

TARGET_DIR=$(dirname "$CERT_PATH")
mkdir -p "$TARGET_DIR"

python - <<'PY'
import base64
import os
import sys

data = os.environ.get('EXPERT_SIGNER_CERT_BASE64', '')
path = os.environ.get('EXPERT_SIGNER_CERT_PATH', '/tmp/expert-signer.p12')
if not data:
    sys.exit(0)
padding = len(data) % 4
if padding:
    data += "=" * (4 - padding)
try:
    decoded = base64.b64decode(data)
except Exception as exc:
    sys.stderr.write(f"[signer] base64 decode failed: {exc}\n")
    sys.exit(1)
with open(path, 'wb') as fp:
    fp.write(decoded)
PY

chmod 600 "$CERT_PATH"

echo "📄 EXPERT 서명용 인증서를 $CERT_PATH 에 복원했습니다."
