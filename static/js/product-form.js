// 상품 폼 관련 통합 JavaScript

window.initProductForm = function (isEditMode, initialOptionCount) {
  // 할인 관련
  const isDiscounted = document.getElementById('is_discounted');
  const discountSection = document.getElementById('discountSection');

  if (isDiscounted && discountSection) {
    isDiscounted.addEventListener('change', function () {
      discountSection.classList.toggle('hidden', !this.checked);
    });
  }

  // 가격 표시 방식 변경에 따른 단위 업데이트
  const priceDisplayRadios = document.querySelectorAll('input[name="price_display"]');
  const priceUnits = document.querySelectorAll('.price-unit');

  function updatePriceUnits(selectedValue) {
    const unit = selectedValue === 'sats' ? 'sats' : '원';
    priceUnits.forEach(unitElement => {
      unitElement.textContent = unit;
    });
    
    // 옵션 가격 단위도 업데이트
    const optionUnits = document.querySelectorAll('.option-price-unit');
    optionUnits.forEach(unitElement => {
      unitElement.textContent = unit;
    });
    
    // 배송비 도움말 텍스트도 업데이트
    const shippingHelp = document.querySelector('#shipping_fee')?.closest('.field')?.querySelector('.help');
    if (shippingHelp) {
      if (selectedValue === 'sats') {
        shippingHelp.textContent = '배송비는 사토시 단위로 입력하세요 (0sats인 경우 배송비 무료로 표시됩니다)';
      } else {
        shippingHelp.textContent = '배송비는 원 단위로 입력하세요 (0원인 경우 배송비 무료로 표시됩니다)';
      }
    }
  }

  // 초기 단위 설정
  const checkedRadio = document.querySelector('input[name="price_display"]:checked');
  if (checkedRadio) {
    updatePriceUnits(checkedRadio.value);
  }

  // 라디오 버튼 변경 이벤트 리스너
  priceDisplayRadios.forEach(radio => {
    radio.addEventListener('change', function() {
      if (this.checked) {
        updatePriceUnits(this.value);
      }
    });
  });

  // 옵션 관련
  const optionsContainer = document.getElementById('optionsContainer');
  const addOptionBtn = document.getElementById('addOptionBtn');
  let optionCount = isEditMode ? initialOptionCount : 0;

  if (addOptionBtn && !addOptionBtn.hasAttribute('data-initialized')) {
    // 옵션 편집 페이지에서는 edit-options.js에서 처리하므로 건너뜀
    const isOptionsEditPage = document.getElementById('optionsForm');
    if (isOptionsEditPage) {
      return;
    }
    
    // 상품 수정 페이지(unifiedProductForm)에서는 edit-product-unified.js에서 처리하므로 건너뜀
    const isProductEditPage = document.getElementById('unifiedProductForm');
    if (isProductEditPage) {
      console.log('상품 수정 페이지에서는 product-form.js의 옵션 기능을 비활성화');
      return;
    }
    
    // 중복 초기화 방지를 위한 플래그 설정
    addOptionBtn.setAttribute('data-initialized', 'true');
    
    addOptionBtn.addEventListener('click', function () {
      if (optionCount >= 20) {
        alert('옵션은 최대 20개까지만 추가할 수 있습니다.');
        return;
      }

      // 현재 선택된 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
      const checkedRadio = document.querySelector('input[name="price_display"]:checked');
      // 라디오 버튼이 없는 경우(옵션 편집 페이지) window.productPriceDisplay 사용
      const isKrwMode = checkedRadio ? checkedRadio.value === 'krw' : window.productPriceDisplay === 'krw';
      const priceUnit = isKrwMode ? '원' : 'sats';
      const exchangeInfoClass = isKrwMode ? '' : 'hidden';

      const optionSection = document.createElement('div');
      optionSection.className = 'option-section bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 space-y-4';
      optionSection.innerHTML = `
        <div class="flex items-center gap-4">
          <div class="flex-1">
            <input class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
                   type="text" name="options[${optionCount}][name]" required
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
                     type="text" name="options[${optionCount}][choices][0][name]" required
                     placeholder="옵션 종류 (예: 빨강, 파랑)">
            </div>
            <div class="w-32">
              <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 option-price-input"
                     type="number" name="options[${optionCount}][choices][0][price]" min="0"
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
      optionsContainer.appendChild(optionSection);
      optionCount++;
    });
  }

  // addOptionChoice 함수를 전역으로 정의 (이미 정의되어 있다면 덮어쓰지 않음)
  if (!window.addOptionChoice) {
    // 옵션 편집 페이지에서는 edit-options.js에서 처리하므로 건너뜀
    const isOptionsEditPage = document.getElementById('optionsForm');
    if (isOptionsEditPage) {
      return;
    }
    
    // 상품 수정 페이지(unifiedProductForm)에서는 edit-product-unified.js에서 처리하므로 건너뜀
    const isProductEditPage = document.getElementById('unifiedProductForm');
    if (isProductEditPage) {
      console.log('상품 수정 페이지에서는 product-form.js의 addOptionChoice 함수를 비활성화');
      return;
    }
    
    window.addOptionChoice = function (button) {
      const optionSection = button.closest('.option-section');
      const optionIndex = Array.from(optionsContainer.children).indexOf(optionSection);
      const choicesContainer = optionSection.querySelector('.space-y-3');
      const choiceCount = choicesContainer.children.length;

      if (choiceCount >= 20) {
        alert('옵션 종류는 최대 20개까지만 추가할 수 있습니다.');
        return;
      }

      // 현재 선택된 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
      const checkedRadio = document.querySelector('input[name="price_display"]:checked');
      // 라디오 버튼이 없는 경우(옵션 편집 페이지) window.productPriceDisplay 사용
      const isKrwMode = checkedRadio ? checkedRadio.value === 'krw' : window.productPriceDisplay === 'krw';
      const priceUnit = isKrwMode ? '원' : 'sats';
      const exchangeInfoClass = isKrwMode ? '' : 'hidden';

      const choiceDiv = document.createElement('div');
      choiceDiv.className = 'flex items-center gap-3';
      choiceDiv.innerHTML = `
        <div class="flex-1">
          <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                 type="text" name="options[${optionIndex}][choices][${choiceCount}][name]" required
                 placeholder="옵션 종류 (예: 빨강, 파랑)">
        </div>
        <div class="w-32">
          <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 option-price-input"
                 type="number" name="options[${optionIndex}][choices][${choiceCount}][price]" min="0"
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
    }
  }

  // 폼 제출 시 옵션 데이터 수집
  const productForm = document.getElementById('productForm') || document.getElementById('optionsForm') || document.getElementById('unifiedProductForm');
  if (productForm && !productForm.hasAttribute('data-options-initialized')) {
    // 중복 초기화 방지를 위한 플래그 설정
    productForm.setAttribute('data-options-initialized', 'true');
    
    productForm.addEventListener('submit', function (e) {
      // optionsForm인 경우 기본 폼 제출 방식을 사용하므로 옵션 데이터 수집을 건너뜀
      if (productForm.id === 'optionsForm') {
        return; // 기본 폼 제출 방식 사용
      }
      
      // 옵션 데이터 수집 (productForm인 경우만)
      const options = [];
      document.querySelectorAll('.option-section').forEach((optionSection, optionIndex) => {
        const optionName = optionSection.querySelector('input[name*="[name]"]')?.value;
        if (optionName) {
          const choices = [];
          optionSection.querySelectorAll('.space-y-3 > .flex').forEach((choiceDiv, choiceIndex) => {
            const choiceName = choiceDiv.querySelector('input[name*="[name]"]')?.value;
            const choicePrice = parseInt(choiceDiv.querySelector('input[name*="[price]"]')?.value) || 0;

            if (choiceName) {
              choices.push({
                name: choiceName,
                price: choicePrice,
                order: choiceIndex
              });
            }
          });

          if (choices.length > 0) {
            options.push({
              name: optionName,
              order: optionIndex,
              choices: choices
            });
          }
        }
      });

      // 옵션 데이터를 hidden input으로 추가
      let optionsInput = document.querySelector('input[name="options"]');
      if (!optionsInput) {
        optionsInput = document.createElement('input');
        optionsInput.type = 'hidden';
        optionsInput.name = 'options';
        this.appendChild(optionsInput);
      }
      optionsInput.value = JSON.stringify(options);
    });
  }
}; 