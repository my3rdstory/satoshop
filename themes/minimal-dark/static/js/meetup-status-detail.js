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

// 클립보드 복사 함수
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // 성공 시 임시 알림 표시
        showCopyNotification();
    }).catch(function(err) {
        console.error('클립보드 복사 실패:', err);
        // fallback: 텍스트 선택
        fallbackCopyTextToClipboard(text);
    });
}

// 복사 성공 알림 표시
function showCopyNotification() {
    // 기존 알림이 있다면 제거
    const existingNotification = document.querySelector('.copy-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 새 알림 생성
    const notification = document.createElement('div');
    notification.className = 'copy-notification fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300';
    notification.innerHTML = '<i class="fas fa-check mr-2"></i>결제 해시가 복사되었습니다';
    document.body.appendChild(notification);
    
    // 3초 후 제거
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// 폴백 복사 함수 (구형 브라우저용)
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.top = '0';
    textArea.style.left = '0';
    textArea.style.width = '2em';
    textArea.style.height = '2em';
    textArea.style.padding = '0';
    textArea.style.border = 'none';
    textArea.style.outline = 'none';
    textArea.style.boxShadow = 'none';
    textArea.style.background = 'transparent';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showCopyNotification();
    } catch (err) {
        console.error('폴백 복사 실패:', err);
    }
    
    document.body.removeChild(textArea);
}

// 결제 해시 모달 관련 함수들
let currentPaymentHash = '';

// 결제 해시 모달 열기
function showPaymentHashModal(paymentHash) {
    currentPaymentHash = paymentHash;
    document.getElementById('modalPaymentHash').textContent = paymentHash;
    document.getElementById('paymentHashModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // 배경 스크롤 방지
}

// 결제 해시 모달 닫기
function closePaymentHashModal() {
    document.getElementById('paymentHashModal').classList.add('hidden');
    document.body.style.overflow = 'auto'; // 배경 스크롤 복원
    currentPaymentHash = '';
}

// 모달의 결제 해시 복사
function copyModalPaymentHash() {
    if (currentPaymentHash) {
        copyToClipboard(currentPaymentHash);
    }
}

// 모달 외부 클릭 시 닫기
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('paymentHashModal');
    const modalContent = modal.querySelector('div > div');
    
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closePaymentHashModal();
        }
    });
    
    // ESC 키로 모달 닫기
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            closePaymentHashModal();
        }
    });
});

// 참가 취소 함수
function cancelParticipation(orderId, participantName) {
    if (confirm(`정말로 "${participantName}"님의 참가를 취소하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
        // CSRF 토큰 가져오기
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        // 버튼 비활성화
        const cancelButton = event.target.closest('button');
        const originalText = cancelButton.innerHTML;
        cancelButton.disabled = true;
        cancelButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>처리중...';
        
        fetch(`/meetup/${window.location.pathname.split('/')[2]}/${window.location.pathname.split('/')[4]}/cancel_participation/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                order_id: orderId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showCancelNotification('참가가 성공적으로 취소되었습니다.');
                // 해당 행의 상태를 즉시 업데이트
                updateOrderRowStatus(orderId, 'cancelled');
                // 통계 업데이트
                updateStatistics();
            } else {
                alert('참가 취소 중 오류가 발생했습니다: ' + (data.error || '알 수 없는 오류'));
                // 버튼 복원
                cancelButton.disabled = false;
                cancelButton.innerHTML = originalText;
            }
        })
        .catch(error => {
            console.error('참가 취소 오류:', error);
            alert('참가 취소 중 오류가 발생했습니다.');
            // 버튼 복원
            cancelButton.disabled = false;
            cancelButton.innerHTML = originalText;
        });
    }
}

// 취소 성공 알림 표시
function showCancelNotification(message) {
    // 기존 알림이 있다면 제거
    const existingNotification = document.querySelector('.cancel-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 새 알림 생성
    const notification = document.createElement('div');
    notification.className = 'cancel-notification fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300';
    notification.innerHTML = `<i class="fas fa-check mr-2"></i>${message}`;
    document.body.appendChild(notification);
    
    // 3초 후 제거
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// 주문 행 상태 업데이트 함수
function updateOrderRowStatus(orderId, newStatus) {
    // 해당 주문의 행을 찾기
    const orderRow = document.querySelector(`tr:has(input[id="attendance_${orderId}"])`);
    if (!orderRow) return;
    
    // 상태 셀 찾기
    const statusCell = orderRow.querySelector('td:nth-child(4) > div');
    if (!statusCell) return;
    
    // 상태에 따라 업데이트
    if (newStatus === 'cancelled') {
        statusCell.innerHTML = `
            <div>
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300">
                    <i class="fas fa-ban mr-1"></i>
                    취소됨
                </span>
            </div>
        `;
    }
}

// 통계 업데이트 함수
function updateStatistics() {
    // 현재 페이지의 모든 주문 행을 확인하여 통계 재계산
    const orderRows = document.querySelectorAll('tbody tr');
    let confirmedCount = 0;
    let attendedCount = 0;
    let totalRevenue = 0;
    
    orderRows.forEach(row => {
        const statusCell = row.querySelector('td:nth-child(4)');
        const priceCell = row.querySelector('td:nth-child(2)');
        const attendanceCheckbox = row.querySelector('input[type="checkbox"]');
        
        if (statusCell && priceCell) {
            const statusText = statusCell.textContent.trim();
            
            // 확정된 참가자인지 확인
            if (statusText.includes('참가 확정') || statusText.includes('밋업 완료')) {
                confirmedCount++;
                
                // 가격 추출 (sats 제거)
                const priceText = priceCell.textContent.trim().replace(/[^\d]/g, '');
                const price = parseInt(priceText) || 0;
                totalRevenue += price;
                
                // 참석 여부 확인
                if (attendanceCheckbox && attendanceCheckbox.checked) {
                    attendedCount++;
                }
            }
        }
    });
    
    // 참석률 계산
    const attendanceRate = confirmedCount > 0 ? (attendedCount / confirmedCount) * 100 : 0;
    const averagePrice = confirmedCount > 0 ? totalRevenue / confirmedCount : 0;
    
    // DOM 업데이트
    updateStatCard('총 참가자', confirmedCount);
    updateStatCard('총 매출 (sats)', totalRevenue.toLocaleString());
    updateStatCard('평균 참가비', Math.round(averagePrice).toLocaleString());
    updateStatCard('실제 참석자', attendedCount);
    updateStatCard('참석률', attendanceRate.toFixed(1) + '%');
}

// 통계 카드 업데이트 함수
function updateStatCard(label, value) {
    const statCards = document.querySelectorAll('.stat-card');
    statCards.forEach(card => {
        const labelElement = card.querySelector('div:last-child');
        if (labelElement && labelElement.textContent.trim() === label) {
            const valueElement = card.querySelector('div:first-child');
            if (valueElement) {
                // 애니메이션 효과
                valueElement.style.transition = 'transform 0.2s ease-in-out';
                valueElement.style.transform = 'scale(1.1)';
                valueElement.textContent = value;
                setTimeout(() => {
                    valueElement.style.transform = 'scale(1)';
                }, 200);
            }
        }
    });
}

// 참석 시간 표시 업데이트 함수
function updateAttendanceDisplay(orderId, isAttended, attendedAt = null) {
    const checkbox = document.getElementById(`attendance_${orderId}`);
    const attendanceCell = checkbox.closest('td');
    
    // 기존 시간 표시 제거
    const existingTimeElements = attendanceCell.querySelectorAll('.attendance-time');
    existingTimeElements.forEach(el => el.remove());
    
    if (isAttended && attendedAt) {
        // 새로운 시간 표시 추가
        const attendedDate = new Date(attendedAt);
        const month = String(attendedDate.getMonth() + 1).padStart(2, '0');
        const day = String(attendedDate.getDate()).padStart(2, '0');
        const hour = String(attendedDate.getHours()).padStart(2, '0');
        const minute = String(attendedDate.getMinutes()).padStart(2, '0');
        
        // 체크일시 div
        const checkTimeLabel = document.createElement('div');
        checkTimeLabel.className = 'attendance-time text-xs text-green-600 dark:text-green-400 mt-1';
        checkTimeLabel.textContent = '체크일시';
        
        // 실제 시간 div
        const checkTimeValue = document.createElement('div');
        checkTimeValue.className = 'attendance-time text-xs text-green-600 dark:text-green-400';
        checkTimeValue.textContent = `${month}/${day} ${hour}:${minute}`;
        
        attendanceCell.appendChild(checkTimeLabel);
        attendanceCell.appendChild(checkTimeValue);
    }
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
    
    console.log('CSRF 토큰:', csrfToken);
    
    // 현재 URL에서 store_id와 meetup_id 추출
    const pathParts = window.location.pathname.split('/');
    const storeId = pathParts[2]; // /meetup/store_id/status/meetup_id/
    const meetupId = pathParts[4];
    
    console.log('URL 경로:', window.location.pathname);
    console.log('Store ID:', storeId, 'Meetup ID:', meetupId);
    
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
                updateAttendanceDisplay(orderId, true, data.attended_at);
            } else {
                row.style.backgroundColor = '';
                row.style.borderLeft = '';
                showToast('참석이 해제되었습니다.', 'info');
                
                // 참석 시간 표시 제거
                updateAttendanceDisplay(orderId, false);
            }
            
            // 통계 업데이트
            updateStatistics();
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