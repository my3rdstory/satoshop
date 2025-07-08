// lecture_live_add.js
// 라이브 강의 추가 페이지 JavaScript

// EasyMDE 에디터 변수들
let descriptionEditor;
let completionMessageEditor;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
  initializeEditors();
  selectPriceType('free');
  setupEventListeners();
  addDebugHelper();
  console.log('라이브 강의 추가 페이지 로드 완료');
});

// EasyMDE 에디터 초기화
function initializeEditors() {
  descriptionEditor = new EasyMDE({
    element: document.getElementById('description'),
    spellChecker: false,
    toolbar: ['bold', 'italic', 'strikethrough', '|', 'heading-1', 'heading-2', 'heading-3', '|', 'unordered-list', 'ordered-list', '|', 'link', 'quote', 'code', '|', 'preview', 'side-by-side', 'fullscreen', '|', 'guide'],
    placeholder: '강의에 대한 자세한 설명을 작성하세요...'
  });

  completionMessageEditor = new EasyMDE({
    element: document.getElementById('completion_message'),
    spellChecker: false,
    toolbar: ['bold', 'italic', '|', 'heading-2', 'heading-3', '|', 'unordered-list', 'ordered-list', '|', 'link', 'quote', 'code', '|', 'preview', 'side-by-side', 'fullscreen'],
    placeholder: '참가 완료 후 보여줄 메시지를 작성하세요...'
  });
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
    } else {
      maxParticipantsSection.style.display = 'block';
      maxParticipantsInput.required = true;
    }
  });

  // 이미지 업로드 이벤트
  setupImageUpload();

  // 폼 제출 검증
  document.getElementById('liveLectureForm').addEventListener('submit', validateForm);
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
  
  satoshiSection.classList.add('hidden');
  krwSection.classList.add('hidden');
  
  if (type === 'sats') {
    satoshiSection.classList.remove('hidden');
    document.getElementById('price').required = true;
    document.getElementById('price_krw').required = false;
  } else if (type === 'krw') {
    krwSection.classList.remove('hidden');
    document.getElementById('price_krw').required = true;
    document.getElementById('price').required = false;
  } else {
    document.getElementById('price').required = false;
    document.getElementById('price_krw').required = false;
  }
}

// 폼 제출 전 검증
function validateForm(e) {
  console.log('폼 제출 시도 시작');
  const errors = [];
  
  // 디버깅: 모든 폼 데이터 출력
  const formData = new FormData(this);
  console.log('폼 데이터:');
  for (let [key, value] of formData.entries()) {
    console.log(`${key}: ${value}`);
  }
  
  // 1. 필수 항목 검증
  const name = document.getElementById('name').value.trim();
  if (!name) {
    errors.push('라이브 강의명을 입력해주세요.');
  }
  
  let description = '';
  try {
    description = descriptionEditor.value().trim();
  } catch (e) {
    description = document.getElementById('description').value.trim();
  }
  if (!description) {
    errors.push('강의 설명을 입력해주세요.');
  }
  
  const dateTime = document.getElementById('date_time').value;
  if (!dateTime) {
    errors.push('강의 일시를 입력해주세요.');
  }
  
  // 2. 가격 타입 검증
  const priceType = document.querySelector('input[name="price_display"]:checked');
  if (!priceType) {
    errors.push('가격 타입을 선택해주세요.');
  } else {
    // 가격 타입별 추가 검증
    if (priceType.value === 'sats') {
      const priceInput = document.getElementById('price');
      if (!priceInput.value || priceInput.value <= 0) {
        errors.push('사토시 가격을 입력해주세요.');
      }
    } else if (priceType.value === 'krw') {
      const priceKrwInput = document.getElementById('price_krw');
      if (!priceKrwInput.value || priceKrwInput.value <= 0) {
        errors.push('원화 가격을 입력해주세요.');
      }
    }
  }
  
  // 3. 강사 연락처 검증
  const instructorContact = document.getElementById('instructor_contact').value.trim();
  const instructorEmail = document.getElementById('instructor_email').value.trim();
  
  if (!instructorContact && !instructorEmail) {
    errors.push('강사 연락처 또는 이메일 중 하나는 필수 입력입니다.');
  }
  
  // 4. 정원 검증
  const noLimit = document.getElementById('no_limit').checked;
  const maxParticipants = document.getElementById('max_participants').value;
  
  if (!noLimit && (!maxParticipants || maxParticipants <= 0)) {
    errors.push('정원을 설정하거나 정원 제한 없음을 체크해주세요.');
  }
  
  // 에러가 있으면 폼 제출 중단
  if (errors.length > 0) {
    e.preventDefault();
    console.log('검증 실패 - 에러 목록:', errors);
    alert('다음 항목을 확인해주세요:\n\n' + errors.join('\n'));
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