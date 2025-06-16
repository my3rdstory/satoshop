// my-stores.js - 내 스토어 목록 페이지 JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // 스토어 카드 애니메이션
  const storeCards = document.querySelectorAll('.store-card');
  storeCards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
      card.style.transition = 'all 0.5s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, index * 100);
  });

  // 스토어 삭제 확인
  const deleteButtons = document.querySelectorAll('.delete-store-btn');
  deleteButtons.forEach(button => {
    button.addEventListener('click', function(e) {
      e.preventDefault();
      
      const storeName = this.dataset.storeName;
      const storeId = this.dataset.storeId;
      
      if (confirm(`정말로 "${storeName}" 스토어를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`)) {
        // 삭제 요청
        fetch(`/stores/delete/${storeId}/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json'
          }
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // 성공 시 카드 제거 애니메이션
            const card = this.closest('.store-card');
            card.style.transition = 'all 0.3s ease';
            card.style.opacity = '0';
            card.style.transform = 'translateX(-100%)';
            
            setTimeout(() => {
              card.remove();
              
              // 스토어가 없으면 빈 상태 메시지 표시
              if (document.querySelectorAll('.store-card').length === 0) {
                showEmptyState();
              }
            }, 300);
            
            showNotification('스토어가 삭제되었습니다.', 'success');
          } else {
            showNotification(data.error || '스토어 삭제에 실패했습니다.', 'error');
          }
        })
        .catch(error => {
          console.error('Error:', error);
          showNotification('서버 오류가 발생했습니다.', 'error');
        });
      }
    });
  });

  // 빈 상태 메시지 표시
  function showEmptyState() {
    const container = document.querySelector('.stores-grid');
    if (container) {
      container.innerHTML = `
        <div class="col-span-full text-center py-12">
          <div class="inline-flex items-center justify-center w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full mb-4">
            <i class="fas fa-store text-2xl text-gray-400 dark:text-gray-500"></i>
          </div>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">아직 스토어가 없습니다</h3>
          <p class="text-gray-500 dark:text-gray-400 mb-6">첫 번째 스토어를 만들어보세요!</p>
          <a href="/stores/create/" class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors">
            <i class="fas fa-plus mr-2"></i>
            스토어 만들기
          </a>
        </div>
      `;
    }
  }

  // 알림 메시지 표시 함수
  function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg text-white ${
      type === 'success' ? 'bg-green-500' : 'bg-red-500'
    }`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // 3초 후 제거
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  // 스토어 상태 표시 업데이트
  const statusBadges = document.querySelectorAll('.status-badge');
  statusBadges.forEach(badge => {
    const status = badge.textContent.trim();
    if (status === '활성') {
      badge.classList.add('animate-pulse');
    }
  });
}); 