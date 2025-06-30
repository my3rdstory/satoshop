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
    }
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

// 옵션 선택 함수
function selectOption(choiceElement) {
    const optionId = choiceElement.dataset.optionId;
    const choiceId = choiceElement.dataset.choiceId;
    const choicePrice = parseFloat(choiceElement.dataset.choicePrice) || 0;
    const isCurrentlySelected = choiceElement.classList.contains('selected');
    
    // 같은 옵션 그룹의 모든 선택지들 비활성화
    document.querySelectorAll(`[data-option-id="${optionId}"]`).forEach(choice => {
        choice.classList.remove('selected');
        choice.classList.remove('border-purple-500', 'bg-purple-50', 'dark:bg-purple-900/20');
        choice.classList.add('border-gray-200', 'dark:border-gray-600');
        
        const indicator = choice.querySelector('.choice-indicator i');
        if (indicator) {
            indicator.className = 'fas fa-circle text-gray-300 dark:text-gray-600';
        }
    });
    
    // 이미 선택된 옵션이 아니라면 활성화
    if (!isCurrentlySelected) {
        choiceElement.classList.add('selected');
        choiceElement.classList.remove('border-gray-200', 'dark:border-gray-600');
        choiceElement.classList.add('border-purple-500', 'bg-purple-50', 'dark:bg-purple-900/20');
        
        const indicator = choiceElement.querySelector('.choice-indicator i');
        if (indicator) {
            indicator.className = 'fas fa-check-circle text-purple-500';
        }
        
        // 선택된 옵션 저장
        selectedOptions[optionId] = {
            choiceId: choiceId,
            price: choicePrice
        };
    } else {
        // 토글로 선택 해제
        delete selectedOptions[optionId];
    }
    
    // 가격 업데이트
    updatePriceSummary();
    updateSubmitButton();
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
        
        const optionElement = document.querySelector(`[data-choice-id="${option.choiceId}"]`);
        if (optionElement) {
            const optionGroup = optionElement.closest('.option-group');
            const optionName = optionGroup ? optionGroup.querySelector('h4').textContent : '';
            const choiceName = optionElement.querySelector('.option-title').textContent;
            
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
        }
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
    
    // 필수 옵션 체크
    const requiredOptions = document.querySelectorAll('[data-required="true"]');
    let allRequiredSelected = true;
    
    for (let option of requiredOptions) {
        const optionId = option.dataset.optionId;
        if (!selectedOptions[optionId]) {
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
    
    // 필수 옵션 체크
    const requiredOptions = document.querySelectorAll('[data-required="true"]');
    for (let option of requiredOptions) {
        const optionId = option.dataset.optionId;
        if (!selectedOptions[optionId]) {
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
window.selectOption = selectOption; 