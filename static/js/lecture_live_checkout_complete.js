// lecture_live_checkout_complete.js
// 라이브 강의 참가 확정 완료 페이지 JavaScript

// 전역 변수
let qrCodeCanvas;

// 페이지 로드 후 QR 코드 생성 및 자동 다운로드
document.addEventListener('DOMContentLoaded', function() {
    // 데이터 로드 대기
    setTimeout(function() {
        const canvas = document.getElementById('qr-code');
        const orderNumber = window.liveLectureData?.orderNumber;
        
        if (canvas && orderNumber) {
            // QR 코드 생성
            const qr = new QRious({
                element: canvas,
                value: orderNumber,
                size: 128,
                background: 'white',
                foreground: 'black',
                level: 'M'
            });
            
            qrCodeCanvas = canvas;
            
            // 페이지 로드 후 2초 뒤에 자동 다운로드 시작
            setTimeout(function() {
                downloadParticipantInfo(); // TXT 파일 먼저 다운로드
                setTimeout(function() {
                    downloadQRCode(); // 3초 후 PNG 파일 다운로드
                }, 3000); // QR코드는 3초 뒤에 다운로드
            }, 2000);
        }
    }, 100); // 데이터 로드를 위한 약간의 지연
});

// 참가 정보 텍스트 파일 다운로드
function downloadParticipantInfo() {
    // 템플릿에서 데이터 추출 (전역 변수로 설정된 경우)
    const liveLectureName = window.liveLectureData?.name || '';
    const orderNumber = window.liveLectureData?.orderNumber || '';
    const participantName = window.liveLectureData?.participantName || '';
    const participantEmail = window.liveLectureData?.participantEmail || '';
    const confirmedAt = window.liveLectureData?.confirmedAt || '';
    const lectureDate = window.liveLectureData?.lectureDate || '';
    const totalPrice = window.liveLectureData?.totalPrice || '';
    const storeName = window.liveLectureData?.storeName || '';
    
    // 사용자 로컬 시간대로 변환 (다운로드용)
    const localConfirmedAt = window.convertToLocalTime ? window.convertToLocalTime(confirmedAt) : confirmedAt;
    
    // 강사 정보 추가
    let instructorInfo = '';
    if (window.liveLectureData?.instructorContact) {
        instructorInfo += `- 강사: ${window.liveLectureData.instructorContact}\n`;
    }
    if (window.liveLectureData?.instructorEmail) {
        instructorInfo += `- 강사 이메일: ${window.liveLectureData.instructorEmail}\n`;
    }
    
    const textContent = `라이브 강의 참가 확인서
========================

라이브 강의 정보:
- 강의명: ${liveLectureName}
- 주최: ${storeName}
- 일시: ${lectureDate}
${instructorInfo}
참가자 정보:
- 이름: ${participantName}
- 이메일: ${participantEmail}
- 주문번호: ${orderNumber}
- 참가 확정일시: ${localConfirmedAt}

결제 정보:
- 최종 결제금액: ${totalPrice} sats

이 파일은 라이브 강의 참가 증명서입니다.
강의 당일 QR코드와 함께 지참해 주세요.

========================
생성일시: ${new Date().toLocaleString('ko-KR')}`;

    // 파일 다운로드 (모바일 호환성 개선)
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
                text: `${liveLectureName} 참가 확인서`
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

// QR코드 PNG 파일 다운로드
function downloadQRCode() {
    if (!qrCodeCanvas) {
        console.error('QR 코드가 생성되지 않았습니다.');
        return;
    }
    
    try {
        // Canvas를 PNG로 변환
        const dataURL = qrCodeCanvas.toDataURL('image/png');
        const orderNumber = window.liveLectureData?.orderNumber || 'qr-code';
        
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