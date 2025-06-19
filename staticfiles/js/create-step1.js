// create-step1.js - 스토어 생성 1단계 JavaScript

document.addEventListener('DOMContentLoaded', function () {
  const storeIdInput = document.getElementById('store_id');
  const previewUrl = document.getElementById('previewUrl');
  const submitBtn = document.getElementById('submitBtn');
  const checkIcon = document.getElementById('checkIcon');
  const helpText = document.getElementById('storeIdHelp');
  let checkTimeout;

  // 스토어 아이디 입력 시 미리보기 업데이트
  storeIdInput.addEventListener('input', function () {
    const value = this.value;
    previewUrl.value = `${window.location.host}/stores/${value}`;

    // 아이콘과 버튼 초기화
    checkIcon.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.classList.remove('bg-blue-500', 'hover:bg-blue-600');
    submitBtn.classList.add('bg-gray-300');
    helpText.className = 'mt-2 text-sm text-gray-600 dark:text-gray-400';
    helpText.textContent = '영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.';

    // 입력 검증
    if (value.length === 0) {
      return;
    }

    // 패턴 검증
    const pattern = /^[a-zA-Z0-9_-]+$/;
    if (!pattern.test(value)) {
      helpText.className = 'mt-2 text-sm text-red-600 dark:text-red-400';
      helpText.textContent = '영문, 숫자, 하이픈(-), 언더스코어(_)만 사용 가능합니다.';
      return;
    }

    // 중복 검사 (디바운싱)
    clearTimeout(checkTimeout);
    checkTimeout = setTimeout(() => {
      checkStoreIdAvailability(value);
    }, 500);
  });

  function checkStoreIdAvailability(storeId) {
    // 현재 생성 중인 스토어 아이디도 전송하여 체크에서 제외
    const currentStoreId = window.currentStoreId || '';
    let body = `store_id=${encodeURIComponent(storeId)}`;
    if (currentStoreId) {
      body += `&current_store_id=${encodeURIComponent(currentStoreId)}`;
    }

    fetch(window.checkStoreIdUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': window.csrfToken
      },
      body: body
    })
      .then(response => response.json())
      .then(data => {
        if (data.available) {
          checkIcon.style.display = 'block';
          checkIcon.innerHTML = '<i class="fas fa-check text-green-500"></i>';
          submitBtn.disabled = false;
          submitBtn.classList.remove('bg-gray-300');
          submitBtn.classList.add('bg-blue-500', 'hover:bg-blue-600');
          helpText.className = 'mt-2 text-sm text-green-600 dark:text-green-400';
          helpText.textContent = data.message;
        } else {
          checkIcon.style.display = 'block';
          checkIcon.innerHTML = '<i class="fas fa-times text-red-500"></i>';
          submitBtn.disabled = true;
          submitBtn.classList.remove('bg-blue-500', 'hover:bg-blue-600');
          submitBtn.classList.add('bg-gray-300');
          helpText.className = 'mt-2 text-sm text-red-600 dark:text-red-400';
          helpText.textContent = data.message;
        }
      })
      .catch(error => {
        console.error('Error:', error);
        helpText.className = 'mt-2 text-sm text-red-600 dark:text-red-400';
        helpText.textContent = '서버 오류가 발생했습니다.';
      });
  }

  // 폼 제출 시 재검증
  document.getElementById('step1Form').addEventListener('submit', function (e) {
    if (submitBtn.disabled) {
      e.preventDefault();
      alert('스토어 아이디를 다시 확인해주세요.');
    }
  });

  // 기존 값이 있다면 검증
  if (storeIdInput.value) {
    checkStoreIdAvailability(storeIdInput.value);
  }
}); 