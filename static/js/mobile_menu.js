// 모바일 메뉴 토글 (통합 버전)
document.addEventListener('DOMContentLoaded', function() {
  const mobileMenuButton = document.getElementById('mobile-menu-button');
  const mobileMenu = document.getElementById('mobile-menu');
  
  if (mobileMenuButton && mobileMenu) {
    // 메뉴 토글 함수
    function toggleMobileMenu(e) {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      
      // 토글 처리
      const isHidden = mobileMenu.classList.contains('hidden');
      if (isHidden) {
        mobileMenu.classList.remove('hidden');
      } else {
        mobileMenu.classList.add('hidden');
      }
      
      // 아이콘 변경
      const icon = mobileMenuButton.querySelector('i');
      if (icon) {
        if (mobileMenu.classList.contains('hidden')) {
          icon.className = 'fas fa-bars text-lg pointer-events-none';
        } else {
          icon.className = 'fas fa-times text-lg pointer-events-none';
        }
      }
    }
    
    // 다양한 이벤트 리스너 추가 (모바일 호환성 향상)
    mobileMenuButton.addEventListener('click', toggleMobileMenu);
    mobileMenuButton.addEventListener('touchend', function(e) {
      e.preventDefault();
      e.stopPropagation();
      toggleMobileMenu();
    });
    
    // 메뉴 외부 클릭 시 닫기
    document.addEventListener('click', function(e) {
      if (!mobileMenu.contains(e.target) && !mobileMenuButton.contains(e.target)) {
        if (!mobileMenu.classList.contains('hidden')) {
          mobileMenu.classList.add('hidden');
          const icon = mobileMenuButton.querySelector('i');
          if (icon) {
            icon.className = 'fas fa-bars text-lg pointer-events-none';
          }
        }
      }
    });
    
    // ESC 키로 메뉴 닫기
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && !mobileMenu.classList.contains('hidden')) {
        mobileMenu.classList.add('hidden');
        const icon = mobileMenuButton.querySelector('i');
        if (icon) {
          icon.className = 'fas fa-bars text-lg pointer-events-none';
        }
      }
    });
  }
}); 