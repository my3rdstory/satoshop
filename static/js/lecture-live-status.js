// 라이브 강의 현황 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeLiveLectureStatus();
});

function initializeLiveLectureStatus() {
    // 통계 카드 애니메이션 초기화
    initializeStatsCards();
    
    // 라이브 강의 카드 호버 효과 초기화
    initializeLectureCards();
    
    console.log('라이브 강의 현황 페이지가 초기화되었습니다.');
}

function initializeStatsCards() {
    // 통계 카드에 애니메이션 효과 추가
    const statsCards = document.querySelectorAll('.stats-card');
    
    statsCards.forEach((card, index) => {
        // 카드 호버 시 부드러운 애니메이션
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });
    
    console.log('통계 카드 초기화 완료');
}

function initializeLectureCards() {
    const lectureCards = document.querySelectorAll('.bg-gray-50.dark\\:bg-gray-700');
    
    lectureCards.forEach(card => {
        // 카드 클릭 시 부드러운 전환 효과
        card.addEventListener('click', function(e) {
            // 링크 클릭은 기본 동작 유지
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                return;
            }
            
            // 카드 전체 클릭 시 링크로 이동
            const link = this.querySelector('a');
            if (link) {
                // 클릭 애니메이션 효과
                this.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    window.location.href = link.href;
                }, 150);
            }
        });
        
        // 카드 호버 시 커서 변경
        card.style.cursor = 'pointer';
        
        // 카드 호버 효과
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
            this.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '';
        });
    });
    
    console.log('라이브 강의 카드 초기화 완료');
}

// 통계 업데이트 함수
function updateStatistics() {
    // 페이지 새로고침 없이 통계 업데이트 (향후 확장용)
    console.log('통계 업데이트 요청');
}

// 카드 상태 표시 함수
function updateCardStatus(cardElement, status) {
    const statusElements = cardElement.querySelectorAll('.inline-flex.items-center.px-2.py-1');
    
    // 기존 상태 제거
    statusElements.forEach(element => {
        element.remove();
    });
    
    // 새 상태 추가
    if (status !== 'active') {
        const statusBadge = document.createElement('span');
        statusBadge.className = 'ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium';
        
        switch(status) {
            case 'inactive':
                statusBadge.className += ' bg-gray-500 text-white';
                statusBadge.textContent = '비활성화';
                break;
            case 'expired':
                statusBadge.className += ' bg-gray-600 text-white';
                statusBadge.textContent = '종료';
                break;
            case 'temporarily_closed':
                statusBadge.className += ' bg-purple-500 text-white';
                statusBadge.textContent = '일시중단';
                break;
        }
        
        const titleElement = cardElement.querySelector('h3');
        titleElement.appendChild(statusBadge);
    }
}

// 검색 및 필터 기능 (향후 확장용)
function filterLectures(searchTerm = '', status = 'all') {
    const lectureCards = document.querySelectorAll('.bg-gray-50.dark\\:bg-gray-700');
    
    lectureCards.forEach(card => {
        const title = card.querySelector('h3').textContent.toLowerCase();
        const matchesSearch = title.includes(searchTerm.toLowerCase());
        const matchesStatus = status === 'all' || card.classList.contains(`lecture-${status}`);
        
        if (matchesSearch && matchesStatus) {
            card.style.display = 'block';
        } else {
            card.style.display = 'none';
        }
    });
}

// 유틸리티 함수들
function formatNumber(num) {
    return new Intl.NumberFormat('ko-KR').format(num);
}

function formatSats(sats) {
    return formatNumber(sats) + ' sats';
}

function formatKRW(amount) {
    return formatNumber(amount) + ' 원';
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

// 토스트 메시지 표시 함수
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