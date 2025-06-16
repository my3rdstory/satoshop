document.addEventListener('DOMContentLoaded', function () {
  // 상품 폼 초기화 (edit mode = true, 현재 옵션 개수 전달)
  if (typeof window.initProductForm === 'function') {
    // 현재 옵션 개수를 전역 변수에서 가져오거나 동적으로 계산
    const optionCount = window.productOptionsCount || document.querySelectorAll('.option-section').length;
    window.initProductForm(true, optionCount);
  }
  
  // 디버깅: 가격 표시 방식 확인
  console.log('Product price display:', window.productPriceDisplay);
  
  // 기존 옵션들의 단위와 환율 정보 초기화
  initializeExistingOptions();
  
  // 옵션 가격 입력 시 환율 변환 이벤트 리스너 추가
  setupPriceConversionListeners();
  
  // 옵션 추가 버튼 이벤트 리스너 추가
  setupAddOptionButton();
});

function initializeExistingOptions() {
  const allUnitSpans = document.querySelectorAll('.option-price-unit');
  const allExchangeInfos = document.querySelectorAll('.option-exchange-info');
  
  console.log('Initializing existing options, price display:', window.productPriceDisplay);
  
  if (window.productPriceDisplay === 'krw') {
    // 원화일 때
    allUnitSpans.forEach(span => {
      span.textContent = '원';
    });
    allExchangeInfos.forEach(info => {
      info.classList.remove('hidden');
    });
  } else {
    // 사토시일 때
    allUnitSpans.forEach(span => {
      span.textContent = 'sats';
    });
    allExchangeInfos.forEach(info => {
      info.classList.add('hidden');
    });
  }
}

function setupPriceConversionListeners() {
  // 기존 옵션 가격 입력 필드에 이벤트 리스너 추가
  document.querySelectorAll('.option-price-input').forEach(input => {
    input.addEventListener('input', handlePriceInput);
  });
}

function handlePriceInput(event) {
  if (window.productPriceDisplay !== 'krw') return;
  
  const input = event.target;
  const value = parseFloat(input.value);
  const exchangeInfo = input.closest('.flex').querySelector('.option-converted-amount');
  
  if (exchangeInfo && !isNaN(value) && value > 0) {
    // 환율 정보가 있다면 변환 계산
    if (window.btcKrwRate && window.btcKrwRate > 0) {
      const satsValue = Math.round((value / window.btcKrwRate) * 100000000);
      exchangeInfo.textContent = `${satsValue.toLocaleString()} sats`;
    } else {
      exchangeInfo.textContent = '환율 정보 로딩 중...';
    }
  } else if (exchangeInfo) {
    exchangeInfo.textContent = '';
  }
}

function setupAddOptionButton() {
  const addOptionBtn = document.getElementById('addOptionBtn');
  if (addOptionBtn && !addOptionBtn.hasAttribute('data-edit-options-initialized')) {
    // 중복 초기화 방지를 위한 플래그 설정
    addOptionBtn.setAttribute('data-edit-options-initialized', 'true');
    
    addOptionBtn.addEventListener('click', function() {
      addNewOption();
    });
  }
}

function addNewOption() {
  const optionsContainer = document.getElementById('optionsContainer');
  if (!optionsContainer) {
    console.error('옵션 컨테이너를 찾을 수 없습니다.');
    return;
  }
  
  const currentOptionCount = optionsContainer.children.length;
  if (currentOptionCount >= 20) {
    alert('옵션은 최대 20개까지만 추가할 수 있습니다.');
    return;
  }
  
  // 현재 상품의 가격 표시 방식에 따라 단위와 환율 정보 표시 여부 결정
  const isKrwMode = window.productPriceDisplay === 'krw';
  const priceUnit = isKrwMode ? '원' : 'sats';
  const exchangeInfoClass = isKrwMode ? '' : 'hidden';
  
  const optionDiv = document.createElement('div');
  optionDiv.className = 'bg-gray-50 dark:bg-gray-700/50 rounded-lg p-6 space-y-4';
  optionDiv.innerHTML = `
    <!-- 옵션 헤더 -->
    <div class="flex items-center gap-4">
      <div class="flex-1">
        <input class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400" 
               type="text" name="options[${currentOptionCount}][name]" required
               placeholder="옵션명 (예: 색상, 사이즈)">
      </div>
      <button type="button" class="p-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
              onclick="this.closest('.bg-gray-50, .dark\\\\:bg-gray-700\\\\/50').remove()">
        <i class="fas fa-trash"></i>
      </button>
    </div>
    
    <!-- 옵션 선택지들 -->
    <div class="space-y-3">
      <div class="flex items-center gap-3">
        <div class="flex-1">
          <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                 type="text"
                 name="options[${currentOptionCount}][choices][0][name]"
                 required placeholder="옵션 종류 (예: 빨강, 파랑)">
        </div>
        <div class="w-32">
          <input class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-bitcoin focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 option-price-input"
                 type="number"
                 name="options[${currentOptionCount}][choices][0][price]"
                 min="0" placeholder="추가 가격">
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
  if (newPriceInput) {
    newPriceInput.addEventListener('input', handlePriceInput);
  }
  
  console.log('Added new option, price display:', window.productPriceDisplay, 'unit:', priceUnit);
}

function addOptionChoice(button) {
  const optionSection = button.closest('.bg-gray-50, .dark\\:bg-gray-700\\/50');
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
  
  console.log('Adding option choice, price display:', window.productPriceDisplay, 'unit:', priceUnit);
  
  // 새로 추가된 옵션 가격 입력 필드에 이벤트 리스너 추가
  const newPriceInput = choiceDiv.querySelector('.option-price-input');
  if (newPriceInput) {
    newPriceInput.addEventListener('input', handlePriceInput);
  }
}

// 전역 함수로 등록
window.addOptionChoice = addOptionChoice; 