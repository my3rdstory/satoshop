// lecture_live_edit.js
// 라이브 강의 수정 페이지 JavaScript

// EasyMDE 에디터 변수들
let descriptionEditor;
let completionMessageEditor;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeEditors();
    setupEventListeners();
    initializeFormStates();
});

// EasyMDE 에디터 초기화
function initializeEditors() {
    const descriptionElement = document.getElementById('description');
    const completionMessageElement = document.getElementById('completion_message');
    
    descriptionEditor = new EasyMDE({
        element: descriptionElement,
        spellChecker: false,
        toolbar: ['bold', 'italic', 'strikethrough', '|', 'heading-1', 'heading-2', 'heading-3', '|', 'unordered-list', 'ordered-list', '|', 'link', 'quote', 'code'],
        placeholder: '강의에 대한 자세한 설명을 작성하세요...',
        initialValue: descriptionElement.value || ''
    });

    completionMessageEditor = new EasyMDE({
        element: completionMessageElement,
        spellChecker: false,
        toolbar: ['bold', 'italic', '|', 'heading-2', 'heading-3', '|', 'unordered-list', 'ordered-list', '|', 'link', 'quote', 'code'],
        placeholder: '참가 완료 후 보여줄 메시지를 작성하세요...',
        initialValue: completionMessageElement.value || ''
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

    // 이미지 변경 버튼 이벤트
    const changeImageBtn = document.getElementById('changeImageBtn');
    const currentImage = document.getElementById('currentImage');
    const imageDropArea = document.getElementById('imageDropArea');

    if (changeImageBtn) {
        changeImageBtn.addEventListener('click', () => {
            currentImage.classList.add('hidden');
            imageDropArea.classList.remove('hidden');
        });
    }

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
    const radioValue = type === 'satoshi' ? 'sats' : (type === 'krw_linked' ? 'krw' : 'free');
    document.getElementById(`price_display_${radioValue}`).checked = true;
    
    // 가격 섹션 표시/숨김
    const satoshiSection = document.getElementById('satoshi_price_section');
    const krwSection = document.getElementById('krw_price_section');
    
    satoshiSection.classList.add('hidden');
    krwSection.classList.add('hidden');
    
    if (type === 'satoshi') {
        satoshiSection.classList.remove('hidden');
        document.getElementById('price').required = true;
        document.getElementById('price_krw').required = false;
    } else if (type === 'krw_linked') {
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
    console.log('폼 제출 시작 - validateForm 호출됨');
    
    // EasyMDE 에디터의 내용을 텍스트영역에 저장
    if (descriptionEditor) {
        const description = descriptionEditor.value();
        document.getElementById('description').value = description;
        console.log('Description 값 설정:', description);
    }
    if (completionMessageEditor) {
        const completionMessage = completionMessageEditor.value();
        document.getElementById('completion_message').value = completionMessage;
        console.log('Completion message 값 설정:', completionMessage);
    }
    
    const priceType = document.querySelector('input[name="price_display"]:checked');
    if (!priceType) {
        e.preventDefault();
        alert('가격 타입을 선택해주세요.');
        console.log('폼 제출 실패: 가격 타입 미선택');
        return false;
    }
    console.log('선택된 가격 타입:', priceType.value);
    
    // 가격 타입에 따라 숨겨진 필드들에 기본값 설정
    const priceInput = document.getElementById('price');
    const priceKrwInput = document.getElementById('price_krw');
    
    if (priceType.value === 'free') {
        // 무료인 경우 모든 가격 필드를 0으로 설정
        priceInput.value = '0';
        priceKrwInput.value = '0';
        console.log('무료 강의 - 가격 필드들을 0으로 설정');
    } else if (priceType.value === 'sats') {
        // 사토시인 경우 원화 가격을 0으로 설정
        priceKrwInput.value = '0';
        // 사토시 가격이 비어있으면 0으로 설정
        if (!priceInput.value || priceInput.value.trim() === '') {
            priceInput.value = '0';
        }
        console.log('사토시 강의 - 원화 가격을 0으로 설정, 사토시 가격:', priceInput.value);
    } else if (priceType.value === 'krw') {
        // 원화인 경우 사토시 가격을 0으로 설정
        priceInput.value = '0';
        // 원화 가격이 비어있으면 0으로 설정
        if (!priceKrwInput.value || priceKrwInput.value.trim() === '') {
            priceKrwInput.value = '0';
        }
                 console.log('원화 강의 - 사토시 가격을 0으로 설정, 원화 가격:', priceKrwInput.value);
     }
     
     // 할인 관련 필드들도 기본값 설정
     const discountedPriceInput = document.getElementById('discounted_price');
     const discountedPriceKrwInput = document.getElementById('discounted_price_krw');
     
     if (discountedPriceInput && (!discountedPriceInput.value || discountedPriceInput.value.trim() === '')) {
         discountedPriceInput.value = '0';
     }
     if (discountedPriceKrwInput && (!discountedPriceKrwInput.value || discountedPriceKrwInput.value.trim() === '')) {
         discountedPriceKrwInput.value = '0';
     }
     
     // 정원 관련 필드 처리
     const noLimitCheckbox = document.getElementById('no_limit');
     const maxParticipantsInput = document.getElementById('max_participants');
     
     if (noLimitCheckbox && noLimitCheckbox.checked) {
         // 정원 제한이 없는 경우 max_participants를 null로 처리하기 위해 빈 값으로 설정
         if (maxParticipantsInput) {
             maxParticipantsInput.value = '';
         }
         console.log('정원 제한 없음 - max_participants를 빈 값으로 설정');
     } else if (maxParticipantsInput && (!maxParticipantsInput.value || maxParticipantsInput.value.trim() === '')) {
         // 정원 제한이 있는데 값이 비어있으면 에러
         e.preventDefault();
         alert('정원을 설정하거나 정원 없음을 체크해주세요.');
         console.log('폼 제출 실패: 정원 미설정');
         return false;
     }
     
     console.log('최종 가격 설정 - price:', priceInput.value, 'price_krw:', priceKrwInput.value);
     
     const instructorContact = document.getElementById('instructor_contact').value;
    const instructorEmail = document.getElementById('instructor_email').value;
    
    if (!instructorContact && !instructorEmail) {
        e.preventDefault();
        alert('강사 연락처 또는 이메일 중 하나는 필수 입력입니다.');
        console.log('폼 제출 실패: 강사 연락처/이메일 미입력');
        return false;
    }
    
    console.log('폼 검증 통과 - 제출 계속 진행');
    return true;
}

// 페이지 로드 시 초기 설정
function initializeFormStates() {
    // 가격 타입에 따른 섹션 표시/숨김 설정
    const selectedPriceType = document.querySelector('input[name="price_display"]:checked');
    if (selectedPriceType) {
        // 선택된 값에 따라 올바른 타입으로 변환
        const type = selectedPriceType.value === 'sats' ? 'satoshi' : (selectedPriceType.value === 'krw' ? 'krw_linked' : 'free');
        selectPriceType(type);
    }
    
    // 정원 제한 체크박스 상태에 따른 섹션 표시/숨김 설정
    const noLimitCheckbox = document.getElementById('no_limit');
    if (noLimitCheckbox && noLimitCheckbox.checked) {
        document.getElementById('max_participants_section').style.display = 'none';
        document.getElementById('max_participants').required = false;
    }
}

// selectPriceType 함수를 전역으로 노출 (HTML에서 onclick으로 호출하기 때문)
window.selectPriceType = selectPriceType; 