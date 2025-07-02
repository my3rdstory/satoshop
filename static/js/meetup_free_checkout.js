// meetup_free_checkout.js - 무료 밋업 전용 스크립트
console.log('🚀 meetup_free_checkout.js 로드됨');

let countdownInstance = null;

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 무료 밋업 체크아웃 페이지 초기화');
    
    // 데이터 로드
    const freeCheckoutDataElement = document.getElementById('free-checkout-data');
    if (!freeCheckoutDataElement) {
        console.error('❌ 무료 체크아웃 데이터를 찾을 수 없습니다.');
        return;
    }
    
    const checkoutData = JSON.parse(freeCheckoutDataElement.textContent);
    window.freeCheckoutData = checkoutData;
    console.log('✅ 무료 체크아웃 데이터 로드:', checkoutData);
    
    // 카운트다운 초기화
    initializeCountdown();
    
    // 폼 이벤트 리스너 등록
    setupFormEventListener();
});

// 카운트다운 초기화
function initializeCountdown() {
    const data = window.freeCheckoutData;
    
    if (data.reservationExpiresAt && window.MeetupCountdown) {
        console.log('🕒 카운트다운 초기화 시작');
        
        countdownInstance = new MeetupCountdown({
            storeId: data.storeId,
            meetupId: data.meetupId,
            reservationExpiresAt: data.reservationExpiresAt
        });
        
        // 전역에서 접근 가능하도록 저장
        window.meetupCountdownInstance = countdownInstance;
        
        console.log('✅ 카운트다운 초기화 완료');
    } else {
        console.log('⚠️ 카운트다운 정보가 없거나 MeetupCountdown 클래스가 로드되지 않음');
    }
}

// 폼 이벤트 리스너 설정
function setupFormEventListener() {
    const form = document.getElementById('free-participation-form');
    
    if (!form) {
        console.error('❌ 무료 참가 신청 폼을 찾을 수 없습니다.');
        return;
    }
    
    console.log('📝 무료 참가 신청 폼 이벤트 리스너 등록');
    
    form.addEventListener('submit', function(event) {
        console.log('🆓 무료 참가 신청 폼 제출됨!');
        
        // 카운트다운 중지
        stopCountdown();
        
        // 버튼 상태 변경
        updateButtonState();
        
        // 폼 제출 계속 진행 (event.preventDefault() 호출하지 않음)
        console.log('📤 서버로 폼 제출 진행');
    });
}

// 카운트다운 중지
function stopCountdown() {
    if (window.meetupCountdownInstance) {
        console.log('🛑 카운트다운 중지 시도');
        
        try {
            window.meetupCountdownInstance.stopAndHide();
            console.log('✅ 카운트다운 중지 성공');
        } catch (error) {
            console.error('❌ 카운트다운 중지 실패:', error);
        }
    } else {
        console.log('⚠️ 카운트다운 인스턴스가 없음');
    }
}

// 버튼 상태 변경
function updateButtonState() {
    const button = document.getElementById('freeParticipationBtn');
    
    if (button) {
        console.log('🔄 버튼 상태를 "처리 중"으로 변경');
        
        button.disabled = true;
        button.innerHTML = `
            <div class="flex items-center">
                <div class="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent mr-3"></div>
                <span>참가 신청 처리 중...</span>
            </div>
        `;
    } else {
        console.error('❌ 무료 참가 신청 버튼을 찾을 수 없음');
    }
} 