// meetup_free_checkout.js - 무료 밋업 전용 스크립트

let countdownInstance = null;

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    
    // 데이터 로드
    const freeCheckoutDataElement = document.getElementById('free-checkout-data');
    if (!freeCheckoutDataElement) {
        return;
    }
    
    const checkoutData = JSON.parse(freeCheckoutDataElement.textContent);
    window.freeCheckoutData = checkoutData;
    
    // 카운트다운 초기화
    initializeCountdown();
    
    // 폼 이벤트 리스너 등록
    setupFormEventListener();
});

// 카운트다운 초기화
function initializeCountdown() {
    const data = window.freeCheckoutData;
    
    if (data.reservationExpiresAt && window.MeetupCountdown) {
        
        countdownInstance = new MeetupCountdown({
            storeId: data.storeId,
            meetupId: data.meetupId,
            reservationExpiresAt: data.reservationExpiresAt
        });
        
        // 전역에서 접근 가능하도록 저장
        window.meetupCountdownInstance = countdownInstance;
        
    } else {
    }
}

// 폼 이벤트 리스너 설정
function setupFormEventListener() {
    const form = document.getElementById('free-participation-form');
    
    if (!form) {
        return;
    }
    
    
    form.addEventListener('submit', function(event) {
        
        // 카운트다운 중지
        stopCountdown();
        
        // 버튼 상태 변경
        updateButtonState();
        
        // 폼 제출 계속 진행 (event.preventDefault() 호출하지 않음)
    });
}

// 카운트다운 중지
function stopCountdown() {
    if (window.meetupCountdownInstance) {
        
        try {
            window.meetupCountdownInstance.stopAndHide();
        } catch (error) {
        }
    } else {
    }
}

// 버튼 상태 변경
function updateButtonState() {
    const button = document.getElementById('freeParticipationBtn');
    
    if (button) {
        
        button.disabled = true;
        button.innerHTML = `
            <div class="flex items-center">
                <div class="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent mr-3"></div>
                <span>참가 신청 처리 중...</span>
            </div>
        `;
    } else {
    }
} 