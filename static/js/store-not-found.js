// store-not-found.js - 스토어 404 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // 페이지 로드 시 현재 시간과 함께 로그
  const now = new Date();
  const timeString = now.toLocaleString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });

  // 콘솔에 404 로그 기록
  console.log(`404 페이지 접속: 스토어 ID '${window.storeId}' - ${timeString}`);

  // 페이지 타이틀에 접속 시간 정보 추가
  document.title = `스토어를 찾을 수 없습니다 - ${window.storeId} (${timeString} 접속)`;
  
  // 뒤로가기 버튼에 대한 추가 처리
  // 만약 이전 페이지가 없다면 홈으로 이동하는 버튼으로 변경
  const backButton = document.querySelector('button[onclick="history.back()"]');
  if (backButton && history.length <= 1) {
    backButton.onclick = function() { window.location.href = '/'; };
    const spanElement = backButton.querySelector('span:last-child');
    if (spanElement) {
      spanElement.textContent = '홈으로 가기';
    }
  }
  
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
  
  // 404 아이콘 애니메이션
  const icon404 = document.querySelector('.icon-404');
  if (icon404) {
    setTimeout(() => {
      icon404.style.animation = 'bounce 2s infinite';
    }, 500);
  }
}); 