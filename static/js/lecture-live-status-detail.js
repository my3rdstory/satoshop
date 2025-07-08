// 라이브 강의 현황 상세 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeLiveLectureStatusDetail();
});

function initializeLiveLectureStatusDetail() {
    // 통계 카드 애니메이션 초기화
    initializeStatsCards();
    
    // 테이블 행 호버 효과 초기화
    initializeTableRows();
    
    // 페이지네이션 초기화
    initializePagination();
    
    // 모달 이벤트 초기화
    initializeModal();
    
    console.log('라이브 강의 현황 상세 페이지가 초기화되었습니다.');
}

function initializeStatsCards() {
    // 통계 카드 초기화 (호버 애니메이션 제거됨)
    const statsCards = document.querySelectorAll('.stat-card');
    
    console.log('통계 카드 초기화 완료');
}

function initializeTableRows() {
    const tableRows = document.querySelectorAll('.orders-table tbody tr');
    
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f9fafb';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
    
    console.log('테이블 행 초기화 완료');
}

function initializePagination() {
    const paginationLinks = document.querySelectorAll('nav a');
    
    paginationLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // 페이지 전환 시 부드러운 애니메이션
            const table = document.querySelector('.orders-table');
            if (table) {
                table.style.opacity = '0.7';
                setTimeout(() => {
                    table.style.opacity = '1';
                }, 200);
            }
        });
    });
    
    console.log('페이지네이션 초기화 완료');
}

function initializeModal() {
    const modal = document.getElementById('paymentHashModal');
    if (modal) {
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
    }
    
    console.log('모달 초기화 완료');
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
        
        // 현재 URL에서 store_id와 live_lecture_id 추출
        const pathParts = window.location.pathname.split('/');
        const storeId = pathParts[2];
        const liveLectureId = pathParts[5];
        
        fetch(`/lecture/${storeId}/live/${liveLectureId}/cancel_participation/`, {
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

// 취소 알림 표시
function showCancelNotification(message) {
    // 기존 알림이 있다면 제거
    const existingNotification = document.querySelector('.cancel-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 새 알림 생성
    const notification = document.createElement('div');
    notification.className = 'cancel-notification fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300';
    notification.innerHTML = '<i class="fas fa-check mr-2"></i>' + message;
    document.body.appendChild(notification);
    
    // 3초 후 제거
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// 주문 행 상태 업데이트
function updateOrderRowStatus(orderId, newStatus) {
    const row = document.querySelector(`tr[data-order-id="${orderId}"]`);
    if (!row) return;
    
    const statusCell = row.querySelector('td:nth-child(4)');
    if (statusCell) {
        let statusHtml = '';
        
        switch(newStatus) {
            case 'cancelled':
                statusHtml = `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300">
                        <i class="fas fa-ban mr-1"></i>
                        취소됨
                    </span>
                `;
                break;
            case 'completed':
                statusHtml = `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                        <i class="fas fa-flag-checkered mr-1"></i>
                        강의 완료
                    </span>
                `;
                break;
            default:
                statusHtml = `
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
                        <i class="fas fa-check-circle mr-1"></i>
                        참가 확정
                    </span>
                `;
        }
        
        statusCell.innerHTML = statusHtml;
    }
}

// 통계 업데이트
function updateStatistics() {
    // 페이지의 모든 주문 행을 확인하여 통계 재계산
    const rows = document.querySelectorAll('.orders-table tbody tr');
    let totalParticipants = 0;
    let totalRevenue = 0;
    let attendedCount = 0;
    
    rows.forEach(row => {
        const statusCell = row.querySelector('td:nth-child(4)');
        const priceCell = row.querySelector('td:nth-child(2)');
        const attendanceCheckbox = row.querySelector('input[type="checkbox"]');
        
        if (statusCell && !statusCell.textContent.includes('취소됨')) {
            totalParticipants++;
            
            // 가격 추출
            const priceText = priceCell.textContent.trim();
            const price = parseInt(priceText.replace(/[^\d]/g, '')) || 0;
            totalRevenue += price;
            
            // 참석 여부 확인
            if (attendanceCheckbox && attendanceCheckbox.checked) {
                attendedCount++;
            }
        }
    });
    
    // 통계 카드 업데이트
    updateStatCard('총 참가자', totalParticipants);
    updateStatCard('총 매출', totalRevenue);
    updateStatCard('실제 참석자', attendedCount);
    
    // 참석률 계산
    const attendanceRate = totalParticipants > 0 ? (attendedCount / totalParticipants * 100).toFixed(1) : 0;
    updateStatCard('참석률', attendanceRate + '%');
}

// 통계 카드 업데이트
function updateStatCard(label, value) {
    const statCards = document.querySelectorAll('.stat-card');
    
    statCards.forEach(card => {
        const labelElement = card.querySelector('div:last-child');
        if (labelElement && labelElement.textContent.includes(label)) {
            const valueElement = card.querySelector('div:first-child');
            if (valueElement) {
                valueElement.textContent = value;
            }
        }
    });
}

// 참석 표시 업데이트
function updateAttendanceDisplay(orderId, isAttended, attendedAt = null) {
    const row = document.querySelector(`tr[data-order-id="${orderId}"]`);
    if (!row) return;
    
    const attendanceCell = row.querySelector('td:last-child');
    if (attendanceCell) {
        const checkbox = attendanceCell.querySelector('input[type="checkbox"]');
        if (checkbox) {
            checkbox.checked = isAttended;
        }
        
        // 참석 시간 표시 업데이트
        const timeDisplay = attendanceCell.querySelector('.text-xs.text-green-600');
        if (isAttended && attendedAt) {
            if (!timeDisplay) {
                const timeElement = document.createElement('div');
                timeElement.className = 'text-xs text-green-600 dark:text-green-400 mt-1';
                timeElement.innerHTML = `
                    <div>체크일시</div>
                    <div>${formatDate(attendedAt)}</div>
                `;
                attendanceCell.appendChild(timeElement);
            }
        } else if (!isAttended && timeDisplay) {
            timeDisplay.remove();
        }
    }
}

// 참석 상태 업데이트
function updateAttendance(orderId, isAttended) {
    // CSRF 토큰 가져오기
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                     document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    // 현재 URL에서 store_id와 live_lecture_id 추출
    const pathParts = window.location.pathname.split('/');
    const storeId = pathParts[2];
    const liveLectureId = pathParts[5];
    
    fetch(`/lecture/${storeId}/live/${liveLectureId}/update_attendance/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({
            order_id: orderId,
            attended: isAttended
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 참석 표시 업데이트
            updateAttendanceDisplay(orderId, isAttended, data.attended_at);
            
            // 통계 업데이트
            updateStatistics();
            
            // 성공 알림
            showToast(isAttended ? '참석 체크가 완료되었습니다.' : '참석 체크가 해제되었습니다.', 'success');
        } else {
            // 실패 시 체크박스 상태 복원
            const checkbox = document.querySelector(`#attendance_${orderId}`);
            if (checkbox) {
                checkbox.checked = !isAttended;
            }
            
            showToast('참석 상태 업데이트 중 오류가 발생했습니다.', 'error');
        }
    })
    .catch(error => {
        console.error('참석 상태 업데이트 오류:', error);
        
        // 실패 시 체크박스 상태 복원
        const checkbox = document.querySelector(`#attendance_${orderId}`);
        if (checkbox) {
            checkbox.checked = !isAttended;
        }
        
        showToast('참석 상태 업데이트 중 오류가 발생했습니다.', 'error');
    });
}

// 토스트 메시지 표시
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300 ${getToastClass(type)}`;
    toast.innerHTML = `<i class="fas ${getToastIcon(type)} mr-2"></i>${message}`;
    
    document.body.appendChild(toast);
    
    // 3초 후 제거
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

function getToastClass(type) {
    switch(type) {
        case 'success':
            return 'bg-green-500 text-white';
        case 'error':
            return 'bg-red-500 text-white';
        case 'warning':
            return 'bg-yellow-500 text-white';
        default:
            return 'bg-blue-500 text-white';
    }
}

function getToastIcon(type) {
    switch(type) {
        case 'success':
            return 'fa-check';
        case 'error':
            return 'fa-times';
        case 'warning':
            return 'fa-exclamation-triangle';
        default:
            return 'fa-info';
    }
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
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
} 