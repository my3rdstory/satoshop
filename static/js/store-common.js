// 스토어 전용 JavaScript 함수들

// 상품 섹션으로 스크롤
function scrollToProducts() {
  const productsSection = document.getElementById('products-section');
  if (productsSection) {
    productsSection.scrollIntoView({ behavior: 'smooth' });
  } else {
    // 상품 섹션이 없으면 상품 목록 페이지로 이동
    if (window.storeId) {
      window.location.href = `/stores/${window.storeId}/products/`;
    } else {
      window.location.href = window.homeUrl || '/';
    }
  }
}

// 스토어 전용 테마 초기화 (theme-toggle.js와 연동)
function initStoreTheme() {
  document.addEventListener('DOMContentLoaded', () => {
    // theme-toggle.js에서 이미 테마가 초기화되므로 여기서는 추가 작업만 수행
    console.log('Store theme integration loaded');
  });
}

// 스토어 테마 초기화
initStoreTheme();

// store-common.js - 스토어 공통 JavaScript 기능

document.addEventListener('DOMContentLoaded', function() {
  // 스토어 공통 초기화
  console.log('Store common JavaScript loaded');
  
  // 스토어 관련 공통 기능들을 여기에 추가할 수 있습니다
  
  // 예: 스토어 이미지 로딩 에러 처리
  const storeImages = document.querySelectorAll('img[src*="/media/"]');
  storeImages.forEach(img => {
    img.addEventListener('error', function() {
      this.src = '/static/images/placeholder-store.png'; // 기본 이미지로 대체
    });
  });
  
  // 스토어 링크 클릭 추적 (선택사항)
  const storeLinks = document.querySelectorAll('a[href*="/stores/"]');
  storeLinks.forEach(link => {
    link.addEventListener('click', function() {
      // 스토어 방문 추적 로직을 여기에 추가할 수 있습니다
      console.log('Store link clicked:', this.href);
    });
  });
}); 