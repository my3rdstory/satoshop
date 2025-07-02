// meetup_participant_info.js
console.log('🚀 meetup_participant_info.js 파일이 로드되었습니다!');

document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 DOMContentLoaded 이벤트 발생');
    console.log('🔍 window.meetupData:', window.meetupData);
    
    // 밋업 데이터 초기화
    initializeMeetupData();
    
    // 초기 상태 설정
    updatePriceSummary();
    updateSubmitButton();
    
    // 이벤트 리스너 설정
    setupEventListeners();
    
    // 카운트다운 초기화
    initializeCountdown();
});

// 밋업 데이터
let meetupData = {};
let selectedOptions = {};
let countdownInterval = null;

// 밋업 데이터 초기화
function initializeMeetupData() {
    // 템플릿에서 전달받은 데이터
    if (typeof window.meetupData !== 'undefined') {
        meetupData = window.meetupData;
        
        // 전달받은 선택된 옵션이 있다면 적용
        if (meetupData.selectedOptions && typeof meetupData.selectedOptions === 'object') {
            selectedOptions = { ...meetupData.selectedOptions };
            
            // DOM이 로드된 후 옵션 선택 상태 적용
            setTimeout(() => {
                applySelectedOptions();
            }, 100);
        }
    }
}

// 선택된 옵션 적용
function applySelectedOptions() {
    const selectedOptionsDisplay = document.getElementById('selected-options-display');
    const noOptionsMessage = document.getElementById('no-options-message');
    
    if (!selectedOptionsDisplay) return;
    
    // 선택된 옵션이 있는지 확인
    if (Object.keys(selectedOptions).length === 0) {
        if (noOptionsMessage) {
            noOptionsMessage.style.display = 'block';
        }
        return;
    }
    
    // 선택된 옵션들을 표시
    let optionsHTML = '';
    
    Object.entries(selectedOptions).forEach(([optionId, optionData]) => {
        // 옵션 정보 가져오기 (서버에서 전달된 데이터 사용)
        const optionName = optionData.optionName || '옵션';
        const choiceName = optionData.choiceName || optionData.name || '선택지';
        const price = optionData.price || 0;
        
        optionsHTML += `
            <div class="p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-xl">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-medium text-gray-900 dark:text-white">${optionName}</div>
                        <div class="text-sm text-purple-600 dark:text-purple-400 mt-1">
                            <i class="fas fa-check-circle mr-1"></i>
                            ${choiceName}
                        </div>
                    </div>
                    <div class="text-right">
                        ${price > 0 ? 
                            `<div class="font-medium text-gray-900 dark:text-white">+${price.toLocaleString()} sats</div>` : 
                            `<div class="text-sm text-green-600 dark:text-green-400">무료</div>`
                        }
                    </div>
                </div>
            </div>
        `;
    });
    
    selectedOptionsDisplay.innerHTML = optionsHTML;
    
    // "선택된 옵션이 없습니다" 메시지 숨기기
    if (noOptionsMessage) {
        noOptionsMessage.style.display = 'none';
    }
    
    // 가격 요약 업데이트
    updatePriceSummary();
    updateSubmitButton();
}

// 이벤트 리스너 설정
function setupEventListeners() {
    // 폼 제출 시 유효성 검사
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
        
        // 폼 내에서 엔터키 입력 시 제출 버튼 클릭으로 처리
        form.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && !event.ctrlKey && !event.metaKey) {
                event.preventDefault();
                
                // 현재 포커스된 요소가 텍스트 입력 필드인지 확인
                const activeElement = document.activeElement;
                if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
                    // 제출 버튼이 활성화되어 있는지 확인
                    const submitBtn = document.getElementById('submit-btn');
                    if (submitBtn && !submitBtn.disabled) {
                        console.log('⌨️ 엔터키로 폼 제출 트리거');
                        submitBtn.click();
                    }
                }
            }
        });
    }
    
    // 입력 필드 변경 시 실시간 유효성 검사
    const inputs = document.querySelectorAll('input[required]');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldError);
    });
}

// 가격 요약 업데이트
function updatePriceSummary() {
    const summaryDiv = document.getElementById('selected-options-summary');
    const totalPriceEl = document.getElementById('total-price');
    
    if (!summaryDiv || !totalPriceEl) return;
    
    let optionsTotal = 0;
    let summaryHTML = '';
    
    // 선택된 옵션들 표시
    Object.values(selectedOptions).forEach(option => {
        optionsTotal += option.price;
        
        const optionName = option.optionName || '옵션';
        const choiceName = option.choiceName || option.name || '선택지';
        
        summaryHTML += `
          <div class="flex justify-between text-sm">
            <span class="text-gray-600 dark:text-gray-400">
              <i class="fas fa-chevron-right mr-2 text-xs"></i>${optionName}: ${choiceName}
            </span>
            <span class="font-medium text-gray-900 dark:text-white">
              ${option.price > 0 ? '+' + option.price.toLocaleString() + ' sats' : '무료'}
            </span>
          </div>
        `;
    });
    
    summaryDiv.innerHTML = summaryHTML;
    
    // 총 가격 계산
    const basePrice = meetupData.basePrice || 0;
    const totalPrice = basePrice + optionsTotal;
    totalPriceEl.textContent = totalPrice.toLocaleString() + ' sats';
    
    // 숨겨진 필드에 옵션 정보 저장
    const selectedOptionsInput = document.getElementById('selected_options');
    if (selectedOptionsInput) {
        selectedOptionsInput.value = JSON.stringify(selectedOptions);
    }
}

// 총 가격 계산
function calculateTotalPrice() {
    const basePrice = meetupData.basePrice || 0;
    const optionsPrice = Object.values(selectedOptions).reduce((sum, opt) => sum + opt.price, 0);
    return basePrice + optionsPrice;
}

// 제출 버튼 업데이트
function updateSubmitButton() {
    const submitBtn = document.getElementById('submit-btn');
    const submitIcon = document.getElementById('submit-icon');
    const submitText = document.getElementById('submit-text');
    
    if (!submitBtn || !submitIcon || !submitText) return;
    
    // 필수 옵션 체크 (서버에서 전달받은 필수 옵션 ID 목록 사용)
    const requiredOptionIds = meetupData.requiredOptionIds || [];
    let allRequiredSelected = true;
    
    for (let optionId of requiredOptionIds) {
        if (!selectedOptions[optionId.toString()]) {
            allRequiredSelected = false;
            break;
        }
    }
    
    // 총 가격 확인
    const totalPrice = calculateTotalPrice();
    
    if (allRequiredSelected) {
        submitBtn.disabled = false;
        submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        
        if (totalPrice === 0) {
            submitIcon.className = 'fas fa-check mr-2';
            submitText.textContent = '무료 참가 신청하기';
        } else {
            submitIcon.className = 'fas fa-credit-card mr-2';
            submitText.textContent = '결제하기';
        }
    } else {
        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
        submitIcon.className = 'fas fa-exclamation-triangle mr-2';
        submitText.textContent = '필수 옵션을 선택해주세요';
    }
}

// 카운트다운 중지 및 숨기기
function stopAndHideCountdown() {
    console.log('🛑 카운트다운 중지 및 숨기기 함수 호출됨');
    console.log('🔍 window.meetupCountdownInstance 존재 여부:', !!window.meetupCountdownInstance);
    
    // 새로운 MeetupCountdown 클래스 인스턴스가 있는지 확인
    if (window.meetupCountdownInstance) {
        console.log('🔄 MeetupCountdown 인스턴스로 카운트다운 중지 시도');
        try {
            window.meetupCountdownInstance.stopAndHide();
            console.log('✅ MeetupCountdown.stopAndHide() 호출 완료');
        } catch (error) {
            console.error('❌ MeetupCountdown.stopAndHide() 호출 실패:', error);
        }
        return;
    }
    
    console.log('🔄 기존 방식으로 카운트다운 중지 시도');
    
    // 기존 방식 (호환성을 위해 유지)
    // 카운트다운 인터벌 중지
    if (countdownInterval) {
        clearInterval(countdownInterval);
        countdownInterval = null;
        console.log('⏹️ 카운트다운 인터벌 중지됨');
    } else {
        console.log('⚠️ countdownInterval이 없음');
    }
    
    // 플로팅 카운트다운 숨기기
    const floatingCountdown = document.getElementById('floating-countdown');
    if (floatingCountdown) {
        floatingCountdown.classList.remove('show');
        floatingCountdown.classList.add('hidden');
        console.log('👻 플로팅 카운트다운 숨김 완료');
    } else {
        console.log('⚠️ floating-countdown 요소를 찾을 수 없음');
    }
}

// 폼 제출 처리
function handleFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitButton = form.querySelector('#submit-btn');
    const totalPrice = calculateTotalPrice();
    
    console.log('📋 폼 제출 시작');
    console.log('💰 총 가격:', totalPrice);
    console.log('🎯 meetupData.basePrice:', meetupData.basePrice);
    console.log('📊 selectedOptions:', selectedOptions);
    console.log('🌍 window.meetupCountdownInstance:', window.meetupCountdownInstance);
    
    // 폼 유효성 검사
    if (!validateForm(form)) {
        console.log('❌ 폼 유효성 검사 실패');
        return;
    }
    
    // 무료 밋업인 경우에만 카운트다운 중지 및 숨기기
    if (totalPrice === 0) {
        console.log('🆓 무료 밋업 감지 - 카운트다운 중지 시작');
        stopAndHideCountdown();
    } else {
        console.log('💳 유료 밋업 - 카운트다운 유지 (결제 페이지로 이동 후 연장)');
        // 유료 밋업에서는 카운트다운을 유지하고, 서버에서 예약 시간을 연장함
    }
    
    // 버튼 상태 변경
    submitButton.disabled = true;
    submitButton.innerHTML = `
        <div class="flex items-center">
            <div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
            <span>처리 중...</span>
        </div>
    `;
    
    // 폼 제출
    setTimeout(() => {
        form.submit();
    }, 500);
}

// 폼 유효성 검사
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('input[required]');
    
    requiredFields.forEach(field => {
        if (!validateField({ target: field })) {
            isValid = false;
        }
    });
    
    // 필수 옵션 체크 (서버에서 전달받은 필수 옵션 ID 목록 사용)
    const requiredOptionIds = meetupData.requiredOptionIds || [];
    for (let optionId of requiredOptionIds) {
        if (!selectedOptions[optionId.toString()]) {
            showError('필수 옵션을 모두 선택해주세요.');
            isValid = false;
            break;
        }
    }
    
    return isValid;
}

// 필드 유효성 검사
function validateField(event) {
    const field = event.target;
    const value = field.value.trim();
    let isValid = true;
    
    // 필수 필드 검사
    if (field.hasAttribute('required') && !value) {
        showFieldError(field, '이 필드는 필수입니다.');
        isValid = false;
    }
    
    // 이메일 형식 검사
    if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            showFieldError(field, '올바른 이메일 주소를 입력해주세요.');
            isValid = false;
        }
    }
    
    // 전화번호 형식 검사 (선택사항)
    if (field.type === 'tel' && value) {
        const phoneRegex = /^[0-9-+\s()]+$/;
        if (!phoneRegex.test(value)) {
            showFieldError(field, '올바른 전화번호 형식을 입력해주세요.');
            isValid = false;
        }
    }
    
    if (isValid) {
        clearFieldError(field);
    }
    
    return isValid;
}

// 필드 오류 표시
function showFieldError(field, message) {
    clearFieldError(field);
    
    field.classList.add('border-red-500', 'bg-red-50', 'dark:bg-red-900/20');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error text-red-500 text-sm mt-1';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
}

// 필드 오류 제거
function clearFieldError(field) {
    if (typeof field === 'object' && field.target) {
        field = field.target;
    }
    
    field.classList.remove('border-red-500', 'bg-red-50', 'dark:bg-red-900/20');
    
    const errorDiv = field.parentNode.querySelector('.field-error');
    if (errorDiv) {
        errorDiv.remove();
    }
}

// 일반 오류 메시지 표시
function showError(message) {
    // 기존 오류 메시지 제거
    const existingError = document.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message bg-red-100 dark:bg-red-900/20 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg mb-4';
    errorDiv.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-exclamation-circle mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    
    const form = document.querySelector('form');
    if (form) {
        form.insertBefore(errorDiv, form.firstChild);
    }
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 3000);
}

// 카운트다운 초기화
function initializeCountdown() {
    console.log('📅 카운트다운 초기화 시작');
    console.log('📅 meetupData:', meetupData);
    console.log('📅 reservationExpiresAt:', meetupData.reservationExpiresAt);
    
    if (!meetupData.reservationExpiresAt) {
        console.log('⏰ 예약 만료 시간이 없어서 카운트다운을 표시하지 않음');
        return; // 예약 만료 시간이 없으면 카운트다운을 표시하지 않음
    }
    
    const floatingCountdown = document.getElementById('floating-countdown');
    console.log('🎈 플로팅 카운트다운 요소:', floatingCountdown);
    
    if (!floatingCountdown) {
        console.error('❌ floating-countdown 요소를 찾을 수 없음');
        return;
    }
    
    console.log('✅ 카운트다운 표시 시작');
    
    // 카운트다운 표시
    setTimeout(() => {
        floatingCountdown.classList.add('show');
        console.log('🎈 카운트다운 show 클래스 추가됨');
    }, 1000);
    
    // 카운트다운 시작
    startCountdown();
}

// 카운트다운 시작
function startCountdown() {
    const countdownDisplay = document.getElementById('countdown-display');
    const floatingCountdown = document.getElementById('floating-countdown');
    
    if (!countdownDisplay || !floatingCountdown) return;
    
    countdownInterval = setInterval(() => {
        const now = new Date();
        const expiresAt = new Date(meetupData.reservationExpiresAt);
        const timeLeft = expiresAt - now;
        
        if (timeLeft <= 0) {
            // 시간 만료
            clearInterval(countdownInterval);
            countdownDisplay.textContent = '00:00';
            floatingCountdown.classList.add('urgent');
            
            // 페이지 새로고침 또는 리다이렉트
            setTimeout(() => {
                alert('예약 시간이 만료되었습니다. 다시 시도해주세요.');
                window.location.href = `/meetup/${meetupData.storeId}/${meetupData.meetupId}/`;
            }, 2000);
            return;
        }
        
        // 시간 계산
        const minutes = Math.floor(timeLeft / 60000);
        const seconds = Math.floor((timeLeft % 60000) / 1000);
        
        // 시간 표시 형식
        const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        countdownDisplay.textContent = timeString;
        
        // 1분 미만일 때 긴급 스타일 적용
        if (timeLeft < 60000) {
            floatingCountdown.classList.add('urgent');
        } else {
            floatingCountdown.classList.remove('urgent');
        }
        
        // 30초 미만일 때 추가 경고
        if (timeLeft < 30000 && timeLeft > 25000) {
            showWarningNotification('예약 시간이 30초 남았습니다!');
        }
        
    }, 1000);
}

// 경고 알림 표시
function showWarningNotification(message) {
    // 기존 알림이 있으면 제거
    const existingNotification = document.getElementById('warning-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 새로운 알림 생성
    const notification = document.createElement('div');
    notification.id = 'warning-notification';
    notification.className = 'fixed top-4 right-4 bg-red-500 text-white px-4 py-3 rounded-lg shadow-lg z-50 animate-bounce';
    notification.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-exclamation-triangle mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (notification && notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function(event) {
    // 카운트다운 정리
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    // 임시 예약이 있는 경우 서버에 해제 요청
    if (meetupData.reservationExpiresAt && window.navigator.sendBeacon) {
        const releaseUrl = `/meetup/${meetupData.storeId}/${meetupData.meetupId}/release_reservation/`;
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', getCsrfToken());
        formData.append('reason', '사용자가 페이지를 벗어남');
        
        // 백그라운드에서 비동기 요청 (페이지가 닫혀도 실행됨)
        window.navigator.sendBeacon(releaseUrl, formData);
    }
});

// 페이지 숨김 이벤트 (모바일 앱 전환, 탭 변경 등에도 대응)
document.addEventListener('visibilitychange', function() {
    if (document.hidden && meetupData.reservationExpiresAt) {
        // 페이지가 숨겨질 때도 예약 해제
        releaseReservation('사용자가 페이지를 벗어남');
    }
});

// CSRF 토큰 가져오기
function getCsrfToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

// 예약 해제 함수
function releaseReservation(reason = '사용자 취소') {
    if (!meetupData.reservationExpiresAt) return;
    
    const releaseUrl = `/meetup/${meetupData.storeId}/${meetupData.meetupId}/release_reservation/`;
    
    // sendBeacon 사용 (페이지가 닫혀도 전송됨)
    if (window.navigator.sendBeacon) {
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', getCsrfToken());
        formData.append('reason', reason);
        
        window.navigator.sendBeacon(releaseUrl, formData);
    } else {
        // sendBeacon을 지원하지 않는 브라우저의 경우 동기 요청
        try {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', releaseUrl, false); // 동기 요청
            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
            xhr.setRequestHeader('X-CSRFToken', getCsrfToken());
            xhr.send(`reason=${encodeURIComponent(reason)}`);
        } catch (e) {
            console.log('예약 해제 요청 실패:', e);
        }
    }
    
    // 예약 해제됨을 표시
    meetupData.reservationExpiresAt = null;
}

// 전역 함수로 노출
// window.selectOption = selectOption; 