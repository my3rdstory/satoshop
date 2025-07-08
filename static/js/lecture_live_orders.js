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
        a.download = `${orderNumber}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        console.log('QR코드 다운로드 완료');
    } catch (error) {
        console.error('QR코드 다운로드 실패:', error);
    }
}

// 참가 정보 다운로드 함수
function downloadParticipantInfo(orderNumber, lectureTitle, userName, userEmail, confirmedAt, lectureDate, totalPrice, priceType, krwPrice, storeName) {
    let priceText = '';
    if (priceType === 'free') {
        priceText = '무료';
    } else if (priceType === 'krw_linked') {
        priceText = `${totalPrice} sats (${krwPrice}원 연동)`;
    } else {
        priceText = `${totalPrice} sats`;
    }
    
    const textContent = `라이브 강의 참가 확인서
========================

강의 정보:
- 강의명: ${lectureTitle}
- 주최: ${storeName}
- 일시: ${lectureDate}
- 형태: 온라인 강의

신청자 정보:
- 이름: ${userName}
- 이메일: ${userEmail}
- 주문번호: ${orderNumber}
- 신청 확정일시: ${confirmedAt}

결제 정보:
- 최종 결제금액: ${priceText}

이 파일은 라이브 강의 참가 증명서입니다.
강의 당일 QR코드와 함께 준비해 주세요.

========================
생성일시: ${new Date().toLocaleString('ko-KR')}`;

    // 파일 다운로드
    try {
        // UTF-8 BOM 추가하여 인코딩 문제 방지
        const BOM = '\uFEFF';
        const content = BOM + textContent;
        
        // 모바일 브라우저 감지
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        if (isMobile && navigator.share) {
            // 모바일에서 Web Share API 사용 가능한 경우
            const file = new File([content], `${orderNumber}.txt`, { type: 'text/plain;charset=utf-8' });
            navigator.share({
                files: [file],
                title: '라이브 강의 참가 확인서',
                text: `${lectureTitle} 참가 확인서`
            }).catch(err => {
                console.log('공유 취소 또는 실패:', err);
                // 공유 실패 시 기본 다운로드 방식 사용
                downloadWithBlob();
            });
        } else {
            // 기본 다운로드 방식
            downloadWithBlob();
        }
        
        function downloadWithBlob() {
            const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${orderNumber}.txt`;
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            
            // 리소스 정리
            setTimeout(() => {
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            }, 100);
        }
        
    } catch (error) {
        console.error('파일 다운로드 실패:', error);
        // 대안으로 새 창에서 텍스트 표시
        const newWindow = window.open();
        newWindow.document.write(`<pre style="font-family: monospace; white-space: pre-wrap; padding: 20px;">${textContent}</pre>`);
        newWindow.document.title = `${orderNumber}.txt`;
    }
    
    console.log('참가 정보 다운로드 완료');
} 