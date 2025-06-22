"""
주문서 포맷터 사용 예제

이 파일은 orders/formatters.py의 다양한 포맷터 사용법을 보여줍니다.
"""

from orders.models import Order
from orders.formatters import (
    generate_txt_order,
    generate_email_order,
    generate_html_order,
    generate_json_order,
    TxtOrderFormatter,
    EmailOrderFormatter,
    HtmlOrderFormatter,
    JsonOrderFormatter
)


def example_basic_usage():
    """기본 사용법 예제"""
    
    # 주문 객체 가져오기 (예시)
    order = Order.objects.filter(status='paid').first()
    if not order:
        print("결제 완료된 주문이 없습니다.")
        return
    
    print("=== 기본 사용법 예제 ===")
    
    # 1. TXT 형태 주문서 생성
    txt_content = generate_txt_order(order)
    print(f"TXT 주문서 길이: {len(txt_content)} 문자")
    
    # 2. 이메일용 주문서 생성
    email_data = generate_email_order(order)
    print(f"이메일 제목: {email_data['subject']}")
    print(f"이메일 본문 길이: {len(email_data['body'])} 문자")
    
    # 3. HTML 형태 주문서 생성
    html_content = generate_html_order(order)
    print(f"HTML 주문서 길이: {len(html_content)} 문자")
    
    # 4. JSON 형태 주문서 생성
    json_data = generate_json_order(order)
    print(f"JSON 주문서 키 개수: {len(json_data)} 개")
    print(f"주문 상품 개수: {json_data['meta']['total_items_count']} 개")


def example_class_usage():
    """클래스 직접 사용 예제"""
    
    order = Order.objects.filter(status='paid').first()
    if not order:
        print("결제 완료된 주문이 없습니다.")
        return
    
    print("\n=== 클래스 직접 사용 예제 ===")
    
    # 1. TXT 포맷터 직접 사용
    txt_formatter = TxtOrderFormatter(order)
    base_data = txt_formatter.get_base_data()
    print(f"기본 데이터 - 주문 상품 수: {len(base_data['order_items'])}")
    
    # 2. 이메일 포맷터 직접 사용
    email_formatter = EmailOrderFormatter(order)
    subject = email_formatter.generate_subject()
    body = email_formatter.generate_body()
    print(f"이메일 제목: {subject}")
    
    # 3. JSON 포맷터로 구조화된 데이터 얻기
    json_formatter = JsonOrderFormatter(order)
    json_data = json_formatter.generate()
    
    print(f"주문번호: {json_data['order_info']['order_number']}")
    print(f"스토어명: {json_data['store_info']['store_name']}")
    print(f"총 결제금액: {json_data['payment_summary']['total_amount']} sats")


def example_custom_formatting():
    """커스텀 포맷팅 예제"""
    
    order = Order.objects.filter(status='paid').first()
    if not order:
        print("결제 완료된 주문이 없습니다.")
        return
    
    print("\n=== 커스텀 포맷팅 예제 ===")
    
    # JSON 데이터를 사용하여 커스텀 요약 생성
    json_data = generate_json_order(order)
    
    # 간단한 주문 요약 생성
    summary = f"""
📋 주문 요약
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏪 스토어: {json_data['store_info']['store_name']}
📦 주문번호: {json_data['order_info']['order_number']}
👤 주문자: {json_data['buyer_info']['name']}
💰 총 금액: {json_data['payment_summary']['total_amount']:,} sats
📅 주문일시: {json_data['order_info']['order_date'][:19].replace('T', ' ')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    print(summary)
    
    # 상품별 요약
    print("📦 주문 상품:")
    for item in json_data['items']:
        print(f"  • {item['title']} ({item['quantity']}개) - {item['total_price']:,} sats")


def example_file_export():
    """파일 내보내기 예제"""
    
    order = Order.objects.filter(status='paid').first()
    if not order:
        print("결제 완료된 주문이 없습니다.")
        return
    
    print("\n=== 파일 내보내기 예제 ===")
    
    import json
    import os
    from django.conf import settings
    
    # 임시 디렉토리 생성
    export_dir = '/tmp/order_exports'
    os.makedirs(export_dir, exist_ok=True)
    
    order_number = order.order_number
    
    # 1. TXT 파일로 저장
    txt_content = generate_txt_order(order)
    txt_path = f"{export_dir}/order_{order_number}.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    print(f"TXT 파일 저장: {txt_path}")
    
    # 2. HTML 파일로 저장
    html_content = generate_html_order(order)
    html_path = f"{export_dir}/order_{order_number}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"HTML 파일 저장: {html_path}")
    
    # 3. JSON 파일로 저장
    json_data = generate_json_order(order)
    json_path = f"{export_dir}/order_{order_number}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    print(f"JSON 파일 저장: {json_path}")


def example_email_integration():
    """이메일 통합 예제"""
    
    order = Order.objects.filter(status='paid').first()
    if not order:
        print("결제 완료된 주문이 없습니다.")
        return
    
    print("\n=== 이메일 통합 예제 ===")
    
    # 이메일 데이터 생성
    email_data = generate_email_order(order)
    
    # 실제 이메일 발송 시뮬레이션 (실제로는 발송하지 않음)
    print("이메일 발송 시뮬레이션:")
    print(f"받는 사람: {order.store.owner_email or '설정되지 않음'}")
    print(f"제목: {email_data['subject']}")
    print(f"본문 미리보기: {email_data['body'][:100]}...")
    
    # HTML 첨부파일로 주문서 추가하는 경우
    html_content = generate_html_order(order)
    print(f"HTML 첨부파일 크기: {len(html_content)} 바이트")


if __name__ == "__main__":
    """
    Django 환경에서 실행하려면:
    
    python manage.py shell
    >>> exec(open('orders/example_usage.py').read())
    """
    
    print("주문서 포맷터 사용 예제를 실행합니다...")
    
    try:
        example_basic_usage()
        example_class_usage()
        example_custom_formatting()
        example_file_export()
        example_email_integration()
        
        print("\n✅ 모든 예제가 성공적으로 실행되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 예제 실행 중 오류 발생: {e}")
        print("Django 환경에서 실행해주세요: python manage.py shell") 