// create-step2.js - 스토어 생성 2단계 JavaScript

document.addEventListener('DOMContentLoaded', function () {
  // EasyMDE 초기화
  const easyMDE = new EasyMDE({
    element: document.getElementById('store_description'),
    placeholder: '스토어에 대한 설명을 Markdown 형식으로 작성해주세요.\n\n예:\n# 안녕하세요!\n\n저희 스토어에 오신 것을 환영합니다.\n\n## 주요 상품\n- 상품 1\n- 상품 2\n\n**특별한 서비스**를 제공합니다!',
    spellChecker: false,
    status: false,
    toolbar: [
      'bold', 'italic', 'heading', '|',
      'quote', 'unordered-list', 'ordered-list', '|',
      'link', 'image'
    ]
  });

  // 폼 요소들
  const storeNameInput = document.getElementById('store_name');
  const ownerNameInput = document.getElementById('owner_name');
  const phoneInput = document.getElementById('owner_phone');
  const emailInput = document.getElementById('owner_email');
  const chatChannelInput = document.getElementById('chat_channel');
  const contactHelp = document.getElementById('contactHelp');
  const submitBtn = document.getElementById('submitBtn');

  // 연락처 검증 함수
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

  // 전체 폼 검증 함수
  function validateForm() {
    const storeName = storeNameInput.value.trim();
    const ownerName = ownerNameInput.value.trim();
    const chatChannel = chatChannelInput.value.trim();
    const contactValid = validateContact();

    // 모든 필수 항목이 충족되었는지 확인
    if (storeName && ownerName && chatChannel && contactValid) {
      submitBtn.disabled = false;
      submitBtn.classList.remove('bg-gray-300');
      submitBtn.classList.add('bg-cyan-500', 'hover:bg-cyan-600');
      submitBtn.title = '';
    } else {
      submitBtn.disabled = true;
      submitBtn.classList.remove('bg-cyan-500', 'hover:bg-cyan-600');
      submitBtn.classList.add('bg-gray-300');
      submitBtn.title = '모든 필수 항목을 입력해주세요.';
    }
  }

  // 모든 입력 필드에 이벤트 리스너 추가
  storeNameInput.addEventListener('input', validateForm);
  ownerNameInput.addEventListener('input', validateForm);
  phoneInput.addEventListener('input', validateForm);
  emailInput.addEventListener('input', validateForm);
  chatChannelInput.addEventListener('input', validateForm);

  // 폼 제출 검증
  document.getElementById('step2Form').addEventListener('submit', function (e) {
    if (submitBtn.disabled) {
      e.preventDefault();
      alert('모든 필수 항목을 입력해주세요.');
      return false;
    }
  });

  // 초기 검증
  validateForm();
}); 