// create-step3.js - 스토어 생성 3단계 JavaScript

document.addEventListener('DOMContentLoaded', function () {
  // API 키 보기/숨기기
  const toggleApi = document.getElementById('toggleApi');
  const toggleApiText = document.getElementById('toggleApiText');
  const apiInput = document.getElementById('blink_api_info');

  // 월렛 ID 보기/숨기기
  const toggleWallet = document.getElementById('toggleWallet');
  const toggleWalletText = document.getElementById('toggleWalletText');
  const walletInput = document.getElementById('blink_wallet_id');

  // 제출 버튼
  const submitBtn = document.getElementById('submitBtn');

  // 입력 필드 검증 함수
  function validateInputs() {
    const apiInfo = apiInput.value.trim();
    const walletId = walletInput.value.trim();

    // 두 필드 모두 입력되었을 때만 버튼 활성화
    if (apiInfo && walletId) {
      submitBtn.disabled = false;
      submitBtn.classList.remove('bg-gray-300');
      submitBtn.classList.add('bg-yellow-500', 'hover:bg-yellow-600');
      submitBtn.title = '';
    } else {
      submitBtn.disabled = true;
      submitBtn.classList.remove('bg-yellow-500', 'hover:bg-yellow-600');
      submitBtn.classList.add('bg-gray-300');
      submitBtn.title = '블링크 API 정보와 월렛 ID를 모두 입력해주세요.';
    }
  }

  // 입력 필드에 이벤트 리스너 추가
  apiInput.addEventListener('input', validateInputs);
  walletInput.addEventListener('input', validateInputs);

  toggleApi.addEventListener('click', function () {
    if (apiInput.type === 'password') {
      apiInput.type = 'text';
      toggleApi.innerHTML = '<i class="fas fa-eye-slash text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer"></i>';
      toggleApiText.textContent = 'API 키 숨기기';
    } else {
      apiInput.type = 'password';
      toggleApi.innerHTML = '<i class="fas fa-eye text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer"></i>';
      toggleApiText.textContent = 'API 키 보기';
    }
  });

  toggleWallet.addEventListener('click', function () {
    if (walletInput.type === 'password') {
      walletInput.type = 'text';
      toggleWallet.innerHTML = '<i class="fas fa-eye-slash text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer"></i>';
      toggleWalletText.textContent = '월렛 ID 숨기기';
    } else {
      walletInput.type = 'password';
      toggleWallet.innerHTML = '<i class="fas fa-eye text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer"></i>';
      toggleWalletText.textContent = '월렛 ID 보기';
    }
  });

  // 폼 제출 검증
  document.getElementById('step3Form').addEventListener('submit', function (e) {
    const apiInfo = apiInput.value.trim();
    const walletId = walletInput.value.trim();

    if (!apiInfo || !walletId) {
      e.preventDefault();
      alert('모든 필드를 입력해주세요.');
      return false;
    }

    // 확인 대화상자
    if (!confirm('입력한 API 정보가 정확한지 확인하셨나요? 잘못된 정보는 결제 처리에 문제를 일으킬 수 있습니다.')) {
      e.preventDefault();
      return false;
    }
  });

  // 초기 상태 검증
  validateInputs();
}); 