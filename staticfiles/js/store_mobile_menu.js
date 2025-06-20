// 스토어 모바일 메뉴 토글 (store_nav_bar.html용)
document.addEventListener('DOMContentLoaded', function() {
  const storeMobileMenuButton = document.getElementById('store-mobile-menu-button');
  const storeMobileMenu = document.getElementById('store-mobile-menu');
  
  if (storeMobileMenuButton && storeMobileMenu) {
    // 메뉴 토글 함수
    function toggleStoreMobileMenu(e) {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      
      // 토글 처리
      const isHidden = storeMobileMenu.classList.contains('hidden');
      if (isHidden) {
        storeMobileMenu.classList.remove('hidden');
      } else {
        storeMobileMenu.classList.add('hidden');
      }
      
      // 아이콘 변경
      const icon = storeMobileMenuButton.querySelector('i');
      if (icon) {
        if (storeMobileMenu.classList.contains('hidden')) {
          icon.className = 'fas fa-bars text-lg pointer-events-none';
        } else {
          icon.className = 'fas fa-times text-lg pointer-events-none';
        }
      }
    }
    
    // 다양한 이벤트 리스너 추가 (모바일 호환성 향상)
    storeMobileMenuButton.addEventListener('click', toggleStoreMobileMenu);
    storeMobileMenuButton.addEventListener('touchend', function(e) {
      e.preventDefault();
      e.stopPropagation();
      toggleStoreMobileMenu();
    });
    
    // 메뉴 외부 클릭 시 닫기
    document.addEventListener('click', function(e) {
      if (!storeMobileMenu.contains(e.target) && !storeMobileMenuButton.contains(e.target)) {
        if (!storeMobileMenu.classList.contains('hidden')) {
          storeMobileMenu.classList.add('hidden');
          const icon = storeMobileMenuButton.querySelector('i');
          if (icon) {
            icon.className = 'fas fa-bars text-lg pointer-events-none';
          }
        }
      }
    });
    
    // ESC 키로 메뉴 닫기
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && !storeMobileMenu.classList.contains('hidden')) {
        storeMobileMenu.classList.add('hidden');
        const icon = storeMobileMenuButton.querySelector('i');
        if (icon) {
          icon.className = 'fas fa-bars text-lg pointer-events-none';
        }
      }
    });
  } else {
    console.error('Store mobile menu elements not found');
  }
}); 