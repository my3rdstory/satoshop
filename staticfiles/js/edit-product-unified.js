// edit-product-unified.js - 상품 수정 전용 JavaScript

document.addEventListener('DOMContentLoaded', function () {
  // 페이지 데이터 읽기
  const pageData = document.getElementById('page-data');
  const uploadImageUrl = pageData ? pageData.dataset.uploadUrl : '';
  const storeId = pageData ? pageData.dataset.storeId : '';
  const productId = pageData ? pageData.dataset.productId : '';
  
  // 전역 변수 설정 (add-product.js에서 사용)
  window.productPriceDisplay = document.querySelector('input[name="price_display"]:checked')?.value || 'sats';
  window.productOptionsCount = document.querySelectorAll('.option-section').length;
  
  // addOptionChoice 함수 정의 (상품 수정 페이지 전용, 중복 정의 방지)
  if (!window.addOptionChoice) {
    window.addOptionChoice = function(button) {
      const optionSection = button.closest('.option-section');
      if (!optionSection) {
        console.error('옵션 섹션을 찾을 수 없습니다.');
        return;
      }
      
      const optionIndex = Array.from(optionSection.parentNode.children).indexOf(optionSection);
      const choicesContainer = optionSection.querySelector('.space-y-3');
      if (!choicesContainer) {
        console.error('선택지 컨테이너를 찾을 수 없습니다.');
        return;
      }
      
      const choiceIndex = choicesContainer.children.length;

      // 현재 상품의 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
      const isKrwMode = window.productPriceDisplay === 'krw';
      const priceUnit = isKrwMode ? '원' : 'sats';
      const exchangeInfoClass = isKrwMode ? '' : 'hidden';

      const choiceDiv = document.createElement('div');
      choiceDiv.className = 'flex items-center gap-3';
      choiceDiv.innerHTML = `
        <div class="flex-1">
          <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                 type="text" name="options[${optionIndex}][choices][${choiceIndex}][name]" required
                 placeholder="옵션 종류 (예: 빨강, 파랑)">
        </div>
        <div class="w-32">
          <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 option-price-input"
                 type="number" name="options[${optionIndex}][choices][${choiceIndex}][price]" min="0"
                 placeholder="추가 가격">
        </div>
        <div class="relative w-16">
          <span class="text-sm text-gray-500 dark:text-gray-400 option-price-unit">${priceUnit}</span>
          <div class="text-xs text-gray-600 dark:text-gray-400 mt-1 option-exchange-info ${exchangeInfoClass}">
            <span class="option-converted-amount"></span>        
          </div>
        </div>
        <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                onclick="this.closest('.flex').remove()">
          <i class="fas fa-times"></i>
        </button>
      `;

      choicesContainer.appendChild(choiceDiv);
      
      // 옵션 종류 추가됨
      
      // 새로 추가된 옵션 가격 입력 필드에 이벤트 리스너 추가 (currency-exchange.js에서 처리)
      const newPriceInput = choiceDiv.querySelector('.option-price-input');
      if (newPriceInput && typeof handlePriceInput === 'function') {
        newPriceInput.addEventListener('input', handlePriceInput);
      }
    };
  }
  
  // 옵션 추가 버튼 이벤트 리스너 (중복 등록 방지)
  const addOptionBtn = document.getElementById('addOptionBtn');
  if (addOptionBtn && !addOptionBtn.hasAttribute('data-edit-initialized')) {
    // 중복 초기화 방지를 위한 플래그 설정
    addOptionBtn.setAttribute('data-edit-initialized', 'true');
    
    addOptionBtn.addEventListener('click', function() {
      const optionsContainer = document.getElementById('optionsContainer');
      if (!optionsContainer) {
        console.error('옵션 컨테이너를 찾을 수 없습니다.');
        return;
      }
      
      const currentOptionCount = optionsContainer.children.length;
      
      // 현재 상품의 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
      const isKrwMode = window.productPriceDisplay === 'krw';
      const priceUnit = isKrwMode ? '원' : 'sats';
      const exchangeInfoClass = isKrwMode ? '' : 'hidden';
      
      const optionDiv = document.createElement('div');
      optionDiv.className = 'bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 space-y-4 option-section';
      optionDiv.innerHTML = `
        <div class="flex items-center gap-4">
          <div class="flex-1">
            <input class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                   type="text" name="options[${currentOptionCount}][name]" required
                   placeholder="옵션명 (예: 색상, 사이즈)">
          </div>
          <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                  onclick="this.closest('.option-section').remove()">
            <i class="fas fa-trash"></i>
          </button>
        </div>
        
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <div class="flex-1">
              <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                     type="text" name="options[${currentOptionCount}][choices][0][name]" required
                     placeholder="옵션 종류 (예: 빨강, 파랑)">
            </div>
            <div class="w-32">
              <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 option-price-input"
                     type="number" name="options[${currentOptionCount}][choices][0][price]" min="0"
                     placeholder="추가 가격">
            </div>
            <div class="relative w-16">
              <span class="text-sm text-gray-500 dark:text-gray-400 option-price-unit">${priceUnit}</span>
              <div class="text-xs text-gray-600 dark:text-gray-400 mt-1 option-exchange-info ${exchangeInfoClass}">
                <span class="option-converted-amount"></span>
              </div>
            </div>
            <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                    onclick="this.closest('.flex').remove()">
              <i class="fas fa-times"></i>
            </button>
          </div>
        </div>
        
        <button type="button" class="inline-flex items-center gap-2 px-4 py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 rounded-lg transition-colors" 
                onclick="addOptionChoice(this)">
          <i class="fas fa-plus text-sm"></i>
          <span>옵션 종류 추가</span>
        </button>
      `;
      
      optionsContainer.appendChild(optionDiv);
      
      // 새로 추가된 옵션 가격 입력 필드에 이벤트 리스너 추가
      const newPriceInput = optionDiv.querySelector('.option-price-input');
      if (newPriceInput && typeof handlePriceInput === 'function') {
        newPriceInput.addEventListener('input', handlePriceInput);
      }
      
      // 새 옵션 추가됨
    });
  }
  
  // add-product.js의 공통 기능이 이미 초기화되므로 추가 설정만 수행
      // 상품 수정 모드 초기화 완료
}); 