// 상품 데이터 로드 (전역 변수로 설정되어야 함)
// const productData = JSON.parse(document.getElementById('product-data').textContent);

// 전역 변수
let selectedOptions = {};
let currentQuantity = 1;
let basePrice = 0;
let shippingFee = 0;
let productData = null;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
  // 상품 데이터 로드
  const productDataElement = document.getElementById('product-data');
  if (productDataElement) {
    productData = JSON.parse(productDataElement.textContent);
    basePrice = productData.basePrice;
    shippingFee = productData.shippingFee;
    
    // 전역 변수로 설정
    window.productData = productData;
  }

  const quantityInput = document.getElementById('quantity');
  if (quantityInput) {
    quantityInput.addEventListener('input', validateQuantity);
  }
  
  // 초기 총액 계산
  updateTotalPrice();
});

// 장바구니 관련 함수들은 cart.js에서 처리됩니다

// 메인 이미지 변경
function changeMainImage(imageUrl, thumbnail) {
  const mainImage = document.getElementById('mainImage');
  if (mainImage) {
    mainImage.src = imageUrl;
  }
  
  // 썸네일 활성화 상태 변경
  document.querySelectorAll('.thumbnail').forEach(thumb => {
    thumb.classList.remove('active');
  });
  if (thumbnail) {
    thumbnail.classList.add('active');
  }
}

// 옵션 선택 (토글 방식)
function selectOption(element) {
    const optionId = element.dataset.optionId;
    const isCurrentlySelected = element.classList.contains('selected');
    
    // 같은 옵션 그룹의 모든 선택지들 비활성화
    document.querySelectorAll(`[data-option-id="${optionId}"]`).forEach(option => {
        option.classList.remove('selected');
        option.classList.remove('border-orange-500', 'bg-orange-500', 'text-white');
        option.classList.add('border-black', 'dark:border-white');
    });
    
    // 이미 선택된 옵션이 아니라면 활성화 (토글 효과)
    if (!isCurrentlySelected) {
        element.classList.add('selected');
        element.classList.remove('border-black', 'dark:border-white');
        element.classList.add('border-orange-500', 'bg-orange-500', 'text-white');
    }
    
    updateTotalPrice();
}

// 수량 변경
function changeQuantity(delta) {
    const quantityInput = document.getElementById('quantity');
    if (!quantityInput) return;
    
    const currentQuantity = parseInt(quantityInput.value);
    const newQuantity = Math.max(1, currentQuantity + delta);
    
    quantityInput.value = newQuantity;
    updateTotalPrice();
}

// 수량 유효성 검사
function validateQuantity() {
    const quantityInput = document.getElementById('quantity');
    if (!quantityInput) return;
    
    const quantity = parseInt(quantityInput.value);
    
    if (quantity < 1) {
        quantityInput.value = 1;
    }
    
    updateTotalPrice();
}

// 총액 계산 업데이트
function updateTotalPrice() {
    if (!productData) return;
    
    const quantity = parseInt(document.getElementById('quantity')?.value || 1);
    
    // 기본 상품 가격
    let productPrice = productData.basePrice;
    
    // 선택된 옵션들의 추가 가격 계산
    let optionsPrice = 0;
    const selectedOptions = document.querySelectorAll('.option-choice.selected');
    selectedOptions.forEach(option => {
        optionsPrice += parseInt(option.dataset.choicePrice || 0);
    });
    
    // 총 계산
    const productTotal = (productPrice + optionsPrice) * quantity;
    const shippingFee = productData.shippingFee;
    const finalTotal = productTotal + shippingFee;
    
    // UI 업데이트
    const productTotalElement = document.getElementById('productTotal');
    const quantityDisplay = document.getElementById('quantityDisplay');
    const finalTotalElement = document.getElementById('finalTotal');
    
    if (productTotalElement) {
        productTotalElement.textContent = `${(productPrice * quantity).toLocaleString()} sats`;
    }
    if (quantityDisplay) {
        quantityDisplay.textContent = `${quantity}개`;
    }
    if (finalTotalElement) {
        finalTotalElement.textContent = `${finalTotal.toLocaleString()} sats`;
    }
    
    // 옵션 추가금액 표시
    const optionsRow = document.getElementById('optionsRow');
    const optionsTotal = document.getElementById('optionsTotal');
    
    if (optionsRow && optionsTotal) {
        if (optionsPrice > 0) {
            optionsRow.classList.remove('hidden');
            optionsTotal.textContent = `${(optionsPrice * quantity).toLocaleString()} sats`;
        } else {
            optionsRow.classList.add('hidden');
        }
    }
}

// 장바구니에 추가
function addToCart() {
    if (!productData) return;
    

    
    const quantity = parseInt(document.getElementById('quantity')?.value || 1);
    const selectedOptions = {};
    
    // 선택된 옵션들 수집 (cart.js와 동일한 형식으로)
    document.querySelectorAll('.option-choice.selected').forEach(option => {
        selectedOptions[option.dataset.optionId] = option.dataset.choiceId;
    });
    
    // 서버로 전송 (JSON 형식으로)
    fetch(productData.addToCartUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': productData.csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            product_id: productData.productId,
            quantity: quantity,
            selected_options: selectedOptions
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 장바구니 배지 업데이트
            updateCartBadge(data.cart_count);
            
            // 성공 메시지 (간단하게)
            showSuccessMessage('장바구니에 추가되었습니다!');
            
            // 장바구니 내용 업데이트 및 사이드바 열기
            updateCartContent();
            openCart();
        } else {
            alert(data.error || '장바구니 추가에 실패했습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('오류가 발생했습니다. 다시 시도해주세요.');
    });
}

// 공통 함수들은 cart-common.js에서 로드됩니다

// 장바구니에서 제거 함수는 cart.js에서 처리됩니다 