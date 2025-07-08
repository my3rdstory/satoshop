// lecture_live_checkout_complete.js
// 라이브 강의 결제 완료 페이지 JavaScript

// 페이지 로드 후 자동 다운로드
document.addEventListener('DOMContentLoaded', function() {
    // 자동 다운로드 (페이지 로드 후 3초 후)
    setTimeout(() => {
        downloadParticipantInfo();
    }, 3000);
});

function downloadParticipantInfo() {
    if (!window.liveLectureData) return;
    
    const data = window.liveLectureData;
    const content = `라이브 강의 참가 확인서
=====================================

▶ 라이브 강의 정보
- 강의명: ${data.name}
- 일시: ${data.lectureDate}
- 스토어: ${data.storeName}

▶ 참가자 정보
- 이름: ${data.participantName}
- 이메일: ${data.participantEmail}

▶ 결제 정보
- 참가비: ${data.totalPrice === '0' ? '무료' : data.totalPrice + ' sats'}
- 참가 확정일시: ${data.confirmedAt}

▶ 강사 연락처
${data.instructorContact ? '- 연락처: ' + data.instructorContact : ''}
${data.instructorEmail ? '- 이메일: ' + data.instructorEmail : ''}

${data.completionMessage ? `▶ 강사 안내사항\n${data.completionMessage}\n` : ''}
▶ 일반 안내사항
- 참가 확정 후 취소는 불가능합니다.
- 온라인 강의 링크는 강의 시작 전 이메일로 안내됩니다.
- 문의사항은 강사에게 직접 연락해주세요.

생성일시: ${new Date().toLocaleString('ko-KR')}
플랫폼: SatoShop (https://satoshop.kr)
`;

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `라이브강의_참가확인서_${data.name.replace(/[^a-zA-Z0-9가-힣]/g, '_')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
} 