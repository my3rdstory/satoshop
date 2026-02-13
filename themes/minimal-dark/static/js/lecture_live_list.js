/* lecture_live_list.js */
/* 라이브 강의 목록 페이지 전용 스크립트 */

// 일시중단 토글 함수
function toggleLiveLectureTemporaryClosure(liveLectureId, liveLectureTitle) {
    const action = document.querySelector(`button[onclick*="${liveLectureId}"] span`).textContent.includes('해제') ? '해제' : '설정';
    
    if (confirm(`"${liveLectureTitle}" 라이브 강의를 일시중단 ${action}하시겠습니까?`)) {
        // Django 템플릿 변수를 전역으로 설정된 값에서 가져옴
        const storeId = window.storeId || document.querySelector('[data-store-id]')?.dataset.storeId;
        const url = `/lecture/${storeId}/live/${liveLectureId}/toggle-temporary-closure/`;
        
        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': window.csrfToken || document.querySelector('[name=csrfmiddlewaretoken]')?.value,
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
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('네트워크 오류가 발생했습니다.');
        });
    }
} 