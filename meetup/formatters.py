"""
밋업 주문서 포맷터 모듈
밋업 참가 확인서 및 이메일 생성을 담당합니다.
"""
from django.utils import timezone
from typing import Dict, Any
import base64
import io


class MeetupOrderFormatter:
    """밋업 주문서 포맷터 기본 클래스"""
    
    def __init__(self, meetup_order):
        """
        Args:
            meetup_order: MeetupOrder 모델 인스턴스
        """
        self.meetup_order = meetup_order
    
    def get_base_data(self) -> Dict[str, Any]:
        """밋업 주문서에 필요한 기본 데이터 준비"""
        order = self.meetup_order
        meetup = order.meetup
        store = meetup.store
        
        # 선택된 옵션 정보 수집
        selected_options = []
        for selected_option in order.selected_options.all():
            option_data = {
                'option_name': selected_option.option.name,
                'choice_name': selected_option.choice.name,
                'additional_price': selected_option.additional_price
            }
            selected_options.append(option_data)
        
        return {
            'order': order,
            'meetup': meetup,
            'store': store,
            'selected_options': selected_options,
            'current_time': timezone.now()
        }


class MeetupTxtFormatter(MeetupOrderFormatter):
    """밋업 참가 확인서 TXT 형태 포맷터"""
    
    def generate(self) -> str:
        """TXT 형태의 밋업 참가 확인서 생성"""
        data = self.get_base_data()
        order = data['order']
        meetup = data['meetup']
        store = data['store']
        selected_options = data['selected_options']
        
        def _to_local(dt):
            if not dt:
                return None
            if timezone.is_naive(dt):
                return timezone.make_aware(dt, timezone.get_current_timezone())
            return timezone.localtime(dt)

        meetup_datetime = _to_local(meetup.date_time)
        confirmed_local = _to_local(order.confirmed_at)
        paid_local = _to_local(order.paid_at)
        generated_local = _to_local(data['current_time'])

        content = f"""
===============================================
              밋업 참가 확인서
===============================================

▣ 밋업 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
밋업명: {meetup.name}
주최: {store.store_name}
주최자: {store.owner_name}"""

        if meetup_datetime:
            content += f"\n일시: {meetup_datetime.strftime('%Y년 %m월 %d일 (%A) %H시 %M분')}"
        else:
            content += f"\n일시: 미정"

        if meetup.location_tbd:
            content += f"\n장소: 장소 추후 공지 예정"
        elif meetup.location_full_address:
            content += f"\n장소: {meetup.location_full_address}"
        else:
            content += f"\n장소: 미정"

        if meetup.description:
            content += f"\n설명: {meetup.description}"

        content += f"""

▣ 참가자 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
이름: {order.participant_name}
이메일: {order.participant_email}
주문번호: {order.order_number}
참가 확정일시: {confirmed_local.strftime('%Y년 %m월 %d일 %H시 %M분') if confirmed_local else '-'}"""

        if order.participant_phone:
            content += f"\n연락처: {order.participant_phone}"

        # 선택된 옵션이 있는 경우
        if selected_options:
            content += f"""

▣ 선택 옵션
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
            for option in selected_options:
                content += f"\n• {option['option_name']}: {option['choice_name']}"
                if option['additional_price'] > 0:
                    content += f" (+{option['additional_price']:,.0f} sats)"

        content += f"""

▣ 결제 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
기본 참가비: {order.base_price:,.0f} sats"""

        if order.options_price > 0:
            content += f"\n옵션 추가금: {order.options_price:,.0f} sats"

        if hasattr(order, 'discount_amount') and order.discount_amount > 0:
            content += f"\n할인 금액: -{order.discount_amount:,.0f} sats"

        content += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
최종 결제금액: {order.total_price:,.0f} sats
결제일시: {paid_local.strftime('%Y년 %m월 %d일 %H시 %M분') if paid_local else '-'}
결제방식: 라이트닝 네트워크 (Lightning Network)

▣ 참가 안내
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 이 참가 확인서는 밋업 당일 필요시 제시하실 수 있습니다.
• QR코드와 함께 지참해 주세요.
• 밋업 관련 문의사항은 주최자에게 연락해주세요."""

        if store.owner_phone:
            content += f"\n• 주최자 연락처: {store.owner_phone}"

        if store.chat_channel:
            content += f"\n• 소통채널: {store.chat_channel}"

        content += f"""

▣ 비트코인 관련 정보
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 결제 네트워크: 라이트닝 네트워크 (Lightning Network)
• 단위: sats (사토시, 1 BTC = 100,000,000 sats)
• 특징: 즉시 결제, 낮은 수수료, 확장성

※ 이 참가 확인서는 SatoShop에서 자동 생성된 문서입니다.
   문의사항이 있으시면 밋업 주최자에게 연락해주세요.

생성일시: {generated_local.strftime('%Y년 %m월 %d일 %H시 %M분') if generated_local else '-'}
===============================================
"""
        return content


class MeetupEmailFormatter(MeetupOrderFormatter):
    """밋업 이메일용 포맷터"""
    
    def generate_subject(self) -> str:
        """이메일 제목 생성"""
        return f'[{self.meetup_order.meetup.store.store_name}] 새로운 밋업 참가 신청 - {self.meetup_order.order_number}'
    
    def generate_body(self) -> str:
        """이메일 본문 생성 (참가 확인서 내용 + 안내 메시지)"""
        data = self.get_base_data()
        store = data['store']
        meetup = data['meetup']
        
        # TXT 포맷터를 사용하여 참가 확인서 내용 생성
        txt_formatter = MeetupTxtFormatter(self.meetup_order)
        order_content = txt_formatter.generate()
        
        message = f'''안녕하세요, {store.owner_name}님!

{store.store_name}에서 주최하는 "{meetup.name}" 밋업에 새로운 참가 신청이 접수되었습니다.

아래는 참가자 상세 정보입니다:

{order_content}

---
📧 이 이메일은 {store.store_name}의 자동 알림 시스템에서 발송되었습니다.
📱 참가자에게 밋업 관련 안내사항을 전달해주세요.
💬 참가자와의 소통을 위해 연락을 취해주시기 바랍니다.

감사합니다!
SatoShop 팀 🚀'''
        
        return message
    
    def generate_body_with_attachments(self) -> Dict[str, Any]:
        """첨부파일이 포함된 이메일 본문 생성"""
        # 기본 본문 생성
        body = self.generate_body()
        
        # QR코드 이미지 생성 (base64 인코딩)
        qr_image_data = self.generate_qr_code_image()
        
        # TXT 참가 확인서 내용
        txt_formatter = MeetupTxtFormatter(self.meetup_order)
        txt_content = txt_formatter.generate()
        
        return {
            'body': body,
            'txt_attachment': {
                'filename': f'{self.meetup_order.order_number}.txt',
                'content': txt_content,
                'content_type': 'text/plain; charset=utf-8'
            },
            'qr_image_attachment': {
                'filename': f'{self.meetup_order.order_number}.png',
                'content': qr_image_data,
                'content_type': 'image/png'
            }
        }
    
    def generate_qr_code_image(self) -> bytes:
        """QR코드 이미지를 PNG 바이트로 생성"""
        try:
            import qrcode
            from PIL import Image
            import io
            
            # QR코드 생성
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(self.meetup_order.order_number)
            qr.make(fit=True)
            
            # 이미지 생성
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 바이트로 변환
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            return img_byte_arr
            
        except ImportError as e:
            # qrcode 라이브러리가 없는 경우 빈 바이트 반환
            print(f"QR코드 라이브러리 없음: {e}")
            return b''
        except Exception as e:
            # QR코드 생성 실패 시 빈 바이트 반환
            print(f"QR코드 생성 실패: {e}")
            return b''


# 편의 함수들
def generate_meetup_txt_order(meetup_order) -> str:
    """밋업 참가 확인서 TXT 생성"""
    formatter = MeetupTxtFormatter(meetup_order)
    return formatter.generate()


def generate_meetup_email_order(meetup_order) -> Dict[str, str]:
    """이메일용 밋업 주문서 생성 (편의 함수) - 상품 이메일과 동일한 방식"""
    store = meetup_order.meetup.store
    meetup = meetup_order.meetup
    
    # 제목 생성
    subject = f'[{store.store_name}] 새로운 밋업 참가 신청 - {meetup_order.order_number}'
    
    # 본문 생성 (TXT 포맷터 사용)
    txt_formatter = MeetupTxtFormatter(meetup_order)
    meetup_content = txt_formatter.generate()
    
    body = f'''안녕하세요, {store.owner_name}님!

{store.store_name} 스토어의 밋업에 새로운 참가 신청이 접수되었습니다.

아래는 밋업 참가 신청 상세 내용입니다:

{meetup_content}

---
이 이메일은 {store.store_name} 스토어의 자동 알림 시스템에서 발송되었습니다.
밋업 준비를 위해 참가자에게 연락해주세요.

감사합니다!
SatoShop 팀'''
    
    return {
        'subject': subject,
        'body': body
    }


def generate_meetup_email_with_attachments(meetup_order) -> Dict[str, Any]:
    """첨부파일이 포함된 밋업 이메일 데이터 생성"""
    formatter = MeetupEmailFormatter(meetup_order)
    return formatter.generate_body_with_attachments() 
