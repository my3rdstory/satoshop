document.addEventListener('DOMContentLoaded', function () {
  // EasyMDE 초기화
  const easyMDE = new EasyMDE({
    element: document.getElementById('description'),
    placeholder: '상품에 대한 자세한 설명을 마크다운 형식으로 작성하세요.\n\n예:\n# 상품 특징\n\n- 고품질 소재 사용\n- 친환경 제품\n\n## 사용법\n\n1. 단계별 설명\n2. 주의사항',
    spellChecker: false,
    status: false,
    toolbar: [
      'bold', 'italic', 'heading', '|',
      'quote', 'unordered-list', 'ordered-list', '|',
      'link', 'image', '|',
      'preview', 'side-by-side', 'fullscreen', '|',
      'guide'
    ]
  });

  // 이미지 업로드 관련
  const imageDropArea = document.getElementById('imageDropArea');
  const imageInput = document.getElementById('imageInput');
  const imagePreview = document.getElementById('imagePreview');

  // 드래그 앤 드롭 이벤트
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    imageDropArea.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(eventName => {
    imageDropArea.addEventListener(eventName, highlight, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    imageDropArea.addEventListener(eventName, unhighlight, false);
  });

  function highlight(e) {
    imageDropArea.classList.add('dragover');
  }

  function unhighlight(e) {
    imageDropArea.classList.remove('dragover');
  }

  imageDropArea.addEventListener('drop', handleDrop, false);

  function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
  }

  imageDropArea.addEventListener('click', () => {
    imageInput.click();
  });

  imageInput.addEventListener('change', function () {
    handleFiles(this.files);
  });

  function handleFiles(files) {
    const imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));

    if (imageFiles.length === 0) {
      alert('이미지 파일만 업로드할 수 있습니다.');
      return;
    }

    // 현재 이미지 개수 확인
    const currentImages = document.getElementById('currentImages');
    const currentImageCount = currentImages ? currentImages.querySelectorAll('.column').length : 0;
    if (currentImageCount + imageFiles.length > 10) {
      alert('상품당 최대 10개의 이미지만 업로드할 수 있습니다.');
      return;
    }

    // 파일 크기 검증 (각각 10MB)
    for (let file of imageFiles) {
      if (file.size > 10 * 1024 * 1024) {
        alert(`${file.name} 파일이 너무 큽니다. (최대 10MB)`);
        return;
      }
    }

    // 각 파일을 즉시 업로드
    imageFiles.forEach(file => {
      uploadImageToServer(file);
    });
  }

  // 서버에 이미지 업로드
  async function uploadImageToServer(file) {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

    try {
      // 업로드 진행 표시
      const progressDiv = showUploadProgress(file.name);
      
      // URL을 동적으로 구성해야 하는 경우를 위한 처리
      const uploadUrl = window.uploadImageUrl || '/products/upload-image/';
      
      const response = await fetch(uploadUrl, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      // 진행 표시 제거
      progressDiv.remove();

      if (result.success) {
        // 성공한 이미지를 현재 이미지 목록에 추가
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

  // 업로드 진행 표시
  function showUploadProgress(fileName) {
    const progressDiv = document.createElement('div');
    progressDiv.className = 'column is-one-quarter';
    progressDiv.innerHTML = `
      <div class="card">
        <div class="card-content">
          <div class="has-text-centered">
            <div class="is-loading loading-container">
              <span class="icon">
                <i class="fas fa-spinner fa-spin"></i>
              </span>
            </div>
            <p class="is-size-7 has-text-grey mt-2">업로드 중...</p>
            <p class="is-size-7 has-text-grey">${fileName}</p>
          </div>
        </div>
      </div>
    `;
    
    let currentImages = document.getElementById('currentImages');
    
    // currentImages 요소가 없으면 생성
    if (!currentImages) {
      const imageField = document.querySelector('#imageDropArea').closest('.field');
      const currentImagesSection = document.createElement('div');
      currentImagesSection.innerHTML = `
        <div class="field">
          <label class="label">현재 상품 이미지</label>
          <div class="columns is-multiline" id="currentImages"></div>
        </div>
      `;
      imageField.insertAdjacentElement('beforebegin', currentImagesSection);
      currentImages = document.getElementById('currentImages');
    }
    
    currentImages.appendChild(progressDiv);
    return progressDiv;
  }

  // 현재 이미지 목록에 새 이미지 추가
  function addImageToCurrentList(imageData) {
    let currentImages = document.getElementById('currentImages');

    // currentImages 요소가 없으면 생성
    if (!currentImages) {
      const imageField = document.querySelector('#imageDropArea').closest('.field');
      const currentImagesSection = document.createElement('div');
      currentImagesSection.innerHTML = `
        <div class="field">
          <label class="label">현재 상품 이미지</label>
          <div class="columns is-multiline" id="currentImages"></div>
        </div>
      `;
      imageField.insertAdjacentElement('beforebegin', currentImagesSection);
      currentImages = document.getElementById('currentImages');
    }

    const div = document.createElement('div');
    div.className = 'column is-one-quarter';
    div.id = `image-${imageData.id}`;
    div.innerHTML = `
      <div class="card">
        <div class="card-image">
          <figure class="image is-square">
            <img src="${imageData.file_url}" alt="${imageData.original_name}" loading="lazy">
          </figure>
        </div>
        <div class="card-content p-2">
          <p class="is-size-7 has-text-grey">${imageData.original_name}</p>
          <p class="is-size-7 has-text-grey">${formatFileSize(imageData.file_size)}</p>
          <button type="button" class="button is-danger is-small is-fullwidth mt-2" onclick="deleteExistingImage(${imageData.id})">
            <span class="icon is-small">
              <i class="fas fa-trash"></i>
            </span>
            <span>삭제</span>
          </button>
        </div>
      </div>
    `;

    currentImages.appendChild(div);
  }

  // 기존 이미지 삭제
  window.deleteExistingImage = async function (imageId) {
    if (!confirm('이 이미지를 삭제하시겠습니까?')) {
      return;
    }

    try {
      // URL을 동적으로 구성해야 하는 경우를 위한 처리
      const deleteUrl = window.deleteImageUrl ? window.deleteImageUrl.replace('0', imageId) : `/products/delete-image/${imageId}/`;
      
      const response = await fetch(deleteUrl, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
          'Content-Type': 'application/json'
        }
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

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // 폼 제출 시 유효성 검사
  document.getElementById('productForm').addEventListener('submit', function (e) {
    const descriptionValue = easyMDE.value().trim();
    if (!descriptionValue) {
      e.preventDefault();
      alert('상품 설명을 입력해주세요.');
      easyMDE.codemirror.focus();
      return false;
    }
  });

  // 상품 폼 초기화
  if (typeof window.initProductForm === 'function') {
    // 현재 옵션 개수를 전역 변수에서 가져오거나 동적으로 계산
    const optionCount = window.productOptionsCount || document.querySelectorAll('.option-section').length;
    window.initProductForm(true, optionCount);
  }
}); 