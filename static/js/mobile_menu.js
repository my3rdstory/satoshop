// 모바일 메뉴 토글 (통합 버전)
document.addEventListener('DOMContentLoaded', function() {
  const mobileMenuButton = document.getElementById('mobile-menu-button');
  const mobileMenu = document.getElementById('mobile-menu');
  const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
  
  if (mobileMenuButton && mobileMenu) {
    function setMenuVisibility(show) {
      if (show) {
        mobileMenu.classList.remove('hidden');
        if (mobileMenuOverlay) {
          mobileMenuOverlay.classList.remove('hidden');
        }
      } else {
        mobileMenu.classList.add('hidden');
        if (mobileMenuOverlay) {
          mobileMenuOverlay.classList.add('hidden');
        }
      }
      const icon = mobileMenuButton.querySelector('i');
      if (icon) {
        icon.className = show
          ? 'fas fa-times text-lg pointer-events-none'
          : 'fas fa-bars text-lg pointer-events-none';
      }
    }

    function toggleMobileMenu(e) {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      const shouldOpen = mobileMenu.classList.contains('hidden');
      setMenuVisibility(shouldOpen);
    }
    
    mobileMenuButton.addEventListener('click', toggleMobileMenu);
    mobileMenuButton.addEventListener('touchend', function(e) {
      e.preventDefault();
      e.stopPropagation();
      toggleMobileMenu();
    });

    if (mobileMenuOverlay) {
      mobileMenuOverlay.addEventListener('click', () => setMenuVisibility(false));
    }
    
    document.addEventListener('click', function(e) {
      if (!mobileMenu.contains(e.target) && !mobileMenuButton.contains(e.target)) {
        if (!mobileMenu.classList.contains('hidden')) {
          setMenuVisibility(false);
        }
      }
    });
    
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && !mobileMenu.classList.contains('hidden')) {
        setMenuVisibility(false);
      }
    });
  }
}); 
