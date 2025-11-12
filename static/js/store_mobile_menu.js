// 스토어 모바일 메뉴 토글 (store_nav_bar.html용)
document.addEventListener('DOMContentLoaded', function() {
  const storeMobileMenuButton = document.getElementById('store-mobile-menu-button');
  const storeMobileMenu = document.getElementById('store-mobile-menu');
  const storeMobileMenuOverlay = document.getElementById('store-mobile-menu-overlay');
  
  if (storeMobileMenuButton && storeMobileMenu) {
    function setStoreMenuVisibility(show) {
      if (show) {
        storeMobileMenu.classList.remove('hidden');
        if (storeMobileMenuOverlay) {
          storeMobileMenuOverlay.classList.remove('hidden');
        }
      } else {
        storeMobileMenu.classList.add('hidden');
        if (storeMobileMenuOverlay) {
          storeMobileMenuOverlay.classList.add('hidden');
        }
      }
      const icon = storeMobileMenuButton.querySelector('i');
      if (icon) {
        icon.className = show
          ? 'fas fa-times text-lg pointer-events-none'
          : 'fas fa-bars text-lg pointer-events-none';
      }
    }

    function toggleStoreMobileMenu(e) {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      const shouldOpen = storeMobileMenu.classList.contains('hidden');
      setStoreMenuVisibility(shouldOpen);
    }
    
    storeMobileMenuButton.addEventListener('click', toggleStoreMobileMenu);
    storeMobileMenuButton.addEventListener('touchend', function(e) {
      e.preventDefault();
      e.stopPropagation();
      toggleStoreMobileMenu();
    });

    if (storeMobileMenuOverlay) {
      storeMobileMenuOverlay.addEventListener('click', () => setStoreMenuVisibility(false));
    }
    
    document.addEventListener('click', function(e) {
      if (!storeMobileMenu.contains(e.target) && !storeMobileMenuButton.contains(e.target)) {
        if (!storeMobileMenu.classList.contains('hidden')) {
          setStoreMenuVisibility(false);
        }
      }
    });
    
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && !storeMobileMenu.classList.contains('hidden')) {
        setStoreMenuVisibility(false);
      }
    });
  } else {
    console.error('Store mobile menu elements not found');
  }
}); 
