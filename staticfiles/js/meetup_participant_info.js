// meetup_participant_info.js

document.addEventListener('DOMContentLoaded', function() {
    // 밋업 데이터 초기화
    initializeMeetupData();
    
    // 초기 상태 설정
    updatePriceSummary();
    updateSubmitButton();
    
    // 이벤트 리스너 설정
    setupEventListeners();
});

// 밋업 데이터
let meetupData = {};
let selectedOptions = {};

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
    }
    
    // 입력 필드 변경 시 실시간 유효성 검사
    const inputs = document.querySelectorAll('input[required]');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldError);
    });
}

// 옵션 선택 함수 (비활성화됨 - 읽기 전용으로 변경)
// function selectOption(choiceElement) {
//     // 이 함수는 더 이상 사용되지 않습니다.
//     // 참가자 정보 입력 페이지에서는 선택된 옵션만 표시합니다.
// }

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
    const basePrice = meetupData.basePrice || 0;
    const optionsPrice = Object.values(selectedOptions).reduce((sum, opt) => sum + opt.price, 0);
    const totalPrice = basePrice + optionsPrice;
    
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

// 폼 제출 처리
function handleFormSubmit(event) {
    const form = event.target;
    const submitBtn = document.getElementById('submit-btn');
    
    // 유효성 검사
    if (!validateForm(form)) {
        event.preventDefault();
        return false;
    }
    
    // 제출 버튼 로딩 상태
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.classList.add('loading');
        
        const submitText = document.getElementById('submit-text');
        const submitIcon = document.getElementById('submit-icon');
        
        if (submitText) submitText.textContent = '처리 중...';
        if (submitIcon) submitIcon.className = 'fas fa-spinner fa-spin mr-2';
    }
    
    return true;
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

// 전역 함수로 노출
// window.selectOption = selectOption; 