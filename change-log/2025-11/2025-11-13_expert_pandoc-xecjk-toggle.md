# Expert Pandoc xeCJK 토글

- TinyTeX 번들에 `xeCJK` 패키지가 포함되지 않은 환경에서도 계약 PDF가 항상 생성되도록, 기본값으로는 Pandoc에 `CJKmainfont`/`CJKsansfont` 변수를 전달하지 않도록 변경했습니다.
- 새 환경 변수 `EXPERT_PANDOC_ENABLE_CJK`(기본 `False`)를 추가해 필요 시 `xeCJK`가 설치된 환경에서만 CJK 전용 폰트 설정을 활성화할 수 있습니다.
- README에 해당 옵션과 의존 패키지(`xeCJK`, `ctex`) 안내를 추가해 운영자가 필요한 경우에만 활성화하도록 했습니다.
