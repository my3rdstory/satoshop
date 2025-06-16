// 장바구니 관련 모든 JavaScript 함수들

// 장바구니 토글 함수들
function toggleCart() {
  const cart = document.getElementById('sidebarCart');
  const overlay = document.getElementById('cartOverlay');
  
  if (cart && cart.classList.contains('translate-x-full')) {
    openCart();
  } else {
    closeCart();
  }
}

function openCart() {
  const cart = document.getElementById('sidebarCart');
  const overlay = document.getElementById('cartOverlay');
  
  if (cart) {
    cart.classList.remove('translate-x-full');
  }
  
  // 모바일에서만 오버레이 활성화
  if (window.innerWidth <= 768 && overlay) {
    overlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // 배경 스크롤 방지
  }
}

function closeCart() {
  const cart = document.getElementById('sidebarCart');
  const overlay = document.getElementById('cartOverlay');
  
  if (cart) {
    cart.classList.add('translate-x-full');
  }
  if (overlay) {
    overlay.classList.add('hidden');
  }
  document.body.style.overflow = ''; // 배경 스크롤 복원
}

function handleCloseCart() {
  // 모든 화면 크기에서 닫기 버튼으로 닫기 가능
  closeCart();
}

function handleOverlayClick() {
  // 모바일/태블릿에서만 오버레이 클릭으로 닫기
  if (window.innerWidth < 1025) {
    closeCart();
  }
}

// ESC 키로 장바구니 닫기 (모바일/태블릿에서만)
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape' && window.innerWidth < 1025) {
    closeCart();
  }
});

// 화면 크기에 따른 장바구니 초기화
document.addEventListener('DOMContentLoaded', function() {
  const cartToggleBtn = document.getElementById('cartToggleBtn');
  
  // 데스크톱에서는 기본으로 열려있도록 설정 (아이템이 있을 때만)
  if (window.innerWidth >= 1025 && cartToggleBtn && cartToggleBtn.classList.contains('has-items')) {
    openCart();
  }
  
  // 화면 크기 변경 감지
  window.addEventListener('resize', function() {
    if (window.innerWidth >= 1025 && cartToggleBtn && cartToggleBtn.classList.contains('has-items')) {
      // 데스크톱에서는 아이템이 있을 때만 자동으로 열기
      openCart();
    } else {
      // 모바일/태블릿에서는 닫기
      closeCart();
    }
  });
});

// removeFromCart 함수는 cart-common.js에서 로드됩니다 