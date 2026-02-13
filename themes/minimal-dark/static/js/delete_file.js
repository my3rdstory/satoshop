// delete_file.js - 파일 삭제 기능을 위한 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const deleteForm = document.getElementById('delete-form');
    const confirmButton = document.getElementById('confirm-delete');
    const cancelButton = document.getElementById('cancel-delete');
    const fileNameSpan = document.querySelector('.file-name');
    const confirmInput = document.getElementById('confirm-input');
    
    // 파일명 확인 입력 기능
    if (confirmInput && fileNameSpan) {
        const fileName = fileNameSpan.textContent.trim();
        
        confirmInput.addEventListener('input', function() {
            const inputValue = this.value.trim();
            if (inputValue === fileName) {
                confirmButton.disabled = false;
                confirmButton.classList.remove('opacity-50', 'cursor-not-allowed');
                confirmButton.classList.add('hover:bg-red-600');
            } else {
                confirmButton.disabled = true;
                confirmButton.classList.add('opacity-50', 'cursor-not-allowed');
                confirmButton.classList.remove('hover:bg-red-600');
            }
        });
    }
    
    // 삭제 폼 제출
    if (deleteForm && confirmButton) {
        confirmButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            // 최종 확인
            const confirmed = confirm('정말로 이 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.');
            
            if (confirmed) {
                // 버튼 비활성화 및 로딩 표시
                confirmButton.disabled = true;
                confirmButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>삭제 중...';
                
                // 관련 데이터 백업 정보 표시
                showBackupReminder();
                
                // 폼 제출
                deleteForm.submit();
            }
        });
    }
    
    // 취소 버튼
    if (cancelButton) {
        cancelButton.addEventListener('click', function(e) {
            e.preventDefault();
            window.history.back();
        });
    }
    
    // 백업 알림 표시
    function showBackupReminder() {
        const reminder = document.createElement('div');
        reminder.className = 'fixed top-4 right-4 bg-yellow-100 dark:bg-yellow-900 border border-yellow-400 dark:border-yellow-700 text-yellow-700 dark:text-yellow-200 px-4 py-3 rounded shadow-lg max-w-md';
        reminder.innerHTML = `
            <div class="flex items-start">
                <i class="fas fa-exclamation-triangle mr-2 mt-1"></i>
                <div>
                    <p class="font-semibold">파일 삭제 중</p>
                    <p class="text-sm mt-1">파일과 관련된 모든 데이터가 삭제됩니다.</p>
                </div>
            </div>
        `;
        document.body.appendChild(reminder);
    }
    
    // 삭제 관련 통계 표시
    function displayDeletionStats() {
        const statsElement = document.getElementById('deletion-stats');
        if (statsElement) {
            // 서버에서 통계 데이터 가져오기
            fetch(statsElement.dataset.statsUrl)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        statsElement.innerHTML = `
                            <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4">
                                <h4 class="font-semibold text-gray-900 dark:text-white mb-2">삭제될 데이터:</h4>
                                <ul class="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                                    <li>• 판매 기록: ${data.sales_count}건</li>
                                    <li>• 다운로드 기록: ${data.download_count}건</li>
                                    <li>• 파일 크기: ${data.file_size}</li>
                                </ul>
                            </div>
                        `;
                    }
                })
                .catch(error => {
                    console.error('통계 데이터 로드 실패:', error);
                });
        }
    }
    
    // 페이지 로드 시 통계 표시
    displayDeletionStats();
    
    // 키보드 단축키
    document.addEventListener('keydown', function(e) {
        // ESC 키로 취소
        if (e.key === 'Escape') {
            if (cancelButton) {
                cancelButton.click();
            }
        }
        
        // Enter 키로 확인 (입력 필드에 포커스가 없을 때만)
        if (e.key === 'Enter' && document.activeElement !== confirmInput) {
            if (confirmButton && !confirmButton.disabled) {
                confirmButton.click();
            }
        }
    });
    
    // 페이지 떠나기 경고
    let isDeleting = false;
    
    if (deleteForm) {
        deleteForm.addEventListener('submit', function() {
            isDeleting = true;
        });
    }
    
    window.addEventListener('beforeunload', function(e) {
        if (!isDeleting && confirmInput && confirmInput.value.length > 0) {
            e.preventDefault();
            e.returnValue = '입력한 내용이 있습니다. 정말로 페이지를 떠나시겠습니까?';
        }
    });
});