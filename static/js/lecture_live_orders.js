// lecture_live_orders.js
// 라이브 강의 신청 내역 페이지 JavaScript

// QR 코드 생성 및 관리
document.addEventListener('DOMContentLoaded', function() {
    const qrCanvases = document.querySelectorAll('.qr-code-canvas');
    
    qrCanvases.forEach(canvas => {
        const orderNumber = canvas.getAttribute('data-order-number');
        
        if (orderNumber) {
            // QR 코드 생성
            new QRious({
                element: canvas,
                value: orderNumber,
                size: 128,
                background: 'white',
                foreground: 'black',
                level: 'M'
            });
        }
    });
    
});

// QR코드 다운로드 함수
function downloadQRCode(orderNumber) {
    const canvas = document.querySelector(`canvas[data-order-number="${orderNumber}"]`);
    if (!canvas) {
        console.error('QR 코드를 찾을 수 없습니다.');
        return;
    }
    
    try {
        // Canvas를 PNG로 변환
        const dataURL = canvas.toDataURL('image/png');
        
        // 다운로드 링크 생성
        const a = document.createElement('a');
        a.href = dataURL;
        a.download = `라이브강의_QR코드_${orderNumber}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        console.log('QR코드 다운로드 완료');
    } catch (error) {
        console.error('QR코드 다운로드 실패:', error);
    }
}

// 참가 정보 다운로드 함수
function downloadParticipantInfo(orderNumber, lectureName, participantName, participantEmail, confirmedAt, lectureDate, totalPrice, priceType, priceKrw, storeName) {
    const textContent = `라이브 강의 참가 확인서
========================

라이브 강의 정보:
- 강의명: ${lectureName}
- 주최: ${storeName}
- 일시: ${lectureDate}
- 형태: 온라인 라이브 강의

참가자 정보:
- 이름: ${participantName}
- 이메일: ${participantEmail}
- 주문번호: ${orderNumber}
- 참가 확정일시: ${confirmedAt}

결제 정보:
- 가격 타입: ${priceType === 'free' ? '무료' : priceType === 'krw' ? '원화연동' : '사토시'}
${priceType === 'krw' && priceKrw !== '0' ? `- 원화 기준가: ${parseInt(priceKrw).toLocaleString()}원\n` : ''}
- 최종 결제금액: ${totalPrice === '0' ? '무료' : `${parseInt(totalPrice).toLocaleString()} sats`}

이 파일은 라이브 강의 참가 증명서입니다.
강의 당일 QR코드와 함께 지참해 주세요.

========================
생성일시: ${new Date().toLocaleString('ko-KR')}`;

    // 텍스트 파일로 다운로드
    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `라이브강의_참가정보_${orderNumber}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    console.log('참가 정보 다운로드 완료');
}

 