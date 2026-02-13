// store-inactive.js - 스토어 비활성화 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // 페이지 로드 시 현재 시간 표시
  const now = new Date();
  const timeString = now.toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  // 페이지 타이틀에 접속 시간 정보 추가 (옵션)
  document.title = `스토어 일시 중단 - ${window.storeName} (${timeString} 접속)`;
  
  // 페이지 로드 애니메이션
  const cards = document.querySelectorAll('.animate-card');
  cards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
      card.style.transition = 'all 0.5s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, index * 100);
  });
  
  // 활성화 버튼 클릭 시 확인
  const activateBtn = document.getElementById('activateBtn');
  if (activateBtn) {
    activateBtn.addEventListener('click', function(e) {
      if (!confirm('스토어를 다시 활성화하시겠습니까?')) {
        e.preventDefault();
      }
    });
  }
}); 