// 배송 정보 입력 폼 검증 스크립트

document.addEventListener('DOMContentLoaded', function() {
    const checkoutBtn = document.getElementById('checkout-btn');
    const checkoutBtnText = document.getElementById('checkout-btn-text');
    
    // 필수 필드들
    const requiredFields = [
        'buyer_name',
        'buyer_phone', 
        'buyer_email',
        'shipping_postal_code',
        'shipping_address'
    ];
    
    function validateForm() {
        let allFilled = true;
        
        requiredFields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (!field || !field.value.trim()) {
                allFilled = false;
            }
        });
        
        if (allFilled) {
            checkoutBtn.disabled = false;
            checkoutBtn.classList.remove('disabled:bg-gray-400', 'disabled:cursor-not-allowed', 'disabled:shadow-none');
            checkoutBtn.classList.add('bg-bitcoin', 'hover:bg-bitcoin/90');
            checkoutBtnText.textContent = '다음 단계 (결제하기)';
        } else {
            checkoutBtn.disabled = true;
            checkoutBtn.classList.add('disabled:bg-gray-400', 'disabled:cursor-not-allowed', 'disabled:shadow-none');
            checkoutBtn.classList.remove('bg-bitcoin', 'hover:bg-bitcoin/90');
            checkoutBtnText.textContent = '필수 정보를 입력해주세요';
        }
    }
    
    // 각 필수 필드에 이벤트 리스너 추가
    requiredFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('input', validateForm);
            field.addEventListener('blur', validateForm);
        }
    });
    
    // 초기 검증
    validateForm();
}); 