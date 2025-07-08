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
    document.getElementById('no_capacity_limit').addEventListener('change', function() {
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
    const imageInput = document.getElementById('image');
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
    document.getElementById(`price_type_${type}`).checked = true;
    
    // 가격 섹션 표시/숨김
    const satoshiSection = document.getElementById('satoshi_price_section');
    const krwSection = document.getElementById('krw_price_section');
    
    satoshiSection.classList.add('hidden');
    krwSection.classList.add('hidden');
    
    if (type === 'satoshi') {
        satoshiSection.classList.remove('hidden');
        document.getElementById('satoshi_price').required = true;
        document.getElementById('krw_price').required = false;
    } else if (type === 'krw_linked') {
        krwSection.classList.remove('hidden');
        document.getElementById('krw_price').required = true;
        document.getElementById('satoshi_price').required = false;
    } else {
        document.getElementById('satoshi_price').required = false;
        document.getElementById('krw_price').required = false;
    }
}

// 폼 제출 전 검증
function validateForm(e) {
    const priceType = document.querySelector('input[name="price_type"]:checked');
    if (!priceType) {
        e.preventDefault();
        alert('가격 타입을 선택해주세요.');
        return false;
    }
    
    const instructorContact = document.getElementById('instructor_contact').value;
    const instructorEmail = document.getElementById('instructor_email').value;
    
    if (!instructorContact && !instructorEmail) {
        e.preventDefault();
        alert('강사 연락처 또는 이메일 중 하나는 필수 입력입니다.');
        return false;
    }
    
    return true;
}

// 페이지 로드 시 초기 설정
function initializeFormStates() {
    // 가격 타입에 따른 섹션 표시/숨김 설정
    const selectedPriceType = document.querySelector('input[name="price_type"]:checked');
    if (selectedPriceType) {
        selectPriceType(selectedPriceType.value);
    }
    
    // 정원 제한 체크박스 상태에 따른 섹션 표시/숨김 설정
    const noCapacityLimitCheckbox = document.getElementById('no_capacity_limit');
    if (noCapacityLimitCheckbox && noCapacityLimitCheckbox.checked) {
        document.getElementById('max_participants_section').style.display = 'none';
        document.getElementById('max_participants').required = false;
    }
}

// selectPriceType 함수를 전역으로 노출 (HTML에서 onclick으로 호출하기 때문)
window.selectPriceType = selectPriceType; 