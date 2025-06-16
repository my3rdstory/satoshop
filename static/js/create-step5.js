// create-step5.js - 스토어 생성 5단계 JavaScript

document.addEventListener('DOMContentLoaded', function () {
  const agreeTerms = document.getElementById('agreeTerms');
  const createStoreBtn = document.getElementById('createStoreBtn');

  // 마크다운 렌더링은 MarkdownRenderer가 자동으로 처리

  // 약관 동의 체크박스 상태에 따라 버튼 활성화/비활성화
  agreeTerms.addEventListener('change', function () {
    createStoreBtn.disabled = !this.checked;

    if (this.checked) {
      createStoreBtn.classList.remove('from-gray-300', 'to-gray-300');
      createStoreBtn.classList.add('from-purple-500', 'to-pink-600', 'hover:from-purple-600', 'hover:to-pink-700');
    } else {
      createStoreBtn.classList.remove('from-purple-500', 'to-pink-600', 'hover:from-purple-600', 'hover:to-pink-700');
      createStoreBtn.classList.add('from-gray-300', 'to-gray-300');
    }
  });

  // 폼 제출 시 최종 확인
  document.getElementById('step5Form').addEventListener('submit', function (e) {
    console.log('폼 제출 시도됨');

    if (!agreeTerms.checked) {
      e.preventDefault();
      alert('약관에 동의해주세요.');
      return false;
    }

    // 최종 확인 대화상자
    if (!confirm('정말로 스토어를 생성하시겠습니까?\n생성 후 스토어 아이디는 변경할 수 없습니다.')) {
      e.preventDefault();
      console.log('사용자가 취소함');
      return false;
    }

    console.log('폼 제출 진행됨');
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