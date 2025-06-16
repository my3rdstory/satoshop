// browse-stores.js - 스토어 탐색 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // 검색 입력창에서 엔터키 처리
  const searchInput = document.querySelector('input[name="q"]');
  if (searchInput) {
    searchInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.closest('form').submit();
      }
    });

    // 검색창 포커스 시 효과
    searchInput.addEventListener('focus', function() {
      this.style.transform = 'scale(1.01)';
    });

    searchInput.addEventListener('blur', function() {
      this.style.transform = 'scale(1)';
    });
  }
}); 