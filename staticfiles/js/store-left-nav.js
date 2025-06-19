// store-left-nav.js - 스토어 왼쪽 네비게이션 JavaScript

// 스토어 소개로 스크롤
function scrollToStoreInfo() {
  const storeInfoSection = document.getElementById('store-info') || document.querySelector('.store-description');
  if (storeInfoSection) {
    storeInfoSection.scrollIntoView({ behavior: 'smooth' });
  }
}

// 상품 섹션으로 스크롤 (고객용)
function scrollToProducts() {
  const productsSection = document.getElementById('products-section');
  if (productsSection) {
    productsSection.scrollIntoView({ behavior: 'smooth' });
  } else {
    // 상품 섹션이 없으면 아무것도 하지 않음
            // 상품 섹션을 찾을 수 없음
  }
} 