// 라이브 강의 일시중단 상태 변경 확인
function confirmLiveLecturePauseChange(checkbox) {
    const isPausing = checkbox.checked;
    const liveLectureName = window.liveLectureName || '';
    
    let message = '';
    if (isPausing) {
        message = `"${liveLectureName}" 라이브 강의를 일시중단하시겠습니까?\n\n⚠️ 일시중단하면:\n- 고객들이 임시로 이 강의에 참가할 수 없습니다.\n- 강의는 목록에 표시되지만 참가 불가능 상태가 됩니다.\n- 기존 참가자들은 영향을 받지 않습니다.`;
    } else {
        message = `"${liveLectureName}" 라이브 강의의 일시중단을 해제하시겠습니까?\n\n일시중단 해제하면:\n- 고객들이 다시 이 강의에 참가할 수 있습니다.\n- 강의가 정상적으로 운영됩니다.`;
    }
    
    if (confirm(message)) {
        // 일시중단 상태 변경 API 호출
        const url = window.toggleClosureUrl || '';
        
        if (!url) {
            alert('URL이 설정되지 않았습니다.');
            checkbox.checked = !checkbox.checked;
            return;
        }
        
        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': window.csrfToken || '',
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                location.reload(); // 페이지 새로고침으로 상태 반영
            } else {
                alert('오류가 발생했습니다: ' + data.error);
                // 원래 상태로 되돌리기
                checkbox.checked = !checkbox.checked;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('네트워크 오류가 발생했습니다.');
            // 원래 상태로 되돌리기
            checkbox.checked = !checkbox.checked;
        });
    } else {
        // 사용자가 취소한 경우 원래 상태로 되돌리기
        checkbox.checked = !checkbox.checked;
    }
}

function confirmDeleteLiveLecture() {
    const liveLectureName = window.liveLectureName || '';
    
    if (confirm('정말로 이 라이브 강의를 삭제하시겠습니까?\n\n⚠️ 주의: 이 작업은 되돌릴 수 없습니다.\n- 모든 참가자 정보가 삭제됩니다.\n- 진행 중인 결제가 취소됩니다.\n- 강의 관련 모든 데이터가 영구 삭제됩니다.')) {
        if (confirm(`마지막 확인입니다.\n\n정말로 "${liveLectureName}" 라이브 강의를 삭제하시겠습니까?`)) {
            // 라이브 강의 삭제 API 호출 (향후 구현)
            alert('라이브 강의 삭제 기능은 아직 구현되지 않았습니다.\n\n삭제가 필요한 경우 관리자에게 문의해주세요.');
        }
    }
} 