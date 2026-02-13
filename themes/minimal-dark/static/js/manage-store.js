// 스토어 관리 페이지 JavaScript
function confirmStatusChange(checkbox) {
    // Django 템플릿에서 전달된 현재 상태 확인
    const isCurrentlyActive = checkbox.dataset.currentState === 'true';
    const willBeActive = checkbox.checked;

    let message;
    if (willBeActive && !isCurrentlyActive) {
        message = '스토어를 활성화하시겠습니까?\n\n활성화하면 고객들이 스토어를 방문하고 결제할 수 있습니다.';
    } else if (!willBeActive && isCurrentlyActive) {
        message = '스토어를 비활성화하시겠습니까?\n\n비활성화하면 고객들이 스토어에 접근할 수 없게 됩니다.\n모든 결제 링크가 작동하지 않습니다.';
    }

    if (confirm(message)) {
        // 확인한 경우 폼 제출
        document.getElementById('toggleForm').submit();
    } else {
        // 취소한 경우 체크박스 상태를 원래대로 되돌림
        checkbox.checked = !checkbox.checked;
    }
}

function confirmDelete() {
    // 스토어 이름을 데이터 속성에서 가져오기
    const storeNameElement = document.querySelector('[data-store-name]');
    const storeName = storeNameElement ? storeNameElement.dataset.storeName : '';
    const userInput = prompt(
        `정말로 스토어를 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다!\n\n계속하려면 스토어 이름 "${storeName}"을 정확히 입력하세요:`
    );

    if (userInput === null) {
        return false; // 사용자가 취소를 눌렀을 때
    }

    if (userInput !== storeName) {
        alert('스토어 이름이 일치하지 않습니다. 삭제가 취소되었습니다.');
        return false;
    }

    return confirm('마지막 확인: 정말로 스토어를 완전히 삭제하시겠습니까?');
}

// DOM이 로드된 후 실행
document.addEventListener('DOMContentLoaded', function() {
    // 스토어 상태 토글 기능
    const statusToggle = document.getElementById('statusToggle');
    if (statusToggle) {
        statusToggle.addEventListener('change', function() {
            const storeId = this.dataset.storeId;
            const isActive = this.checked;
            
            // 확인 대화상자
            const action = isActive ? '활성화' : '비활성화';
            if (!confirm(`스토어를 ${action}하시겠습니까?`)) {
                this.checked = !isActive; // 원래 상태로 되돌리기
                return;
            }
            
            // 서버에 상태 변경 요청
            fetch(`/stores/manage/${storeId}/toggle-status/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    is_active: isActive
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 성공 메시지 표시
                    showNotification(`스토어가 ${action}되었습니다.`, 'success');
                    
                    // 페이지 새로고침 (상태 반영)
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    // 실패 시 원래 상태로 되돌리기
                    this.checked = !isActive;
                    showNotification(data.error || '상태 변경에 실패했습니다.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.checked = !isActive;
                showNotification('서버 오류가 발생했습니다.', 'error');
            });
        });
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
    
      // 통계 카드 애니메이션
  const statCards = document.querySelectorAll('.stat-card');
  statCards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    
    setTimeout(() => {
      card.style.transition = 'all 0.5s ease';
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, index * 100);
  });
});

// 상태 변경 확인 함수
function confirmStatusChange(checkbox) {
  const currentState = checkbox.dataset.currentState === 'true';
  const newState = checkbox.checked;
  
  // 상태가 실제로 변경되었는지 확인
  if (currentState === newState) {
    return;
  }
  
  const action = newState ? '활성화' : '비활성화';
  const message = `정말로 스토어를 ${action}하시겠습니까?`;
  
  if (confirm(message)) {
    // 폼 제출
    checkbox.closest('form').submit();
  } else {
    // 취소 시 원래 상태로 되돌리기
    checkbox.checked = currentState;
  }
}

// 스토어 삭제 확인 함수
function confirmDelete() {
  const storeName = document.querySelector('[data-store-name]').dataset.storeName;
  
  const firstConfirm = confirm(
    `정말로 "${storeName}" 스토어를 완전히 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없습니다.`
  );
  
  if (!firstConfirm) {
    return false;
  }
  
  const secondConfirm = confirm(
    `마지막 확인입니다.\n\n"${storeName}" 스토어와 모든 관련 데이터가 영구적으로 삭제됩니다.\n\n정말로 진행하시겠습니까?`
  );
  
  return secondConfirm;
} 