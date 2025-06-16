// store-detail.js - 스토어 상세 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function () {
  // 페이지 로드 완료
  console.log('Store page loaded');
});

function startLightningPayment() {
  alert('라이트닝 결제 기능은 현재 개발 중입니다.');
}

// 이미지 모달 기능
function openImageModal(imageUrl, imageName) {
  const modal = document.getElementById('imageModal');
  const modalImage = document.getElementById('modalImage');

  modalImage.src = imageUrl;
  modalImage.alt = imageName;
  modal.classList.remove('hidden');
}

function closeImageModal() {
  const modal = document.getElementById('imageModal');
  modal.classList.add('hidden');
}

// ESC 키로 모달 닫기
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') {
    closeImageModal();
  }
}); 