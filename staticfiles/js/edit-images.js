document.addEventListener('DOMContentLoaded', function () {
  // 페이지 데이터 읽기
  const pageData = document.getElementById('page-data');
  const uploadImageUrl = pageData ? pageData.dataset.uploadUrl : '';
  const storeId = pageData ? pageData.dataset.storeId : '';
  const productId = pageData ? pageData.dataset.productId : '';

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
    imageDropArea.classList.add('border-blue-400', 'dark:border-blue-500', 'bg-blue-50', 'dark:bg-blue-900');
  }

  function unhighlight(e) {
    imageDropArea.classList.remove('border-blue-400', 'dark:border-blue-500', 'bg-blue-50', 'dark:bg-blue-900');
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
    const currentImageCount = currentImages ? currentImages.querySelectorAll('[id^="image-"]').length : 0;
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
      
      const response = await fetch(uploadImageUrl, {
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
    
    // currentImages 요소가 없으면 생성하지 않고 기존 구조 사용
    if (currentImages) {
      currentImages.appendChild(progressDiv);
    }
    
    return progressDiv;
  }

  // 현재 이미지 목록에 새 이미지 추가
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
          <button type="button" onclick="deleteExistingImage(${imageData.id})"
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

  // 기존 이미지 삭제
  window.deleteExistingImage = async function (imageId) {
    if (!confirm('이 이미지를 삭제하시겠습니까?')) {
      return;
    }

    try {
      // URL을 동적으로 구성
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

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
}); 