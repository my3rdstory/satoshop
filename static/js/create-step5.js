// create-step5.js - 스토어 생성 5단계 JavaScript

document.addEventListener('DOMContentLoaded', function () {
  const agreeInfo = document.getElementById('agreeInfo');
  const agreeTerms = document.getElementById('agreeTerms');
  const createStoreBtn = document.getElementById('createStoreBtn');

  // 마크다운 렌더링은 MarkdownRenderer가 자동으로 처리

  // 체크박스 상태 확인 함수
  function checkAllAgreements() {
    if (!agreeInfo || !agreeTerms || !createStoreBtn) {
      console.error('필요한 요소들을 찾을 수 없습니다');
      return;
    }

    const allChecked = agreeInfo.checked && agreeTerms.checked;
    createStoreBtn.disabled = !allChecked;

    if (allChecked) {
      createStoreBtn.classList.remove('from-gray-300', 'to-gray-300');
      createStoreBtn.classList.add('from-purple-500', 'to-pink-600', 'hover:from-purple-600', 'hover:to-pink-700');
    } else {
      createStoreBtn.classList.remove('from-purple-500', 'to-pink-600', 'hover:from-purple-600', 'hover:to-pink-700');
      createStoreBtn.classList.add('from-gray-300', 'to-gray-300');
    }
  }

  // 동의 체크박스들에 이벤트 리스너 추가
  if (agreeInfo) {
    agreeInfo.addEventListener('change', checkAllAgreements);
  }
  if (agreeTerms) {
    agreeTerms.addEventListener('change', checkAllAgreements);
  }

  // 초기 상태 설정 (페이지 로드시 두 체크박스 모두 비활성화 상태)
  checkAllAgreements();

  // 폼 제출 시 최종 확인
  document.getElementById('step5Form').addEventListener('submit', function (e) {
    // 폼 제출 시도

    if (!agreeInfo.checked) {
      e.preventDefault();
      alert('스토어 정보와 주의사항 확인에 동의해주세요.');
      return false;
    }

    if (!agreeTerms.checked) {
      e.preventDefault();
      alert('이용약관, 개인정보처리방침, 환불 및 반품 정책에 동의해주세요.');
      return false;
    }

    // 최종 확인 대화상자
    if (!confirm('정말로 스토어를 생성하시겠습니까?\n생성 후 스토어 아이디는 변경할 수 없습니다.')) {
      e.preventDefault();
              // 사용자가 취소함
      return false;
    }

          // 폼 제출 진행
    // 버튼 로딩 상태로 변경
    createStoreBtn.innerHTML = `
      <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-3"></div>
      <span>스토어 생성 중...</span>
    `;
    createStoreBtn.disabled = true;

    // 폼이 정상적으로 제출되도록 허용
    return true;
  });

  // 애니메이션 효과
  const summaryBox = document.querySelector('.bg-gray-50.dark\\:bg-gray-700');
  if (summaryBox) {
    summaryBox.style.opacity = '0';
    summaryBox.style.transform = 'translateY(20px)';

    setTimeout(() => {
      summaryBox.style.transition = 'all 0.5s ease';
      summaryBox.style.opacity = '1';
      summaryBox.style.transform = 'translateY(0)';
    }, 300);
  }
}); 