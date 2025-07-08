// lecture_live_add.js
// 라이브 강의 추가 페이지 JavaScript

// EasyMDE 에디터 변수들
let descriptionEditor;
let completionMessageEditor;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
  initializeEditors();
  initializePriceType();
  setupEventListeners();
  setupRealTimeValidation();
  addDebugHelper();
  console.log('라이브 강의 추가 페이지 로드 완료');
});

// EasyMDE 에디터 초기화
function initializeEditors() {
  descriptionEditor = new EasyMDE({
    element: document.getElementById('description'),
    spellChecker: false,
    toolbar: ['bold', 'italic', 'strikethrough', '|', 'heading-1', 'heading-2', 'heading-3', '|', 'unordered-list', 'ordered-list', '|', 'link', 'quote', 'code'],
    placeholder: '강의에 대한 자세한 설명을 작성하세요...'
  });

  completionMessageEditor = new EasyMDE({
    element: document.getElementById('completion_message'),
    spellChecker: false,
    toolbar: ['bold', 'italic', '|', 'heading-2', 'heading-3', '|', 'unordered-list', 'ordered-list', '|', 'link', 'quote', 'code'],
    placeholder: '참가 완료 후 보여줄 메시지를 작성하세요...'
  });
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
  
  priceKrwInput.addEventListener('input', validatePriceSection);
  priceKrwInput.addEventListener('blur', validatePriceSection);

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
  const errorContainer = document.getElementById(`${sectionName}-errors`);
  const errorList = document.getElementById(`${sectionName}-error-list`);
  
  if (errors.length > 0) {
    errorList.innerHTML = errors.map(error => `<li>• ${error}</li>`).join('');
    errorContainer.classList.remove('hidden');
  } else {
    errorContainer.classList.add('hidden');
  }
}

// 모든 섹션 검증
function validateAllSections() {
  const basicInfoValid = validateBasicInfoSection();
  const instructorValid = validateInstructorSection();
  const priceValid = validatePriceSection();
  const capacityValid = validateCapacitySection();
  
  return basicInfoValid && instructorValid && priceValid && capacityValid;
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
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleImageUpload(files[0]);
    }
  });

  imageInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleImageUpload(e.target.files[0]);
    }
  });

  removeImageBtn.addEventListener('click', () => {
    imageInput.value = '';
    imagePreview.classList.add('hidden');
    imageDropArea.classList.remove('hidden');
  });
}

// 이미지 업로드 처리
function handleImageUpload(file) {
  if (file.type.startsWith('image/')) {
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
  } else {
    alert('이미지 파일만 업로드 가능합니다.');
  }
}

// 가격 타입 선택 함수
function selectPriceType(type) {
  // 모든 카드 초기화
  document.querySelectorAll('.price-type-card').forEach(card => {
    card.classList.remove('selected');
  });
  
  // 선택된 카드 활성화
  document.querySelector(`[onclick="selectPriceType('${type}')"]`).classList.add('selected');
  
  // 라디오 버튼 선택
  document.getElementById(`price_display_${type}`).checked = true;
  
  // 가격 섹션 표시/숨김
  const satoshiSection = document.getElementById('sats_price_section');
  const krwSection = document.getElementById('krw_price_section');
  const priceInput = document.getElementById('price');
  const priceKrwInput = document.getElementById('price_krw');
  
  satoshiSection.classList.add('hidden');
  krwSection.classList.add('hidden');
  
  // 모든 가격 필드 초기화 및 required 속성 제거
  priceInput.required = false;
  priceKrwInput.required = false;
  
  if (type === 'sats') {
    satoshiSection.classList.remove('hidden');
    priceInput.required = true;
    priceInput.value = '';
    priceKrwInput.value = '';
  } else if (type === 'krw') {
    krwSection.classList.remove('hidden');
    priceKrwInput.required = true;
    priceInput.value = '';
    priceKrwInput.value = '';
  } else {
    // 무료 옵션일 때는 필드를 비워둠 (폼 제출 시 0으로 설정됨)
    priceInput.value = '';
    priceKrwInput.value = '';
  }
  
  // 가격 섹션 검증
  setTimeout(() => {
    validatePriceSection();
  }, 100);
}

// 폼 제출 전 검증
function validateForm(e) {
  console.log('폼 제출 시도 시작');
  
  // 가격 타입에 따라 숨겨진 필드 값 설정
  const priceType = document.querySelector('input[name="price_display"]:checked');
  if (priceType) {
    const priceInput = document.getElementById('price');
    const priceKrwInput = document.getElementById('price_krw');
    
    if (priceType.value === 'free') {
      // 무료일 때 두 필드 모두 0으로 설정
      priceInput.value = '0';
      priceKrwInput.value = '0';
    } else if (priceType.value === 'sats') {
      // 사토시 가격일 때 원화 필드는 0으로 설정
      priceKrwInput.value = '0';
    } else if (priceType.value === 'krw') {
      // 원화 가격일 때 사토시 필드는 0으로 설정
      priceInput.value = '0';
    }
  }
  
  // 디버깅: 모든 폼 데이터 출력
  const formData = new FormData(this);
  console.log('폼 데이터:');
  for (let [key, value] of formData.entries()) {
    console.log(`${key}: ${value}`);
  }
  
  // 모든 섹션 검증
  const isValid = validateAllSections();
  
  if (!isValid) {
    e.preventDefault();
    console.log('검증 실패 - 각 섹션의 에러 메시지를 확인하세요');
    
    // 첫 번째 에러가 있는 섹션으로 스크롤
    const firstErrorSection = document.querySelector('.bg-red-50:not(.hidden)');
    if (firstErrorSection) {
      firstErrorSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    return false;
  }
  
  console.log('클라이언트 측 검증 통과 - 서버로 제출합니다');
  return true;
}

// 디버깅 도우미 함수 추가
function addDebugHelper() {
  // 디버깅 도우미 함수
  window.debugForm = function() {
    console.log('=== 폼 디버깅 정보 ===');
    console.log('강의명:', document.getElementById('name').value);
    console.log('설명:', document.getElementById('description').value);
    console.log('일시:', document.getElementById('date_time').value);
    console.log('가격 타입:', document.querySelector('input[name="price_display"]:checked')?.value);
    console.log('사토시 가격:', document.getElementById('price').value);
    console.log('원화 가격:', document.getElementById('price_krw').value);
    console.log('강사 연락처:', document.getElementById('instructor_contact').value);
    console.log('강사 이메일:', document.getElementById('instructor_email').value);
    console.log('정원 제한 없음:', document.getElementById('no_limit').checked);
    console.log('최대 참가자:', document.getElementById('max_participants').value);
    console.log('==================');
  };
  
  console.log('디버깅 도우미: 콘솔에서 debugForm()을 입력하면 현재 폼 상태를 확인할 수 있습니다.');
}

// selectPriceType 함수를 전역으로 노출 (HTML에서 onclick으로 호출하기 때문)
window.selectPriceType = selectPriceType; 