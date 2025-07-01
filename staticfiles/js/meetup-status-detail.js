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