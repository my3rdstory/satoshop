// edit-basic-info.js - 기본 정보 편집 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function () {
  // 페이지 데이터 읽기
  const pageData = document.getElementById('page-data');
  const uploadImageUrl = pageData ? pageData.dataset.uploadUrl : '';
  const storeId = pageData ? pageData.dataset.storeId : '';

  // EasyMDE 초기화
  const easyMDE = new EasyMDE({
    element: document.getElementById('store_description'),
    placeholder: '스토어에 대한 설명을 마크다운 형식으로 작성하세요.\n\n예:\n# 스토어 소개\n\n- 신뢰할 수 있는 품질\n- 빠른 배송\n\n## 운영 방침\n\n1. 고객 만족 우선\n2. 정직한 거래',
    spellChecker: false,
    status: false,
    toolbar: [
      'bold', 'italic', 'heading', '|',
      'quote', 'unordered-list', 'ordered-list', '|',
      'link', 'image'
    ]
  });

  // 연락처 입력 검증
  const phoneInput = document.getElementById('owner_phone');
  const emailInput = document.getElementById('owner_email');
  const contactHelp = document.getElementById('contactHelp');

  function validateContact() {
    const hasPhone = phoneInput.value.trim().length > 0;
    const hasEmail = emailInput.value.trim().length > 0;

    if (!hasPhone && !hasEmail) {
      contactHelp.className = 'mt-2 text-sm text-red-600 dark:text-red-400';
      contactHelp.textContent = '휴대전화 또는 이메일 중 하나는 반드시 입력해야 합니다.';
      return false;
    } else {
      contactHelp.className = 'mt-2 text-sm text-green-600 dark:text-green-400';
      contactHelp.textContent = '연락처가 올바르게 입력되었습니다.';
      return true;
    }
  }

  phoneInput.addEventListener('input', validateContact);
  emailInput.addEventListener('input', validateContact);

  // 초기 검증
  validateContact();

  // 폼 제출 검증
  document.getElementById('basicInfoForm').addEventListener('submit', function (e) {
    const descriptionValue = easyMDE.value().trim();
    // 스토어 설명은 선택사항이므로 필수 검증 제거

    if (!validateContact()) {
      e.preventDefault();
      alert('연락처를 확인해주세요.');
      return false;
    }

    // 필수 필드 검증
    const storeName = document.getElementById('store_name').value.trim();
    const ownerName = document.getElementById('owner_name').value.trim();
    const chatChannel = document.getElementById('chat_channel').value.trim();

    if (!storeName || !ownerName || !chatChannel) {
      e.preventDefault();
      alert('필수 입력 항목을 모두 입력해주세요.');
      return false;
    }
  });

  // === 이미지 업로드 관련 기능 ===
  let selectedFiles = [];
  const fileInput = document.getElementById('store_images');
  const fileName = document.getElementById('fileName');
  const uploadArea = document.getElementById('imageUploadArea');
  const imagePreview = document.getElementById('imagePreview');
  const previewContainer = document.getElementById('previewContainer');
  const uploadBtn = document.getElementById('uploadBtn');
  const cancelUploadBtn = document.getElementById('cancelUploadBtn');
  const uploadProgress = document.getElementById('uploadProgress');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');

  // 업로드 영역 클릭 시 파일 선택
  uploadArea.addEventListener('click', function() {
    fileInput.click();
  });

  // 파일 선택 이벤트
  fileInput.addEventListener('change', function (e) {
    handleFileSelection(e.target.files);
  });

  // 드래그 앤 드롭 이벤트
  uploadArea.addEventListener('dragover', function (e) {
    e.preventDefault();
    uploadArea.classList.add('border-blue-400', 'dark:border-blue-500', 'bg-blue-50', 'dark:bg-blue-900');
  });

  uploadArea.addEventListener('dragleave', function (e) {
    e.preventDefault();
    uploadArea.classList.remove('border-blue-400', 'dark:border-blue-500', 'bg-blue-50', 'dark:bg-blue-900');
  });

  uploadArea.addEventListener('drop', function (e) {
    e.preventDefault();
    uploadArea.classList.remove('border-blue-400', 'dark:border-blue-500', 'bg-blue-50', 'dark:bg-blue-900');

    const files = Array.from(e.dataTransfer.files).filter(file =>
      file.type.startsWith('image/')
    );

    if (files.length > 0) {
      handleFileSelection(files);
    }
  });

  // 파일 선택 처리
  function handleFileSelection(files) {
    const imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));

    if (imageFiles.length === 0) {
      alert('이미지 파일만 업로드할 수 있습니다.');
      return;
    }

    if (imageFiles.length > 1) {
      alert('스토어 대표 이미지는 1장만 업로드할 수 있습니다.');
      return;
    }

    selectedFiles = imageFiles;

    // 파일명 표시
    fileName.textContent = selectedFiles[0].name;
    fileName.className = 'text-sm text-green-600 dark:text-green-400';

    // 미리보기 생성
    showImagePreviews();
  }

  // 이미지 미리보기 표시
  function showImagePreviews() {
    previewContainer.innerHTML = '';

    // 단일 파일만 처리
    const file = selectedFiles[0];
    const reader = new FileReader();
    reader.onload = function (e) {
      const div = document.createElement('div');
      div.className = 'bg-white dark:bg-gray-700 rounded-lg shadow-md overflow-hidden border border-gray-200 dark:border-gray-600';
      div.innerHTML = `
        <div class="aspect-video">
          <img src="${e.target.result}" alt="${file.name}" class="w-full h-full object-cover">
        </div>
        <div class="p-3">
          <p class="text-xs text-gray-600 dark:text-gray-400 truncate">${file.name}</p>
          <p class="text-xs text-gray-500 dark:text-gray-500 mb-2">${formatFileSize(file.size)}</p>
          <button type="button" id="removePreviewBtn" class="w-full px-3 py-2 bg-gray-500 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors flex items-center justify-center gap-2">
            <i class="fas fa-times text-xs"></i>
            <span>제거</span>
          </button>
        </div>
      `;
      previewContainer.appendChild(div);
      
      // 제거 버튼 이벤트 리스너 추가
      div.querySelector('#removePreviewBtn').addEventListener('click', removePreviewFile);
    };
    reader.readAsDataURL(file);

    imagePreview.classList.remove('hidden');
  }

  // 미리보기에서 파일 제거
  function removePreviewFile() {
    selectedFiles = [];
    imagePreview.classList.add('hidden');
    fileName.textContent = '파일을 선택하지 않았습니다';
    fileName.className = 'text-sm text-gray-500 dark:text-gray-500';
    fileInput.value = '';
  }

  // 업로드 버튼 클릭
  uploadBtn.addEventListener('click', function () {
    if (selectedFiles.length === 0) {
      alert('업로드할 이미지를 선택해주세요.');
      return;
    }

    uploadImage();
  });

  // 업로드 취소
  cancelUploadBtn.addEventListener('click', function () {
    removePreviewFile();
  });

  // 단일 이미지 업로드 실행
  async function uploadImage() {
    uploadProgress.classList.remove('hidden');
    uploadBtn.disabled = true;
    cancelUploadBtn.disabled = true;

    const file = selectedFiles[0];
    const formData = new FormData();
    formData.append('image', file);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

    try {
      progressText.textContent = '이미지 업로드 중...';
      progressBar.style.width = '50%';

      const response = await fetch(uploadImageUrl, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.success) {
        progressBar.style.width = '100%';
        progressText.textContent = '업로드 완료!';

        // 기존 이미지 목록 완전히 교체
        replaceCurrentImage(result.image);
      } else {
        console.error('업로드 실패:', result.error);
        alert(`업로드에 실패했습니다: ${result.error}`);
      }

    } catch (error) {
      console.error('업로드 오류:', error);
      alert('업로드 중 오류가 발생했습니다.');
    }

    setTimeout(() => {
      uploadProgress.classList.add('hidden');
      uploadBtn.disabled = false;
      cancelUploadBtn.disabled = false;

      // 업로드 영역 초기화
      removePreviewFile();
    }, 1500);
  }

  // 현재 이미지를 새 이미지로 교체
  function replaceCurrentImage(imageData) {
    const currentImages = document.getElementById('currentImages');
    
    // 기존 이미지 목록 완전히 교체
    currentImages.innerHTML = `
      <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">현재 업로드된 이미지</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div class="bg-white dark:bg-gray-700 rounded-lg shadow-md overflow-hidden border border-gray-200 dark:border-gray-600" id="image-${imageData.id}">
          <div class="aspect-video">
            <img src="${imageData.file_url}" alt="${imageData.original_name}" loading="lazy" class="w-full h-full object-cover">
          </div>
          <div class="p-3">
            <p class="text-xs text-gray-600 dark:text-gray-400 truncate">${imageData.original_name}</p>
            <p class="text-xs text-gray-500 dark:text-gray-500 mb-2">${formatFileSize(imageData.file_size)}</p>
            <button type="button" data-image-id="${imageData.id}" class="delete-image-btn w-full px-3 py-2 bg-red-500 hover:bg-red-600 text-white text-sm rounded-lg transition-colors flex items-center justify-center gap-2">
              <i class="fas fa-trash text-xs"></i>
              <span>삭제</span>
            </button>
          </div>
        </div>
      </div>
    `;

    // 새로운 삭제 버튼에 이벤트 리스너 추가
    const newDeleteBtn = currentImages.querySelector('.delete-image-btn');
    if (newDeleteBtn) {
      newDeleteBtn.addEventListener('click', handleDeleteImage);
    }

    // 메시지 숨기기
    const noImagesMessage = document.getElementById('noImagesMessage');
    if (noImagesMessage) {
      noImagesMessage.style.display = 'none';
    }
  }

  // 이미지 삭제 핸들러
  function handleDeleteImage(event) {
    const imageId = event.currentTarget.getAttribute('data-image-id');
    deleteImage(imageId);
  }

  // 기존 삭제 버튼들에 이벤트 리스너 추가
  document.querySelectorAll('.delete-image-btn').forEach(btn => {
    btn.addEventListener('click', handleDeleteImage);
  });

  // 이미지 삭제
  async function deleteImage(imageId) {
    if (!confirm('이 이미지를 삭제하시겠습니까?')) {
      return;
    }

    try {
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      const deleteUrl = `/stores/edit/${storeId}/delete-image/${imageId}/`;
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

        // 이미지가 모두 삭제되면 메시지 표시
        const remainingImages = document.querySelectorAll('[id^="image-"]');
        if (remainingImages.length === 0) {
          const currentImages = document.getElementById('currentImages');
          currentImages.innerHTML = `
            <div class="text-center py-12 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600" id="noImagesMessage">
              <i class="fas fa-images text-4xl text-gray-300 dark:text-gray-600 mb-4"></i>
              <p class="text-gray-500 dark:text-gray-400">아직 업로드된 이미지가 없습니다.</p>
            </div>
          `;
        }
      } else {
        alert('이미지 삭제에 실패했습니다: ' + result.error);
      }
    } catch (error) {
      console.error('삭제 오류:', error);
      alert('이미지 삭제 중 오류가 발생했습니다.');
    }
  }

  // 파일 크기 포맷팅
  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
}); 