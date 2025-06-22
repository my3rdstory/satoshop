# 주문서 포맷터 시스템

SatoShop의 주문서를 다양한 형태로 생성할 수 있는 통합 포맷터 시스템입니다.

## 📁 파일 구조

```
orders/
├── formatters.py          # 메인 포맷터 클래스들
├── example_usage.py       # 사용 예제
├── formatters_README.md   # 이 문서
└── services.py           # 기존 서비스 (포맷터 사용)
```

## 🎯 주요 특징

- **통합된 포맷터**: TXT, HTML, 이메일, JSON 등 다양한 형태 지원
- **재사용 가능**: 한 번 작성된 주문서 로직을 여러 곳에서 활용
- **확장 가능**: 새로운 포맷 추가가 쉬움
- **일관성**: 모든 포맷에서 동일한 데이터 사용

## 🚀 빠른 시작

### 기본 사용법

```python
from orders.formatters import (
    generate_txt_order,
    generate_email_order,
    generate_html_order,
    generate_json_order
)
from orders.models import Order

# 주문 객체 가져오기
order = Order.objects.get(order_number='ORD-20240101-ABC123')

# 1. TXT 형태 주문서 생성
txt_content = generate_txt_order(order)

# 2. 이메일용 주문서 생성
email_data = generate_email_order(order)
subject = email_data['subject']
body = email_data['body']

# 3. HTML 형태 주문서 생성
html_content = generate_html_order(order)

# 4. JSON 형태 주문서 생성 (API용)
json_data = generate_json_order(order)
```

### 클래스 직접 사용

```python
from orders.formatters import TxtOrderFormatter, EmailOrderFormatter

# TXT 포맷터 직접 사용
formatter = TxtOrderFormatter(order)
base_data = formatter.get_base_data()  # 기본 데이터 얻기
txt_content = formatter.generate()     # TXT 생성

# 이메일 포맷터 직접 사용
email_formatter = EmailOrderFormatter(order)
subject = email_formatter.generate_subject()
body = email_formatter.generate_body()
```

## 📋 지원하는 포맷

### 1. TXT 포맷 (`TxtOrderFormatter`)

- **용도**: 파일 다운로드, 텍스트 기반 저장
- **특징**: 깔끔한 텍스트 레이아웃, 유니코드 박스 문자 사용
- **출력**: 순수 텍스트 문자열

```python
txt_content = generate_txt_order(order)
# 결과: "===============================================\n                주 문 서\n..."
```

### 2. 이메일 포맷 (`EmailOrderFormatter`)

- **용도**: 스토어 주인장에게 주문 알림 이메일 발송
- **특징**: 제목과 본문을 분리하여 제공, 안내 메시지 포함
- **출력**: `{'subject': '...', 'body': '...'}`

```python
email_data = generate_email_order(order)
# 결과: {'subject': '[스토어명] 새로운 주문 접수 - 주문번호', 'body': '안녕하세요...'}
```

### 3. HTML 포맷 (`HtmlOrderFormatter`)

- **용도**: 웹 페이지 표시, 이메일 HTML 버전, 인쇄용
- **특징**: 완전한 HTML 문서, CSS 스타일 포함
- **출력**: HTML 문자열

```python
html_content = generate_html_order(order)
# 결과: "<!DOCTYPE html>\n<html lang=\"ko\">..."
```

### 4. JSON 포맷 (`JsonOrderFormatter`)

- **용도**: API 응답, 데이터 교환, 구조화된 저장
- **특징**: 계층적 구조, 타입 안전성
- **출력**: Python 딕셔너리

```python
json_data = generate_json_order(order)
# 결과: {'order_info': {...}, 'store_info': {...}, ...}
```

## 🔧 현재 사용 중인 곳

### 1. TXT 다운로드
- `orders/views.py` - `download_order_txt_public()`
- `accounts/views.py` - `download_order_txt()`

### 2. 이메일 발송
- `orders/services.py` - `send_order_notification_email()`

### 3. 하위 호환성
- `orders/services.py` - `generate_order_txt_content()` (래퍼 함수)

## 🛠 새로운 포맷 추가하기

새로운 포맷을 추가하려면 `OrderFormatter`를 상속받아 구현합니다:

```python
class PdfOrderFormatter(OrderFormatter):
    """PDF 형태의 주문서 포맷터"""
    
    def generate(self) -> bytes:
        """PDF 형태의 주문서 생성"""
        data = self.get_base_data()
        
        # PDF 생성 로직
        # reportlab, weasyprint 등 사용
        
        return pdf_bytes

# 편의 함수 추가
def generate_pdf_order(order) -> bytes:
    formatter = PdfOrderFormatter(order)
    return formatter.generate()
```

## 📊 데이터 구조

모든 포맷터는 `get_base_data()` 메서드를 통해 동일한 기본 데이터를 사용합니다:

```python
{
    'order': Order 객체,
    'order_items': [
        {
            'index': 1,
            'title': '상품명',
            'quantity': 2,
            'product_price': 1000,
            'options_price': 100,
            'total_price': 2200,
            'selected_options': {'색상': '빨강', '사이즈': 'L'}
        },
        ...
    ],
    'store': Store 객체,
    'total_items_count': 3,
    'current_time': datetime 객체
}
```

## 🧪 테스트 및 예제

### 예제 실행

```bash
# Django shell에서 실행
python manage.py shell

# 예제 스크립트 실행
>>> exec(open('orders/example_usage.py').read())
```

### 파일 내보내기 테스트

```python
from orders.formatters import *
from orders.models import Order

order = Order.objects.filter(status='paid').first()

# 각 포맷으로 파일 생성
with open('order.txt', 'w') as f:
    f.write(generate_txt_order(order))

with open('order.html', 'w') as f:
    f.write(generate_html_order(order))

import json
with open('order.json', 'w') as f:
    json.dump(generate_json_order(order), f, ensure_ascii=False, indent=2)
```

## 🔍 디버깅 및 로깅

포맷터 사용 시 문제가 발생하면:

1. **주문 객체 확인**: `order.items.all()` 등이 올바른지 체크
2. **기본 데이터 확인**: `formatter.get_base_data()` 호출하여 데이터 검증
3. **단계별 테스트**: 각 포맷터를 개별적으로 테스트

```python
# 디버깅 예제
formatter = TxtOrderFormatter(order)
base_data = formatter.get_base_data()

print(f"주문 상품 수: {len(base_data['order_items'])}")
print(f"스토어명: {base_data['store'].store_name}")
print(f"총 상품 개수: {base_data['total_items_count']}")
```

## 🚀 향후 확장 계획

- **PDF 포맷터**: 인쇄용 PDF 생성
- **XML 포맷터**: 시스템 간 데이터 교환
- **CSV 포맷터**: 스프레드시트 호환
- **Markdown 포맷터**: 문서화 및 GitHub 이슈
- **템플릿 시스템**: Django 템플릿 기반 포맷터

## 💡 팁과 베스트 프랙티스

1. **편의 함수 사용**: 대부분의 경우 `generate_*_order()` 함수 사용 권장
2. **에러 핸들링**: 주문 객체가 None이거나 빈 경우 체크
3. **성능 고려**: 대량 처리 시 DB 쿼리 최적화 (select_related, prefetch_related)
4. **캐싱**: 동일한 주문서를 반복 생성하는 경우 캐싱 고려

```python
# 좋은 예제
try:
    if order and order.items.exists():
        txt_content = generate_txt_order(order)
        # 사용...
    else:
        print("주문이 없거나 상품이 없습니다.")
except Exception as e:
    print(f"주문서 생성 실패: {e}")
```

---

**문의사항이나 개선 제안이 있으시면 개발팀에 연락해주세요!** 🚀 