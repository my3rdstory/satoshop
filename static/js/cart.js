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

// 화면 크기에 따른 장바구니 초기화 (플로팅 버튼 제거로 단순화)
document.addEventListener('DOMContentLoaded', function() {
  // 플로팅 버튼이 제거되어 자동 열기 기능 비활성화
  // 사용자가 직접 네비게이션에서 장바구니 페이지로 이동해야 함
});

// removeFromCart 함수는 cart-common.js에서 로드됩니다 