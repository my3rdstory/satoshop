// 밋업 현황 상세 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeMeetupStatusDetail();
});

function initializeMeetupStatusDetail() {
    // 통계 카드 애니메이션 초기화
    initializeStatsCards();
    
    // 테이블 행 호버 효과 초기화
    initializeTableRows();
    
    // 페이지네이션 초기화
    initializePagination();
    
    console.log('밋업 현황 상세 페이지가 초기화되었습니다.');
}

function initializeStatsCards() {
    // 통계 카드 애니메이션 효과 제거됨
    console.log('통계 카드 초기화 완료 (애니메이션 없음)');
}

function initializeTableRows() {
    // 테이블 행 애니메이션 효과 제거됨
    console.log('테이블 행 초기화 완료 (애니메이션 없음)');
}

function initializePagination() {
    // 페이지네이션 애니메이션 효과 제거됨
    console.log('페이지네이션 초기화 완료 (애니메이션 없음)');
}

// 참가자 정보 표시 함수
function showParticipantDetails(orderId) {
    // 향후 확장을 위한 함수
    console.log('참가자 상세 정보:', orderId);
}

// 상태 변경 함수 (향후 확장용)
function changeParticipantStatus(orderId, newStatus) {
    // 향후 확장을 위한 함수
    console.log('참가자 상태 변경:', orderId, newStatus);
}

// 참석 확인 함수
function updateAttendance(orderId, isAttended) {
    console.log('참석 확인 업데이트:', orderId, isAttended ? '참석' : '미참석');
    
    // 시각적 피드백 제공
    const checkbox = document.getElementById(`attendance_${orderId}`);
    const row = checkbox.closest('tr');
    
    // 로딩 상태 표시
    checkbox.disabled = true;
    
    // AJAX 요청으로 서버에 참석 상태 업데이트
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                      document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // 현재 URL에서 store_id와 meetup_id 추출
    const pathParts = window.location.pathname.split('/');
    const storeId = pathParts[2]; // /meetup/store_id/status/meetup_id/
    const meetupId = pathParts[4];
    
    fetch(`/meetup/${storeId}/status/${meetupId}/update_attendance/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            order_id: orderId,
            attended: isAttended
        })
    })
    .then(response => response.json())
    .then(data => {
        checkbox.disabled = false;
        
        if (data.success) {
            // 성공시 시각적 피드백
            if (isAttended) {
                row.style.backgroundColor = '#f0f9ff';
                row.style.borderLeft = '4px solid #3b82f6';
                showToast('참석으로 표시되었습니다.', 'success');
                
                // 참석 시간 표시 업데이트
                const label = checkbox.nextElementSibling;
                let timeDiv = label.nextElementSibling;
                if (!timeDiv || !timeDiv.classList.contains('text-xs')) {
                    timeDiv = document.createElement('div');
                    timeDiv.className = 'ml-2 text-xs text-green-600 dark:text-green-400';
                    label.parentNode.appendChild(timeDiv);
                }
                
                if (data.attended_at) {
                    const attendedDate = new Date(data.attended_at);
                    const month = String(attendedDate.getMonth() + 1).padStart(2, '0');
                    const day = String(attendedDate.getDate()).padStart(2, '0');
                    const hour = String(attendedDate.getHours()).padStart(2, '0');
                    const minute = String(attendedDate.getMinutes()).padStart(2, '0');
                    timeDiv.textContent = `${month}/${day} ${hour}:${minute}`;
                }
            } else {
                row.style.backgroundColor = '';
                row.style.borderLeft = '';
                showToast('참석이 해제되었습니다.', 'info');
                
                // 참석 시간 표시 제거
                const label = checkbox.nextElementSibling;
                const timeDiv = label.nextElementSibling;
                if (timeDiv && timeDiv.classList.contains('text-xs')) {
                    timeDiv.remove();
                }
            }
        } else {
            // 실패시 체크박스 상태 복원
            checkbox.checked = !isAttended;
            showToast(data.error || '참석 상태 업데이트에 실패했습니다.', 'error');
        }
    })
    .catch(error => {
        console.error('참석 상태 업데이트 오류:', error);
        checkbox.disabled = false;
        checkbox.checked = !isAttended;
        showToast('서버 오류가 발생했습니다.', 'error');
    });
}

// 토스트 메시지 표시 함수
function showToast(message, type = 'info') {
    // 기존 토스트가 있으면 제거
    const existingToast = document.querySelector('.toast-message');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 토스트 엘리먼트 생성
    const toast = document.createElement('div');
    toast.className = `toast-message fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium transition-all duration-300 transform translate-x-full opacity-0`;
    
    // 타입에 따른 색상 설정
    switch (type) {
        case 'success':
            toast.style.backgroundColor = '#10b981'; // 초록색
            break;
        case 'error':
            toast.style.backgroundColor = '#ef4444'; // 빨간색
            break;
        case 'warning':
            toast.style.backgroundColor = '#f59e0b'; // 주황색
            break;
        default:
            toast.style.backgroundColor = '#3b82f6'; // 파란색
    }
    
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // 애니메이션으로 표시
    setTimeout(() => {
        toast.style.transform = 'translate-x-0';
        toast.style.opacity = '1';
    }, 100);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        toast.style.transform = 'translate-x-full';
        toast.style.opacity = '0';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// 유틸리티 함수들
function formatNumber(num) {
    return new Intl.NumberFormat('ko-KR').format(num);
}

function formatSats(sats) {
    return formatNumber(sats) + ' sats';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
} 