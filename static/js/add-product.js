// add-product.js - 상품 추가/수정 공통 JavaScript

// 전역 변수
window.productFormUtils = {
  easyMDE: null,
  isEditMode: false
};

document.addEventListener('DOMContentLoaded', function () {
  // 편집 모드 감지
  const isEditMode = document.getElementById('unifiedProductForm') !== null;
  window.productFormUtils.isEditMode = isEditMode;
  
  // === 공통 기능 초기화 ===
  initEasyMDE();
  initImageUpload();
  initDiscountToggle();
  initCompletionMessagePreview();
  initFormValidation();
  
  // === 상품 폼 초기화 ===
  if (typeof window.initProductForm === 'function') {
    const optionCount = isEditMode ? (window.productOptionsCount || document.querySelectorAll('.option-section').length) : 0;
    window.initProductForm(isEditMode, optionCount);
  }
  
  // === 편집 모드 전용 기능 ===
  if (isEditMode) {
    initEditModeFeatures();
  }
});

// === EasyMDE 초기화 ===
function initEasyMDE() {
  const descriptionElement = document.getElementById('description');
  if (descriptionElement) {
    // 이미 초기화되었는지 확인 (중복 초기화 방지)
    if (descriptionElement.hasAttribute('data-easymde-initialized')) {
      // EasyMDE 이미 초기화됨
      return;
    }
    
    const easyMDE = new EasyMDE({
      element: descriptionElement,
      placeholder: '상품에 대한 설명을 마크다운 형식으로 작성하세요.\n\n예:\n# 상품 소개\n\n- 고품질 소재\n- 빠른 배송\n\n## 사용법\n\n1. 간단한 사용법\n2. 주의사항',
      spellChecker: false,
      status: false,
      toolbar: [
        'bold', 'italic', 'heading', '|',
        'quote', 'unordered-list', 'ordered-list', '|',
        'link', 'image'
      ]
    });
    
    // 초기화 완료 표시
    descriptionElement.setAttribute('data-easymde-initialized', 'true');
    
    // 전역에서 접근 가능하도록 저장
    window.productFormUtils.easyMDE = easyMDE;
    window.productDescriptionMDE = easyMDE; // 하위 호환성
    
          // EasyMDE 초기화 완료
  }
}

// === 이미지 업로드 초기화 ===
function initImageUpload() {
  const imageDropArea = document.getElementById('imageDropArea');
  const imageInput = document.getElementById('imageInput');

  if (!imageDropArea || !imageInput) return;

  // 드래그 앤 드롭 이벤트
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    imageDropArea.addEventListener(eventName, preventDefaults, false);
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    imageDropArea.addEventListener(eventName, highlight, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    imageDropArea.addEventListener(eventName, unhighlight, false);
  });

  imageDropArea.addEventListener('drop', handleDrop, false);
  imageDropArea.addEventListener('click', () => imageInput.click());
  imageInput.addEventListener('change', function () {
    handleFiles(this.files);
  });
}

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function highlight(e) {
  const imageDropArea = document.getElementById('imageDropArea');
  if (window.productFormUtils.isEditMode) {
    imageDropArea.classList.add('border-amber-400', 'dark:border-amber-500', 'bg-amber-50', 'dark:bg-amber-900');
  } else {
    imageDropArea.classList.add('border-green-400', 'dark:border-green-500', 'bg-green-50', 'dark:bg-green-900');
  }
}

function unhighlight(e) {
  const imageDropArea = document.getElementById('imageDropArea');
  if (window.productFormUtils.isEditMode) {
    imageDropArea.classList.remove('border-amber-400', 'dark:border-amber-500', 'bg-amber-50', 'dark:bg-amber-900');
  } else {
    imageDropArea.classList.remove('border-green-400', 'dark:border-green-500', 'bg-green-50', 'dark:bg-green-900');
  }
}

function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  handleFiles(files);
}

function handleFiles(files) {
  const imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));

  if (imageFiles.length === 0) {
    alert('이미지 파일만 업로드할 수 있습니다.');
    return;
  }

  // 파일 크기 검증 (각각 10MB)
  for (let file of imageFiles) {
    if (file.size > 10 * 1024 * 1024) {
      alert(`${file.name} 파일이 너무 큽니다. (최대 10MB)`);
      return;
    }
  }

  if (window.productFormUtils.isEditMode) {
    // 편집 모드: 서버에 즉시 업로드
    const currentImages = document.getElementById('currentImages');
    const currentImageCount = currentImages ? currentImages.querySelectorAll('[id^="image-"]').length : 0;
    if (currentImageCount + imageFiles.length > 10) {
      alert('상품당 최대 10개의 이미지만 업로드할 수 있습니다.');
      return;
    }
    
    imageFiles.forEach(file => {
      uploadImageToServer(file);
    });
  } else {
    // 추가 모드: 미리보기만 표시
    imageFiles.forEach(file => {
      addImagePreview(file);
    });
  }
}

// === 편집 모드: 서버 업로드 ===
async function uploadImageToServer(file) {
  const pageData = document.getElementById('page-data');
  const uploadImageUrl = pageData ? pageData.dataset.uploadUrl : '';
  
  const formData = new FormData();
  formData.append('image', file);
  formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

  try {
    const progressDiv = showUploadProgress(file.name);
    
    const response = await fetch(uploadImageUrl, {
      method: 'POST',
      body: formData
    });

    const result = await response.json();
    progressDiv.remove();

    if (result.success) {
      addImageToCurrentList(result.image);
    } else {
      console.error('업로드 실패:', result.error);
      alert(`${file.name} 업로드에 실패했습니다: ${result.error}`);
    }

  } catch (error) {
    console.error('업로드 오류:', error);
    alert(`${file.name} 업로드 중 오류가 발생했습니다.`);
  }
}

function showUploadProgress(fileName) {
  const progressDiv = document.createElement('div');
  progressDiv.className = 'relative group';
  progressDiv.innerHTML = `
    <div class="aspect-square bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden flex items-center justify-center">
      <div class="text-center">
        <i class="fas fa-spinner fa-spin text-2xl text-gray-400 mb-2"></i>
        <p class="text-xs text-gray-600 dark:text-gray-400">업로드 중...</p>
        <p class="text-xs text-gray-500 dark:text-gray-500">${fileName}</p>
      </div>
    </div>
  `;
  
  let currentImages = document.getElementById('currentImages');
  if (currentImages) {
    currentImages.appendChild(progressDiv);
  }
  
  return progressDiv;
}

function addImageToCurrentList(imageData) {
  let currentImages = document.getElementById('currentImages');

  if (currentImages) {
    const div = document.createElement('div');
    div.className = 'relative group';
    div.id = `image-${imageData.id}`;
    div.innerHTML = `
      <div class="aspect-square bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden">
        <img src="${imageData.file_url}" alt="${imageData.original_name}" 
             class="w-full h-full object-cover">
        <button onclick="deleteExistingImage(${imageData.id})"
                class="absolute top-2 right-2 w-8 h-8 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <i class="fas fa-times text-sm"></i>
        </button>
      </div>
      <div class="mt-2 text-center">
        <p class="text-xs text-gray-600 dark:text-gray-400 truncate">${imageData.original_name}</p>
        <p class="text-xs text-gray-500 dark:text-gray-500">${formatFileSize(imageData.file_size)}</p>
      </div>
    `;

    currentImages.appendChild(div);
  }
}

// === 추가 모드: 미리보기 ===
function addImagePreview(file) {
  const reader = new FileReader();
  reader.onload = function(e) {
    let previewContainer = document.getElementById('imagePreviewContainer');
    if (!previewContainer) {
      const imageField = document.querySelector('#imageDropArea').closest('.bg-white');
      const previewSection = document.createElement('div');
      previewSection.innerHTML = `
        <div class="mt-6">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">이미지 미리보기</label>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4" id="imagePreviewContainer"></div>
        </div>
      `;
      imageField.appendChild(previewSection);
      previewContainer = document.getElementById('imagePreviewContainer');
    }

    const previewDiv = document.createElement('div');
    previewDiv.className = 'relative group';
    previewDiv.innerHTML = `
      <div class="aspect-square bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden">
        <img src="${e.target.result}" alt="${file.name}" class="w-full h-full object-cover">
        <button type="button" class="absolute top-2 right-2 w-8 h-8 bg-red-500 hover:bg-red-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                onclick="this.closest('.relative').remove()">
          <i class="fas fa-times text-sm"></i>
        </button>
      </div>
      <div class="mt-2 text-center">
        <p class="text-xs text-gray-600 dark:text-gray-400 truncate">${file.name}</p>
        <p class="text-xs text-gray-500 dark:text-gray-500">${formatFileSize(file.size)}</p>
      </div>
    `;
    previewContainer.appendChild(previewDiv);
  };
  reader.readAsDataURL(file);
}

// === 할인 설정 토글 ===
function initDiscountToggle() {
  const isDiscountedCheckbox = document.getElementById('is_discounted');
  const discountSectionDiv = document.getElementById('discountSection');
  
  if (isDiscountedCheckbox && discountSectionDiv) {
    isDiscountedCheckbox.addEventListener('change', function() {
      if (this.checked) {
        discountSectionDiv.classList.remove('hidden');
      } else {
        discountSectionDiv.classList.add('hidden');
      }
    });
  }
}

// === 완료 메시지 미리보기 ===
function initCompletionMessagePreview() {
  const textarea = document.getElementById('completion_message');
  const preview = document.getElementById('messagePreview');

  if (textarea && preview) {
    textarea.addEventListener('input', function () {
      const message = this.value.trim();
      if (message) {
        const formattedMessage = message.replace(/\n/g, '<br>');
        preview.innerHTML = formattedMessage;
      } else {
        preview.innerHTML = '<em class="text-gray-500">메시지를 입력하면 여기에 미리보기가 표시됩니다.</em>';
      }
    });
  }
}

// === 폼 유효성 검사 ===
function initFormValidation() {
  const forms = ['productForm', 'unifiedProductForm'];
  
  forms.forEach(formId => {
    const form = document.getElementById(formId);
    if (form) {
      form.addEventListener('submit', function (e) {
        const easyMDE = window.productFormUtils.easyMDE;
        if (easyMDE) {
          const descriptionValue = easyMDE.value().trim();
          if (!descriptionValue) {
            e.preventDefault();
            alert('상품 설명을 입력해주세요.');
            easyMDE.codemirror.focus();
            return false;
          }
        }
      });
    }
  });
}

// === 편집 모드 전용 기능 ===
function initEditModeFeatures() {
  // 가격 표시 방식 변경 이벤트
  const priceDisplayRadios = document.querySelectorAll('input[name="price_display"]');
  priceDisplayRadios.forEach(radio => {
    radio.addEventListener('change', handlePriceDisplayChange);
  });

  // 기존 옵션들의 단위와 환율 정보 초기화
  initializeExistingOptions();
  
  // 옵션 가격 입력 시 환율 변환 이벤트 리스너 추가
  setupPriceConversionListeners();
  
  // 상품 관리 기능 초기화
  initProductManagement();
}

function handlePriceDisplayChange(event) {
  const priceDisplay = event.target.value;
  const krwFields = document.querySelectorAll('.krw-field');
  const satsFields = document.querySelectorAll('.sats-field');
  
  if (priceDisplay === 'krw') {
    krwFields.forEach(field => field.classList.remove('hidden'));
    satsFields.forEach(field => field.classList.add('hidden'));
  } else {
    krwFields.forEach(field => field.classList.add('hidden'));
    satsFields.forEach(field => field.classList.remove('hidden'));
  }
  
  // 옵션 가격 단위도 업데이트
  updateOptionPriceUnits(priceDisplay);
}

function initializeExistingOptions() {
  const allUnitSpans = document.querySelectorAll('.option-price-unit');
  const allExchangeInfos = document.querySelectorAll('.option-exchange-info');
  
  const priceDisplay = window.productPriceDisplay || 'sats';
  
  if (priceDisplay === 'krw') {
    allUnitSpans.forEach(span => {
      span.textContent = '원';
    });
    allExchangeInfos.forEach(info => {
      info.classList.remove('hidden');
    });
  } else {
    allUnitSpans.forEach(span => {
      span.textContent = 'sats';
    });
    allExchangeInfos.forEach(info => {
      info.classList.add('hidden');
    });
  }
}

function updateOptionPriceUnits(priceDisplay) {
  const allUnitSpans = document.querySelectorAll('.option-price-unit');
  const allExchangeInfos = document.querySelectorAll('.option-exchange-info');
  
  if (priceDisplay === 'krw') {
    allUnitSpans.forEach(span => {
      span.textContent = '원';
    });
    allExchangeInfos.forEach(info => {
      info.classList.remove('hidden');
    });
  } else {
    allUnitSpans.forEach(span => {
      span.textContent = 'sats';
    });
    allExchangeInfos.forEach(info => {
      info.classList.add('hidden');
    });
  }
}

function setupPriceConversionListeners() {
  document.querySelectorAll('.option-price-input').forEach(input => {
    input.addEventListener('input', handleOptionPriceInput);
  });
}

function handleOptionPriceInput(event) {
  const priceDisplay = window.productPriceDisplay || 'sats';
  if (priceDisplay !== 'krw') return;
  
  const input = event.target;
  const value = parseFloat(input.value);
  const exchangeInfo = input.closest('.flex').querySelector('.option-converted-amount');
  
  if (exchangeInfo && !isNaN(value) && value > 0) {
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

function initProductManagement() {
  // 상품 상태 변경 확인
  window.confirmStatusChange = function(checkbox) {
    const form = document.getElementById('toggleForm');
    const originalCheckbox = form.querySelector('input[name="is_active"]');
    const isCurrentlyActive = originalCheckbox.defaultChecked;
    const willBeActive = checkbox.checked;

    let message;
    if (willBeActive && !isCurrentlyActive) {
      message = '상품을 활성화하시겠습니까?\n\n활성화하면 고객들이 이 상품을 구매할 수 있습니다.';
    } else if (!willBeActive && isCurrentlyActive) {
      message = '상품을 비활성화하시겠습니까?\n\n비활성화하면 고객들이 이 상품을 구매할 수 없게 됩니다.\n상품 목록에서는 여전히 보이지만 구매가 불가능합니다.';
    }

    if (confirm(message)) {
      document.getElementById('toggleForm').submit();
    } else {
      checkbox.checked = !checkbox.checked;
    }
  }

  // 상품 삭제 확인
  window.confirmDelete = function() {
    if (confirm('정말로 이 상품을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없으며, 다음 데이터가 모두 삭제됩니다:\n- 상품 정보\n- 상품 이미지\n- 상품 옵션\n- 관련 주문 내역\n\n삭제하려면 "확인"을 클릭하세요.')) {
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = window.deleteProductUrl || '/products/delete/';
      
      const csrfToken = document.createElement('input');
      csrfToken.type = 'hidden';
      csrfToken.name = 'csrfmiddlewaretoken';
      csrfToken.value = document.querySelector('[name=csrfmiddlewaretoken]')?.value || window.csrfToken || '';
      
      form.appendChild(csrfToken);
      document.body.appendChild(form);
      form.submit();
    }
  }
}

// === 편집 모드 전용: 기존 이미지 삭제 ===
window.deleteExistingImage = async function (imageId) {
  if (!confirm('이 이미지를 삭제하시겠습니까?')) {
    return;
  }

  try {
    const pageData = document.getElementById('page-data');
    const storeId = pageData ? pageData.dataset.storeId : '';
    const productId = pageData ? pageData.dataset.productId : '';
    const deleteUrl = `/products/${storeId}/${productId}/delete-image/${imageId}/`;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    const response = await fetch(deleteUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `csrfmiddlewaretoken=${encodeURIComponent(csrfToken)}`
    });

    const result = await response.json();

    if (result.success) {
      const imageElement = document.getElementById(`image-${imageId}`);
      if (imageElement) {
        imageElement.remove();
      }
    } else {
      alert('이미지 삭제에 실패했습니다: ' + result.error);
    }
  } catch (error) {
    console.error('삭제 오류:', error);
    alert('이미지 삭제 중 오류가 발생했습니다.');
  }
}

// === 유틸리티 함수 ===
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// === 전역 함수 등록 (하위 호환성) ===
// addOptionChoice 함수는 product-form.js에서 정의됨 