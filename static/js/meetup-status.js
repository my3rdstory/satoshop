// 밋업 현황 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeMeetupStatus();
});

function initializeMeetupStatus() {
    // 통계 카드 애니메이션 초기화
    initializeStatsCards();
    
    // 밋업 카드 호버 효과 초기화
    initializeMeetupCards();
    
}

function initializeStatsCards() {
    // 통계 카드 애니메이션 효과 제거됨
}

function initializeMeetupCards() {
    const meetupCards = document.querySelectorAll('.bg-gray-50.dark\\:bg-gray-700');
    
    meetupCards.forEach(card => {
        // 카드 클릭 시 부드러운 전환 효과
        card.addEventListener('click', function(e) {
            // 링크 클릭은 기본 동작 유지
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                return;
            }
            
            // 카드 전체 클릭 시 링크로 이동
            const link = this.querySelector('a');
            if (link) {
                window.location.href = link.href;
            }
        });
        
        // 카드 호버 시 커서 변경
        card.style.cursor = 'pointer';
    });
}

// 유틸리티 함수들
function formatNumber(num) {
    return new Intl.NumberFormat('ko-KR').format(num);
}

function formatSats(sats) {
    return formatNumber(sats) + ' sats';
} 