document.addEventListener('DOMContentLoaded', function () {
  // 상품 폼 초기화 (edit mode = true, 현재 옵션 개수 전달)
  if (typeof window.initProductForm === 'function') {
    // 현재 옵션 개수를 전역 변수에서 가져오거나 동적으로 계산
    const optionCount = window.productOptionsCount || document.querySelectorAll('.option-section').length;
    window.initProductForm(true, optionCount);
  }
  
  // 기존 옵션들의 단위와 환율 정보 초기화
  initializeExistingOptions();
  
  // 옵션 가격 입력 시 환율 변환 이벤트 리스너 추가
  setupPriceConversionListeners();
  
  // 옵션 추가 버튼 이벤트 리스너 추가
  setupAddOptionButton();
});

function initializeExistingOptions() {
  const optionSections = document.querySelectorAll('.option-section');
  
  optionSections.forEach(function(section, index) {
    // 기존 옵션들의 가격 표시 방식 설정
    const priceInputs = section.querySelectorAll('input[name$="[price]"]');
    priceInputs.forEach(function(input) {
      // 가격 표시 방식에 따른 단위 설정
      let priceUnit = 'sats';
      if (window.productPriceDisplay === 'krw') {
        priceUnit = '원';
      }
      
      // 입력 필드 옆에 단위 표시
      if (!input.parentElement.querySelector('.price-unit')) {
        const unitSpan = document.createElement('span');
        unitSpan.className = 'price-unit ml-2 text-sm text-gray-500';
        unitSpan.textContent = priceUnit;
        input.parentElement.appendChild(unitSpan);
      }
    });
  });
}

// 동적으로 추가된 옵션에 대한 이벤트 리스너
function setupPriceConversionListeners() {
  document.addEventListener('input', function(e) {
    if (e.target && e.target.name && e.target.name.includes('[price]')) {
      // 가격 입력 시 환율 변환 로직
      convertPriceOnInput(e.target);
    }
  });
}

function convertPriceOnInput(input) {
  const value = parseFloat(input.value);
  if (isNaN(value) || value <= 0) return;
  
  // 환율 변환 로직 (필요에 따라 구현)
  // 현재는 단순히 단위만 표시
  const unitSpan = input.parentElement.querySelector('.price-unit');
  if (unitSpan) {
    if (window.productPriceDisplay === 'krw') {
      unitSpan.textContent = '원';
    } else {
      unitSpan.textContent = 'sats';
    }
  }
}

function setupAddOptionButton() {
  const addOptionBtn = document.getElementById('add-option-btn');
  if (!addOptionBtn) return;
  
  addOptionBtn.addEventListener('click', function() {
    addNewOption();
  });
}

function addNewOption() {
  const optionsContainer = document.getElementById('options-container');
  if (!optionsContainer) return;
  
  const optionIndex = document.querySelectorAll('.option-section').length;
  
  // 새 옵션 HTML 생성
  const newOptionHtml = createNewOptionHtml(optionIndex);
  
  // 옵션 추가
  optionsContainer.insertAdjacentHTML('beforeend', newOptionHtml);
  
  // 새로 추가된 옵션에 이벤트 리스너 추가
  setupNewOptionEvents(optionIndex);
}

function createNewOptionHtml(index) {
  let priceUnit = 'sats';
  if (window.productPriceDisplay === 'krw') {
    priceUnit = '원';
  }
  
  return `
    <div class="option-section border border-gray-300 rounded-lg p-4 mb-4" data-option-index="${index}">
      <div class="flex justify-between items-center mb-3">
        <h4 class="text-lg font-medium">옵션 ${index + 1}</h4>
        <button type="button" class="remove-option-btn text-red-600 hover:text-red-800">
          <i class="fas fa-trash"></i> 삭제
        </button>
      </div>
      
      <div class="mb-3">
        <label class="block text-sm font-medium mb-2">옵션명</label>
        <input type="text" name="options[${index}][name]" class="w-full p-2 border border-gray-300 rounded" placeholder="예: 색상, 크기 등">
      </div>
      
      <div class="option-choices">
        <label class="block text-sm font-medium mb-2">선택지</label>
        <div class="choice-item flex items-center mb-2">
          <input type="text" name="options[${index}][choices][0][name]" class="flex-1 p-2 border border-gray-300 rounded mr-2" placeholder="선택지명">
          <input type="number" name="options[${index}][choices][0][price]" class="w-24 p-2 border border-gray-300 rounded mr-2" placeholder="0" min="0" step="1">
          <span class="price-unit text-sm text-gray-500 mr-2">${priceUnit}</span>
          <button type="button" class="remove-choice-btn text-red-600 hover:text-red-800">
            <i class="fas fa-minus-circle"></i>
          </button>
        </div>
      </div>
      
      <button type="button" class="add-choice-btn mt-2 px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
        <i class="fas fa-plus"></i> 선택지 추가
      </button>
    </div>
  `;
}

function setupNewOptionEvents(optionIndex) {
  const optionSection = document.querySelector(`[data-option-index="${optionIndex}"]`);
  if (!optionSection) return;
  
  // 옵션 삭제 버튼
  const removeBtn = optionSection.querySelector('.remove-option-btn');
  if (removeBtn) {
    removeBtn.addEventListener('click', function() {
      optionSection.remove();
      updateOptionIndexes();
    });
  }
  
  // 선택지 추가 버튼
  const addChoiceBtn = optionSection.querySelector('.add-choice-btn');
  if (addChoiceBtn) {
    addChoiceBtn.addEventListener('click', function() {
      addOptionChoice(optionSection, optionIndex);
    });
  }
  
  // 선택지 삭제 버튼
  const removeChoiceBtns = optionSection.querySelectorAll('.remove-choice-btn');
  removeChoiceBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const choiceItem = btn.closest('.choice-item');
      if (choiceItem) {
        choiceItem.remove();
        updateChoiceIndexes(optionSection, optionIndex);
      }
    });
  });
}

function addOptionChoice(optionSection, optionIndex) {
  const choicesContainer = optionSection.querySelector('.option-choices');
  const choiceCount = choicesContainer.querySelectorAll('.choice-item').length;
  
  let priceUnit = 'sats';
  if (window.productPriceDisplay === 'krw') {
    priceUnit = '원';
  }
  
  const newChoiceHtml = `
    <div class="choice-item flex items-center mb-2">
      <input type="text" name="options[${optionIndex}][choices][${choiceCount}][name]" class="flex-1 p-2 border border-gray-300 rounded mr-2" placeholder="선택지명">
      <input type="number" name="options[${optionIndex}][choices][${choiceCount}][price]" class="w-24 p-2 border border-gray-300 rounded mr-2" placeholder="0" min="0" step="1">
      <span class="price-unit text-sm text-gray-500 mr-2">${priceUnit}</span>
      <button type="button" class="remove-choice-btn text-red-600 hover:text-red-800">
        <i class="fas fa-minus-circle"></i>
      </button>
    </div>
  `;
  
  choicesContainer.insertAdjacentHTML('beforeend', newChoiceHtml);
  
  // 새로 추가된 선택지의 삭제 버튼에 이벤트 리스너 추가
  const newChoiceItem = choicesContainer.lastElementChild;
  const removeBtn = newChoiceItem.querySelector('.remove-choice-btn');
  if (removeBtn) {
    removeBtn.addEventListener('click', function() {
      newChoiceItem.remove();
      updateChoiceIndexes(optionSection, optionIndex);
    });
  }
}

function updateOptionIndexes() {
  const optionSections = document.querySelectorAll('.option-section');
  optionSections.forEach((section, index) => {
    section.setAttribute('data-option-index', index);
    
    // 옵션 제목 업데이트
    const title = section.querySelector('h4');
    if (title) {
      title.textContent = `옵션 ${index + 1}`;
    }
    
    // input name 속성 업데이트
    const inputs = section.querySelectorAll('input');
    inputs.forEach(input => {
      if (input.name) {
        input.name = input.name.replace(/options\[\d+\]/, `options[${index}]`);
      }
    });
  });
}

function updateChoiceIndexes(optionSection, optionIndex) {
  const choiceItems = optionSection.querySelectorAll('.choice-item');
  choiceItems.forEach((item, index) => {
    const inputs = item.querySelectorAll('input');
    inputs.forEach(input => {
      if (input.name) {
        input.name = input.name.replace(/\[choices\]\[\d+\]/, `[choices][${index}]`);
      }
    });
  });
} 