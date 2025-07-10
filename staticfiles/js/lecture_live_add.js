// lecture_live_add.js
// 라이브 강의 추가 페이지 JavaScript

// EasyMDE 에디터 변수들
let descriptionEditor;
let completionMessageEditor;

// 환율 관련 변수들
let currentExchangeRate = null;
let isLoadingExchangeRate = false;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
  initializeEditors();
  initializePriceType();
  setupEventListeners();
  setupRealTimeValidation();
  loadExchangeRate();
  addDebugHelper();
  console.log('라이브 강의 추가 페이지 로드 완료');
});

// EasyMDE 에디터 초기화
function initializeEditors() {
  descriptionEditor = new EasyMDE({
    element: document.getElementById('description'),
    spellChecker: false,
    toolbar: ['bold', 'italic', 'strikethrough', '|', 'heading-1', 'heading-2', 'heading-3', '|', 'unordered-list', 'ordered-list', '|', 'link', 'image', 'quote', 'code'],
    placeholder: '강의에 대한 자세한 설명을 작성하세요...'
  });

  completionMessageEditor = new EasyMDE({
    element: document.getElementById('completion_message'),
    spellChecker: false,
    toolbar: ['bold', 'italic', '|', 'heading-2', 'heading-3', '|', 'unordered-list', 'ordered-list', '|', 'link', 'image', 'quote', 'code'],
    placeholder: '참가 완료 후 보여줄 메시지를 작성하세요...'
  });
}

// 환율 정보 로드
async function loadExchangeRate() {
  if (isLoadingExchangeRate) return;
  
  isLoadingExchangeRate = true;
  try {
    console.log('환율 정보 로드 중...');
    const response = await fetch('/api/exchange-rate/');
    const data = await response.json();
    
    if (data.success) {
      currentExchangeRate = data.btc_krw_rate;
      console.log('환율 정보 로드 완료:', currentExchangeRate);
      // 환율 로드 완료 후 가격 변환 정보 업데이트
      updatePriceConversion();
    } else {
      console.error('환율 데이터 로드 실패:', data.error);
    }
  } catch (error) {
    console.error('환율 API 호출 실패:', error);
  } finally {
    isLoadingExchangeRate = false;
  }
}

// 원화를 사토시로 변환
function convertKrwToSats(krwAmount) {
  if (!krwAmount || !currentExchangeRate || krwAmount <= 0) {
    return 0;
  }
  
  // 1 BTC = 100,000,000 사토시
  const btcAmount = krwAmount / currentExchangeRate;
  const satsAmount = btcAmount * 100_000_000;
  return Math.round(satsAmount);
}

// 가격 변환 정보 업데이트
function updatePriceConversion() {
  const priceKrwInput = document.getElementById('price_krw');
  if (!priceKrwInput) return;
  
  const krwValue = parseFloat(priceKrwInput.value);
  const exchangeInfo = document.querySelector('#krw_price_section .exchange-info');
  const convertedAmount = document.querySelector('#krw_price_section .converted-amount');
  
  if (exchangeInfo && convertedAmount) {
    if (krwValue && krwValue > 0 && currentExchangeRate) {
      const satsValue = convertKrwToSats(krwValue);
      convertedAmount.textContent = `약 ${satsValue.toLocaleString()} sats`;
      exchangeInfo.classList.remove('hidden');
    } else {
      exchangeInfo.classList.add('hidden');
    }
  }
}

// 가격 타입 초기화
function initializePriceType() {
  // 무료 옵션이 기본으로 선택되도록 설정
  selectPriceType('free');
}

// 이벤트 리스너 설정
function setupEventListeners() {
  // 정원 제한 체크박스 이벤트
  document.getElementById('no_limit').addEventListener('change', function() {
    const maxParticipantsSection = document.getElementById('max_participants_section');
    const maxParticipantsInput = document.getElementById('max_participants');
    
    if (this.checked) {
      maxParticipantsSection.style.display = 'none';
      maxParticipantsInput.required = false;
      maxParticipantsInput.value = '';
    } else {
      maxParticipantsSection.style.display = 'block';
      maxParticipantsInput.required = true;
    }
    
    // 정원 설정 섹션 검증
    validateCapacitySection();
  });

  // 이미지 업로드 이벤트
  setupImageUpload();

  // 폼 제출 검증
  document.getElementById('liveLectureForm').addEventListener('submit', validateForm);
}

// 실시간 검증 설정
function setupRealTimeValidation() {
  // 기본 정보 필드들
  const nameInput = document.getElementById('name');
  const dateTimeInput = document.getElementById('date_time');
  
  nameInput.addEventListener('input', validateBasicInfoSection);
  nameInput.addEventListener('blur', validateBasicInfoSection);
  
  dateTimeInput.addEventListener('change', validateBasicInfoSection);
  dateTimeInput.addEventListener('blur', validateBasicInfoSection);

  // 에디터 변경 감지
  if (descriptionEditor) {
    descriptionEditor.codemirror.on('change', function() {
      setTimeout(validateBasicInfoSection, 500); // 디바운스
    });
  }

  // 강사 정보 필드들
  const instructorContactInput = document.getElementById('instructor_contact');
  const instructorEmailInput = document.getElementById('instructor_email');
  
  instructorContactInput.addEventListener('input', validateInstructorSection);
  instructorContactInput.addEventListener('blur', validateInstructorSection);
  
  instructorEmailInput.addEventListener('input', validateInstructorSection);
  instructorEmailInput.addEventListener('blur', validateInstructorSection);

  // 가격 필드들
  const priceInput = document.getElementById('price');
  const priceKrwInput = document.getElementById('price_krw');
  
  priceInput.addEventListener('input', validatePriceSection);
  priceInput.addEventListener('blur', validatePriceSection);
  
  if (priceKrwInput) {
    priceKrwInput.addEventListener('input', function() {
      validatePriceSection();
      updatePriceConversion(); // 원화 입력 시 실시간 변환
    });
    priceKrwInput.addEventListener('blur', function() {
      validatePriceSection();
      updatePriceConversion();
    });
  }

  // 정원 필드
  const maxParticipantsInput = document.getElementById('max_participants');
  maxParticipantsInput.addEventListener('input', validateCapacitySection);
  maxParticipantsInput.addEventListener('blur', validateCapacitySection);
}

// 섹션별 검증 함수들
function validateBasicInfoSection() {
  const errors = [];
  
  // 강의명 검증
  const name = document.getElementById('name').value.trim();
  if (!name) {
    errors.push('라이브 강의명을 입력해주세요.');
  }
  
  // 설명 검증
  let description = '';
  try {
    description = descriptionEditor.value().trim();
  } catch (e) {
    description = document.getElementById('description').value.trim();
  }
  if (!description) {
    errors.push('강의 설명을 입력해주세요.');
  }
  
  // 날짜 시간 검증
  const dateTime = document.getElementById('date_time').value;
  if (!dateTime) {
    errors.push('강의 일시를 입력해주세요.');
  }
  
  showSectionErrors('basic-info', errors);
  return errors.length === 0;
}

function validateInstructorSection() {
  const errors = [];
  
  const instructorContact = document.getElementById('instructor_contact').value.trim();
  const instructorEmail = document.getElementById('instructor_email').value.trim();
  
  if (!instructorContact && !instructorEmail) {
    errors.push('강사 연락처 또는 이메일 중 하나는 필수 입력입니다.');
  }
  
  showSectionErrors('instructor', errors);
  return errors.length === 0;
}

function validatePriceSection() {
  const errors = [];
  
  const priceType = document.querySelector('input[name="price_display"]:checked');
  if (!priceType) {
    errors.push('가격 타입을 선택해주세요.');
  } else {
    // 가격 타입별 추가 검증
    if (priceType.value === 'sats') {
      const priceInput = document.getElementById('price');
      const priceValue = parseFloat(priceInput.value);
      if (!priceInput.value || isNaN(priceValue) || priceValue <= 0) {
        errors.push('사토시 가격을 입력해주세요.');
      }
    } else if (priceType.value === 'krw') {
      const priceKrwInput = document.getElementById('price_krw');
      const priceKrwValue = parseFloat(priceKrwInput.value);
      if (!priceKrwInput.value || isNaN(priceKrwValue) || priceKrwValue <= 0) {
        errors.push('원화 가격을 입력해주세요.');
      }
    }
    // 무료 옵션('free')일 때는 추가 검증 없음
  }
  
  showSectionErrors('price', errors);
  return errors.length === 0;
}

function validateCapacitySection() {
  const errors = [];
  
  const noLimit = document.getElementById('no_limit').checked;
  const maxParticipants = document.getElementById('max_participants').value;
  
  if (!noLimit && (!maxParticipants || maxParticipants <= 0)) {
    errors.push('정원을 설정하거나 정원 제한 없음을 체크해주세요.');
  }
  
  showSectionErrors('capacity', errors);
  return errors.length === 0;
}

// 섹션별 에러 표시 함수
function showSectionErrors(sectionName, errors) {
  const errorDiv = document.getElementById(`${sectionName}-errors`);
  const errorList = document.getElementById(`${sectionName}-error-list`);
  
  if (errors.length > 0) {
    errorList.innerHTML = '';
    errors.forEach(error => {
      const li = document.createElement('li');
      li.textContent = `• ${error}`;
      errorList.appendChild(li);
    });
    errorDiv.classList.remove('hidden');
  } else {
    errorDiv.classList.add('hidden');
  }
}

// 전체 검증 함수
function validateAllSections() {
  const basicValid = validateBasicInfoSection();
  const instructorValid = validateInstructorSection();
  const priceValid = validatePriceSection();
  const capacityValid = validateCapacitySection();
  
  return basicValid && instructorValid && priceValid && capacityValid;
}

// 이미지 업로드 관련 이벤트 설정
function setupImageUpload() {
  const imageDropArea = document.getElementById('imageDropArea');
  const imageInput = document.getElementById('images');
  const imagePreview = document.getElementById('imagePreview');
  const previewImg = document.getElementById('previewImg');
  const removeImageBtn = document.getElementById('removeImage');

  imageDropArea.addEventListener('click', () => imageInput.click());
  
  imageDropArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    imageDropArea.classList.add('border-purple-500', 'bg-purple-50', 'dark:bg-purple-900/20');
  });
  
  imageDropArea.addEventListener('dragleave', () => {
    imageDropArea.classList.remove('border-purple-500', 'bg-purple-50', 'dark:bg-purple-900/20');
  });
  
  imageDropArea.addEventListener('drop', (e) => {
    e.preventDefault();
    imageDropArea.classList.remove('border-purple-500', 'bg-purple-50', 'dark:bg-purple-900/20');
    const files = Array.from(e.dataTransfer.files);
    handleImageFiles(files);
  });

  imageInput.addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    handleImageFiles(files);
  });

  removeImageBtn.addEventListener('click', () => {
    imageInput.value = '';
    imagePreview.classList.add('hidden');
    imageDropArea.classList.remove('hidden');
  });
}

// 이미지 파일 처리 (밋업과 동일한 방식)
function handleImageFiles(files) {
  // 1장만 허용
  if (files.length > 1) {
    alert('라이브 강의 이미지는 1장만 업로드할 수 있습니다.');
    return;
  }
  
  const file = files[0];
  if (file && file.type.startsWith('image/')) {
    if (file.size <= 10 * 1024 * 1024) { // 10MB 제한
      handleImageUpload(file);
      updateImageInput(file);
    } else {
      alert('이미지 크기는 10MB 이하여야 합니다.');
    }
  } else {
    alert('이미지 파일만 업로드할 수 있습니다.');
  }
}

// 이미지 업로드 처리
function handleImageUpload(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const previewImg = document.getElementById('previewImg');
    const imagePreview = document.getElementById('imagePreview');
    const imageDropArea = document.getElementById('imageDropArea');
    
    previewImg.src = e.target.result;
    imagePreview.classList.remove('hidden');
    imageDropArea.classList.add('hidden');
  };
  reader.readAsDataURL(file);
}

// 이미지 input 업데이트 (실제 파일이 폼에 포함되도록)
function updateImageInput(file) {
  const imageInput = document.getElementById('images');
  const dt = new DataTransfer();
  dt.items.add(file);
  imageInput.files = dt.files;
}

function selectPriceType(type) {
  // 모든 카드 초기화
  document.querySelectorAll('.price-type-card').forEach(card => {
    card.classList.remove('selected');
  });
  
  // 선택된 카드 활성화
  const selectedCard = document.querySelector(`[onclick="selectPriceType('${type}')"]`);
  if (selectedCard) {
    selectedCard.classList.add('selected');
  }
  
  // 라디오 버튼 선택
  let radioValue;
  if (type === 'free') {
    radioValue = 'free';
  } else if (type === 'sats') {
    radioValue = 'sats';
  } else if (type === 'krw') {
    radioValue = 'krw';
  }
  
  if (radioValue) {
    const radioButton = document.getElementById(`price_display_${radioValue}`);
    if (radioButton) {
      radioButton.checked = true;
    }
  }
  
  // 가격 섹션 표시/숨김
  const satsSection = document.getElementById('sats_price_section');
  const krwSection = document.getElementById('krw_price_section');
  
  if (satsSection) satsSection.classList.add('hidden');
  if (krwSection) krwSection.classList.add('hidden');
  
  // 입력 필드 required 속성 초기화
  const priceInput = document.getElementById('price');
  const priceKrwInput = document.getElementById('price_krw');
  
  if (priceInput) priceInput.required = false;
  if (priceKrwInput) priceKrwInput.required = false;
  
  if (type === 'sats' && satsSection) {
    satsSection.classList.remove('hidden');
    if (priceInput) priceInput.required = true;
  } else if (type === 'krw' && krwSection) {
    krwSection.classList.remove('hidden');
    if (priceKrwInput) {
      priceKrwInput.required = true;
      // 원화 가격 섹션이 표시될 때 변환 정보 업데이트
      updatePriceConversion();
    }
  }
  
  // 가격 검증 업데이트
  validatePriceSection();
}

// 폼 제출 검증
function validateForm(e) {
  console.log('폼 제출 시작 - validateForm 호출됨');
  
  // 폼 제출 전 환율 기반 사토시 값 준비
  prepareFormDataForSubmission();
  
  // EasyMDE 에디터의 내용을 텍스트영역에 저장
  if (descriptionEditor) {
    const descriptionTextarea = document.getElementById('description');
    descriptionTextarea.value = descriptionEditor.value();
  }
  
  if (completionMessageEditor) {
    const completionMessageTextarea = document.getElementById('completion_message');
    completionMessageTextarea.value = completionMessageEditor.value();
  }
  
  // 전체 검증 수행
  const allValid = validateAllSections();
  
  if (!allValid) {
    e.preventDefault();
    console.log('폼 검증 실패 - 제출 중단');
    return false;
  }
  
  console.log('폼 검증 성공 - 제출 진행');
  return true;
}

// 폼 제출 시 원화연동 가격 처리
function prepareFormDataForSubmission() {
  const priceDisplay = document.querySelector('input[name="price_display"]:checked');
  if (!priceDisplay) return;
  
  const form = document.getElementById('liveLectureForm');
  if (!form) return;
  
  // 기존 hidden 필드들 제거
  const existingHiddenFields = form.querySelectorAll('input[type="hidden"][name$="_calculated"]');
  existingHiddenFields.forEach(field => field.remove());
  
  // 가격 필드 처리
  const priceInput = document.getElementById('price');
  const priceKrwInput = document.getElementById('price_krw');
  
  if (priceDisplay.value === 'krw') {
    // 원화연동 모드: 원화 값을 사토시로 변환해서 추가 전송
    if (priceKrwInput && priceKrwInput.value && currentExchangeRate) {
      const krwValue = parseFloat(priceKrwInput.value);
      const satsValue = convertKrwToSats(krwValue);
      
      // 계산된 사토시 값을 hidden field로 추가
      const hiddenSatsField = document.createElement('input');
      hiddenSatsField.type = 'hidden';
      hiddenSatsField.name = 'price_sats_calculated';
      hiddenSatsField.value = satsValue;
      form.appendChild(hiddenSatsField);
      
      // price 필드에 임시값 설정 (폼 검증 통과용)
      if (priceInput) {
        priceInput.value = '1'; // 임시값 설정
      }
      
      console.log(`원화연동 가격 처리: ${krwValue}원 -> ${satsValue}sats`);
    }
  } else if (priceDisplay.value === 'free') {
    // 무료 모드: price 필드를 0으로 설정
    if (priceInput) {
      priceInput.value = '0';
    }
    if (priceKrwInput) {
      priceKrwInput.value = '0';
    }
  } else if (priceDisplay.value === 'sats') {
    // 사토시 모드: price_krw 필드를 0으로 설정
    if (priceKrwInput) {
      priceKrwInput.value = '0';
    }
  }
}

// 디버깅 도우미 함수 추가
function addDebugHelper() {
  if (window.location.hostname === 'localhost' || window.location.hostname.includes('127.0.0.1')) {
    console.log('디버그 모드 활성화');
    window.debugLiveLecture = {
      getFormData: function() {
        const formData = new FormData(document.getElementById('liveLectureForm'));
        const data = {};
        for (let [key, value] of formData.entries()) {
          data[key] = value;
        }
        return data;
      },
      validateAll: validateAllSections,
      getDescriptionValue: () => descriptionEditor ? descriptionEditor.value() : '',
      getCompletionMessageValue: () => completionMessageEditor ? completionMessageEditor.value() : ''
    };
  }
} 