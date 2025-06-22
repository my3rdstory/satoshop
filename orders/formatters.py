"""
주문서 포맷터 모듈
다양한 형태의 주문서 생성을 담당합니다.
"""
from django.utils import timezone
from typing import Dict, Any, Optional


class OrderFormatter:
    """주문서 포맷터 기본 클래스"""
    
    def __init__(self, order):
        """
        Args:
            order: Order 모델 인스턴스
        """
        self.order = order
    
    def get_base_data(self) -> Dict[str, Any]:
        """주문서에 필요한 기본 데이터 준비"""
        order = self.order
        
        # 주문 상품 정보 수집
        order_items = []
        for i, item in enumerate(order.items.all(), 1):
            item_data = {
                'index': i,
                'title': item.product_title,
                'quantity': item.quantity,
                'product_price': item.product_price,
                'options_price': item.options_price,
                'total_price': item.total_price,
                'selected_options': item.selected_options or {}
            }
            order_items.append(item_data)
        
        return {
            'order': order,
            'order_items': order_items,
            'store': order.store,
            'total_items_count': order.items.count(),
            'current_time': timezone.now()
        }


class TxtOrderFormatter(OrderFormatter):
    """TXT 형태의 주문서 포맷터"""
    
    def generate(self) -> str:
        """TXT 형태의 주문서 생성"""
        data = self.get_base_data()
        order = data['order']
        store = data['store']
        order_items = data['order_items']
        
        content = f"""
===============================================
                주 문 서
===============================================

▣ 주문 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
주문번호: {order.order_number}
주문일시: {order.created_at.strftime('%Y년 %m월 %d일 %H시 %M분')}
결제일시: {order.paid_at.strftime('%Y년 %m월 %d일 %H시 %M분') if order.paid_at else '-'}
주문상태: 결제 완료
결제방식: 라이트닝 네트워크 (Lightning Network)

▣ 스토어 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
스토어명: {store.store_name}
판매자: {store.owner_name}"""

        if store.owner_phone:
            content += f"\n연락처: {store.owner_phone}"
        
        if store.chat_channel:
            content += f"\n소통채널: {store.chat_channel}"

        content += f"""

▣ 주문자 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
이름: {order.buyer_name}
연락처: {order.buyer_phone}
이메일: {order.buyer_email}

▣ 배송지 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
우편번호: {order.shipping_postal_code}
주소: {order.shipping_address}"""

        if order.shipping_detail_address:
            content += f"\n상세주소: {order.shipping_detail_address}"

        if order.order_memo:
            content += f"\n배송요청사항: {order.order_memo}"

        content += f"""

▣ 주문 상품 ({data['total_items_count']}개)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        for item_data in order_items:
            content += f"""

{item_data['index']}. {item_data['title']}
   - 수량: {item_data['quantity']}개
   - 단가: {item_data['product_price']:,.0f} sats"""
            
            if item_data['options_price'] > 0:
                content += f"\n   - 옵션추가: {item_data['options_price']:,.0f} sats"
            
            if item_data['selected_options']:
                content += "\n   - 선택옵션:"
                for option_name, choice_name in item_data['selected_options'].items():
                    content += f" {option_name}({choice_name})"
            
            content += f"\n   - 소계: {item_data['total_price']:,.0f} sats"

        content += f"""

▣ 결제 내역
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
상품 금액: {order.subtotal:,.0f} sats
배송비: {order.shipping_fee:,.0f} sats
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
총 결제 금액: {order.total_amount:,.0f} sats

▣ 비트코인 관련 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 결제 네트워크: 라이트닝 네트워크 (Lightning Network)
• 단위: sats (사토시, 1 BTC = 100,000,000 sats)
• 특징: 즉시 결제, 낮은 수수료, 확장성

※ 이 주문서는 SatoShop에서 자동 생성된 문서입니다.
   문의사항이 있으시면 스토어 판매자에게 연락해주세요.

생성일시: {data['current_time'].strftime('%Y년 %m월 %d일 %H시 %M분')}
===============================================
"""
        return content


class EmailOrderFormatter(OrderFormatter):
    """이메일용 주문서 포맷터"""
    
    def generate_subject(self) -> str:
        """이메일 제목 생성"""
        return f'[{self.order.store.store_name}] 새로운 주문 접수 - {self.order.order_number}'
    
    def generate_body(self) -> str:
        """이메일 본문 생성 (주문서 내용 + 안내 메시지)"""
        data = self.get_base_data()
        store = data['store']
        
        # TXT 포맷터를 사용하여 주문서 내용 생성
        txt_formatter = TxtOrderFormatter(self.order)
        order_content = txt_formatter.generate()
        
        message = f'''안녕하세요, {store.owner_name}님!

{store.store_name} 스토어에 새로운 주문이 접수되었습니다.

아래는 주문 상세 내용입니다:

{order_content}

---
이 이메일은 {store.store_name} 스토어의 자동 알림 시스템에서 발송되었습니다.
주문 처리를 위해 고객에게 연락해주세요.

감사합니다!
SatoShop 팀'''
        
        return message


class HtmlOrderFormatter(OrderFormatter):
    """HTML 형태의 주문서 포맷터 (향후 확장용)"""
    
    def generate(self) -> str:
        """HTML 형태의 주문서 생성"""
        data = self.get_base_data()
        order = data['order']
        store = data['store']
        order_items = data['order_items']
        
        # 기본적인 HTML 구조 (향후 템플릿으로 확장 가능)
        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주문서 - {order.order_number}</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; margin: 20px; }}
        .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        .section {{ margin: 20px 0; }}
        .section h3 {{ background: #f0f0f0; padding: 10px; margin: 0; }}
        .item {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
        .total {{ font-weight: bold; background: #fffacd; padding: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>주 문 서</h1>
        <p>주문번호: {order.order_number}</p>
    </div>
    
    <div class="section">
        <h3>주문 정보</h3>
        <p>주문일시: {order.created_at.strftime('%Y년 %m월 %d일 %H시 %M분')}</p>
        <p>결제일시: {order.paid_at.strftime('%Y년 %m월 %d일 %H시 %M분') if order.paid_at else '-'}</p>
        <p>주문상태: 결제 완료</p>
        <p>결제방식: 라이트닝 네트워크</p>
    </div>
    
    <div class="section">
        <h3>스토어 정보</h3>
        <p>스토어명: {store.store_name}</p>
        <p>판매자: {store.owner_name}</p>
        {f'<p>연락처: {store.owner_phone}</p>' if store.owner_phone else ''}
        {f'<p>소통채널: {store.chat_channel}</p>' if store.chat_channel else ''}
    </div>
    
    <div class="section">
        <h3>주문자 정보</h3>
        <p>이름: {order.buyer_name}</p>
        <p>연락처: {order.buyer_phone}</p>
        <p>이메일: {order.buyer_email}</p>
    </div>
    
    <div class="section">
        <h3>배송지 정보</h3>
        <p>우편번호: {order.shipping_postal_code}</p>
        <p>주소: {order.shipping_address}</p>
        {f'<p>상세주소: {order.shipping_detail_address}</p>' if order.shipping_detail_address else ''}
        {f'<p>배송요청사항: {order.order_memo}</p>' if order.order_memo else ''}
    </div>
    
    <div class="section">
        <h3>주문 상품 ({data['total_items_count']}개)</h3>"""
        
        for item_data in order_items:
            html += f"""
        <div class="item">
            <h4>{item_data['index']}. {item_data['title']}</h4>
            <p>수량: {item_data['quantity']}개</p>
            <p>단가: {item_data['product_price']:,.0f} sats</p>"""
            
            if item_data['options_price'] > 0:
                html += f"<p>옵션추가: {item_data['options_price']:,.0f} sats</p>"
            
            if item_data['selected_options']:
                options_str = ', '.join([f"{k}({v})" for k, v in item_data['selected_options'].items()])
                html += f"<p>선택옵션: {options_str}</p>"
            
            html += f"<p><strong>소계: {item_data['total_price']:,.0f} sats</strong></p>"
            html += "</div>"
        
        html += f"""
    </div>
    
    <div class="section total">
        <h3>결제 내역</h3>
        <p>상품 금액: {order.subtotal:,.0f} sats</p>
        <p>배송비: {order.shipping_fee:,.0f} sats</p>
        <hr>
        <p><strong>총 결제 금액: {order.total_amount:,.0f} sats</strong></p>
    </div>
    
    <div class="section">
        <h3>비트코인 관련 정보</h3>
        <ul>
            <li>결제 네트워크: 라이트닝 네트워크 (Lightning Network)</li>
            <li>단위: sats (사토시, 1 BTC = 100,000,000 sats)</li>
            <li>특징: 즉시 결제, 낮은 수수료, 확장성</li>
        </ul>
        <p><small>※ 이 주문서는 SatoShop에서 자동 생성된 문서입니다.<br>
        문의사항이 있으시면 스토어 판매자에게 연락해주세요.</small></p>
        <p><small>생성일시: {data['current_time'].strftime('%Y년 %m월 %d일 %H시 %M분')}</small></p>
    </div>
</body>
</html>"""
        
        return html


# 편의 함수들
def generate_txt_order(order) -> str:
    """TXT 형태의 주문서 생성 (편의 함수)"""
    formatter = TxtOrderFormatter(order)
    return formatter.generate()


def generate_email_order(order) -> Dict[str, str]:
    """이메일용 주문서 생성 (편의 함수)"""
    formatter = EmailOrderFormatter(order)
    return {
        'subject': formatter.generate_subject(),
        'body': formatter.generate_body()
    }


def generate_html_order(order) -> str:
    """HTML 형태의 주문서 생성 (편의 함수)"""
    formatter = HtmlOrderFormatter(order)
    return formatter.generate()


class JsonOrderFormatter(OrderFormatter):
    """JSON 형태의 주문서 포맷터 (API 응답용)"""
    
    def generate(self) -> Dict[str, Any]:
        """JSON 형태의 주문서 생성"""
        data = self.get_base_data()
        order = data['order']
        store = data['store']
        order_items = data['order_items']
        
        # 주문 상품 정보를 JSON 형태로 변환
        items_json = []
        for item_data in order_items:
            items_json.append({
                'index': item_data['index'],
                'title': item_data['title'],
                'quantity': item_data['quantity'],
                'product_price': item_data['product_price'],
                'options_price': item_data['options_price'],
                'total_price': item_data['total_price'],
                'selected_options': item_data['selected_options']
            })
        
        return {
            'order_info': {
                'order_number': order.order_number,
                'order_date': order.created_at.isoformat(),
                'payment_date': order.paid_at.isoformat() if order.paid_at else None,
                'status': order.get_status_display(),
                'payment_method': '라이트닝 네트워크 (Lightning Network)'
            },
            'store_info': {
                'store_name': store.store_name,
                'owner_name': store.owner_name,
                'owner_phone': store.owner_phone or '',
                'chat_channel': store.chat_channel or ''
            },
            'buyer_info': {
                'name': order.buyer_name,
                'phone': order.buyer_phone,
                'email': order.buyer_email
            },
            'shipping_info': {
                'postal_code': order.shipping_postal_code,
                'address': order.shipping_address,
                'detail_address': order.shipping_detail_address or '',
                'memo': order.order_memo or ''
            },
            'items': items_json,
            'payment_summary': {
                'subtotal': order.subtotal,
                'shipping_fee': order.shipping_fee,
                'total_amount': order.total_amount,
                'currency': 'sats'
            },
            'bitcoin_info': {
                'network': 'Lightning Network',
                'unit': 'sats (사토시)',
                'conversion': '1 BTC = 100,000,000 sats',
                'features': ['즉시 결제', '낮은 수수료', '확장성']
            },
            'meta': {
                'generated_at': data['current_time'].isoformat(),
                'total_items_count': data['total_items_count'],
                'platform': 'SatoShop'
            }
        }


def generate_json_order(order) -> Dict[str, Any]:
    """JSON 형태의 주문서 생성 (편의 함수)"""
    formatter = JsonOrderFormatter(order)
    return formatter.generate() 