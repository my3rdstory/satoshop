// lecture_live_orders.js
// 라이브 강의 신청 내역 페이지 JavaScript

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 온라인 강의이므로 QR코드 생성 없음
    console.log('라이브 강의 신청 내역 페이지 로드 완료');
});

// 참가 정보 다운로드 함수
function downloadParticipantInfo(orderNumber, lectureName, participantName, participantEmail, confirmedAt, lectureDate, totalPrice, priceType, priceKrw, storeName, instructorContact, instructorEmail, completionMessage) {
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

강사 연락처:
${instructorContact ? `- 연락처: ${instructorContact}` : ''}
${instructorEmail ? `- 이메일: ${instructorEmail}` : ''}

${completionMessage ? `강사 안내사항:\n${completionMessage}\n` : ''}
일반 안내사항:
- 참가 확정 후 취소는 불가능합니다.
- 온라인 강의 링크는 강의 시작 전 이메일로 안내됩니다.
- 문의사항은 강사에게 직접 연락해주세요.

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

 