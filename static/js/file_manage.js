// file_manage.js - 파일 관리 페이지를 위한 JavaScript

// 일시중단 토글 함수 (템플릿에서 사용)
function toggleTemporaryClosure(fileId) {
    const adminAccessQuery = window.adminAccessQuery || '';
    fetch(`/file/${window.storeId}/files/${fileId}/toggle-closure/${adminAccessQuery}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert(data.error || '상태 변경에 실패했습니다.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('상태 변경 중 오류가 발생했습니다.');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const toggleButtons = document.querySelectorAll('.toggle-button');
    const bulkSelectCheckbox = document.getElementById('bulk-select-all');
    const fileCheckboxes = document.querySelectorAll('.file-checkbox');
    const bulkActionButtons = document.querySelectorAll('.bulk-action');
    const searchInput = document.getElementById('manage-search');
    const filterTabs = document.querySelectorAll('.filter-tab');
    const fileRows = document.querySelectorAll('.file-row');
    
    // 토글 버튼 기능 (활성/비활성)
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const fileId = this.dataset.fileId;
            const action = this.dataset.action;
            const currentState = this.dataset.state === 'true';
            
            // 로딩 표시
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            // AJAX 요청
            fetch(`/file/api/toggle-status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    file_id: fileId,
                    action: action,
                    state: !currentState
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 버튼 상태 업데이트
                    updateToggleButton(this, !currentState, action);
                    showNotification(`파일이 ${!currentState ? '활성화' : '비활성화'}되었습니다.`, 'success');
                } else {
                    showNotification(data.error || '상태 변경에 실패했습니다.', 'error');
                }
            })
            .catch(error => {
                console.error('토글 오류:', error);
                showNotification('네트워크 오류가 발생했습니다.', 'error');
            })
            .finally(() => {
                this.disabled = false;
            });
        });
    });
    
    // 토글 버튼 업데이트 함수
    function updateToggleButton(button, state, action) {
        button.dataset.state = state;
        
        if (action === 'active') {
            if (state) {
                button.innerHTML = '<i class="fas fa-toggle-on text-green-500"></i>';
                button.title = '비활성화';
            } else {
                button.innerHTML = '<i class="fas fa-toggle-off text-gray-400"></i>';
                button.title = '활성화';
            }
        } else if (action === 'temporary') {
            if (state) {
                button.innerHTML = '<i class="fas fa-pause-circle text-yellow-500"></i>';
                button.title = '판매 재개';
            } else {
                button.innerHTML = '<i class="fas fa-play-circle text-green-500"></i>';
                button.title = '일시 중단';
            }
        }
    }
    
    // 대량 선택 기능
    if (bulkSelectCheckbox) {
        bulkSelectCheckbox.addEventListener('change', function() {
            const isChecked = this.checked;
            fileCheckboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
            updateBulkActionButtons();
        });
    }
    
    // 개별 체크박스 이벤트
    fileCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateBulkActionButtons();
            updateSelectAllCheckbox();
        });
    });
    
    // 대량 작업 버튼 업데이트
    function updateBulkActionButtons() {
        const checkedCount = document.querySelectorAll('.file-checkbox:checked').length;
        
        bulkActionButtons.forEach(button => {
            if (checkedCount > 0) {
                button.disabled = false;
                button.classList.remove('opacity-50', 'cursor-not-allowed');
            } else {
                button.disabled = true;
                button.classList.add('opacity-50', 'cursor-not-allowed');
            }
        });
        
        // 선택 개수 표시
        const countDisplay = document.getElementById('selected-count');
        if (countDisplay) {
            countDisplay.textContent = checkedCount > 0 ? `${checkedCount}개 선택됨` : '';
        }
    }
    
    // 전체 선택 체크박스 상태 업데이트
    function updateSelectAllCheckbox() {
        const totalCount = fileCheckboxes.length;
        const checkedCount = document.querySelectorAll('.file-checkbox:checked').length;
        
        if (bulkSelectCheckbox) {
            if (checkedCount === 0) {
                bulkSelectCheckbox.checked = false;
                bulkSelectCheckbox.indeterminate = false;
            } else if (checkedCount === totalCount) {
                bulkSelectCheckbox.checked = true;
                bulkSelectCheckbox.indeterminate = false;
            } else {
                bulkSelectCheckbox.checked = false;
                bulkSelectCheckbox.indeterminate = true;
            }
        }
    }
    
    // 대량 작업 실행
    bulkActionButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.dataset.bulkAction;
            const selectedFiles = Array.from(document.querySelectorAll('.file-checkbox:checked'))
                .map(cb => cb.value);
            
            if (selectedFiles.length === 0) return;
            
            let confirmMessage = '';
            switch(action) {
                case 'activate':
                    confirmMessage = `선택한 ${selectedFiles.length}개 파일을 활성화하시겠습니까?`;
                    break;
                case 'deactivate':
                    confirmMessage = `선택한 ${selectedFiles.length}개 파일을 비활성화하시겠습니까?`;
                    break;
                case 'delete':
                    confirmMessage = `선택한 ${selectedFiles.length}개 파일을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`;
                    break;
            }
            
            if (confirm(confirmMessage)) {
                performBulkAction(action, selectedFiles);
            }
        });
    });
    
    // 대량 작업 수행
    function performBulkAction(action, fileIds) {
        // 로딩 표시
        showLoadingOverlay();
        
        fetch('/file/api/bulk-action/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                action: action,
                file_ids: fileIds
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message || '작업이 완료되었습니다.', 'success');
                
                // 페이지 새로고침 또는 동적 업데이트
                if (action === 'delete') {
                    location.reload();
                } else {
                    updateFileStates(fileIds, action);
                }
            } else {
                showNotification(data.error || '작업 수행에 실패했습니다.', 'error');
            }
        })
        .catch(error => {
            console.error('대량 작업 오류:', error);
            showNotification('네트워크 오류가 발생했습니다.', 'error');
        })
        .finally(() => {
            hideLoadingOverlay();
            // 체크박스 초기화
            fileCheckboxes.forEach(cb => cb.checked = false);
            updateBulkActionButtons();
            updateSelectAllCheckbox();
        });
    }
    
    // 검색 기능
    if (searchInput) {
        let searchTimer;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimer);
            const searchTerm = this.value.toLowerCase();
            
            searchTimer = setTimeout(() => {
                filterFileRows(searchTerm);
            }, 300);
        });
    }
    
    // 파일 행 필터링
    function filterFileRows(searchTerm) {
        fileRows.forEach(row => {
            const fileName = row.querySelector('.file-name').textContent.toLowerCase();
            const shouldShow = fileName.includes(searchTerm);
            
            if (shouldShow) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
        
        // 결과 없음 메시지
        const visibleRows = document.querySelectorAll('.file-row:not([style*="display: none"])').length;
        updateNoResultsMessage(visibleRows);
    }
    
    // 필터 탭 기능
    filterTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const filter = this.dataset.filter;
            
            // 탭 활성화 상태
            filterTabs.forEach(t => t.classList.remove('active', 'border-purple-500', 'text-purple-600'));
            this.classList.add('active', 'border-purple-500', 'text-purple-600');
            
            // 필터 적용
            applyFilter(filter);
        });
    });
    
    // 필터 적용
    function applyFilter(filter) {
        fileRows.forEach(row => {
            let shouldShow = true;
            
            switch(filter) {
                case 'active':
                    shouldShow = row.querySelector('[data-action="active"][data-state="true"]') !== null;
                    break;
                case 'inactive':
                    shouldShow = row.querySelector('[data-action="active"][data-state="false"]') !== null;
                    break;
                case 'discounted':
                    shouldShow = row.querySelector('.discount-badge') !== null;
                    break;
                case 'soldout':
                    shouldShow = row.querySelector('.soldout-badge') !== null;
                    break;
            }
            
            row.style.display = shouldShow ? '' : 'none';
        });
    }
    
    // 통계 차트 (Chart.js 사용 시)
    const statsCanvas = document.getElementById('sales-chart');
    if (statsCanvas && typeof Chart !== 'undefined') {
        const ctx = statsCanvas.getContext('2d');
        
        // 서버에서 통계 데이터 가져오기
        fetch('/file/api/sales-stats/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.labels,
                            datasets: [{
                                label: '판매량',
                                data: data.sales,
                                borderColor: 'rgb(168, 85, 247)',
                                backgroundColor: 'rgba(168, 85, 247, 0.1)',
                                tension: 0.4
                            }, {
                                label: '다운로드',
                                data: data.downloads,
                                borderColor: 'rgb(34, 197, 94)',
                                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom'
                                }
                            }
                        }
                    });
                }
            });
    }
    
    // 파일 순서 변경 (드래그 앤 드롭)
    const sortableTable = document.getElementById('files-table');
    if (sortableTable && typeof Sortable !== 'undefined') {
        new Sortable(sortableTable.querySelector('tbody'), {
            handle: '.drag-handle',
            animation: 150,
            onEnd: function(evt) {
                const fileIds = Array.from(sortableTable.querySelectorAll('.file-row'))
                    .map(row => row.dataset.fileId);
                
                // 순서 저장
                fetch('/file/api/update-order/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({
                        file_ids: fileIds
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('순서가 저장되었습니다.', 'success');
                    }
                });
            }
        });
    }
    
    // CSV 내보내기
    const exportButton = document.getElementById('export-csv');
    if (exportButton) {
        exportButton.addEventListener('click', function() {
            const selectedFiles = Array.from(document.querySelectorAll('.file-checkbox:checked'))
                .map(cb => cb.value);
            
            const params = selectedFiles.length > 0 ? 
                `?files=${selectedFiles.join(',')}` : '';
            
            window.location.href = `/file/export/csv/${params}`;
        });
    }
    
    // 유틸리티 함수들
    function getCsrfToken() {
        const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
        return tokenElement ? tokenElement.value : '';
    }
    
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-6 py-4 rounded-lg shadow-lg max-w-md animate-slide-in z-50`;
        
        const colors = {
            success: 'bg-green-100 text-green-800 border-green-200',
            error: 'bg-red-100 text-red-800 border-red-200',
            info: 'bg-blue-100 text-blue-800 border-blue-200'
        };
        
        notification.className += ' ' + colors[type];
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} mr-3"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('animate-slide-out');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }
    
    function showLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        overlay.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6">
                <i class="fas fa-spinner fa-spin text-4xl text-purple-500"></i>
                <p class="mt-3 text-gray-700 dark:text-gray-300">처리 중...</p>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    
    function hideLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
    
    function updateNoResultsMessage(count) {
        let noResultsMsg = document.getElementById('no-results');
        
        if (count === 0) {
            if (!noResultsMsg) {
                noResultsMsg = document.createElement('tr');
                noResultsMsg.id = 'no-results';
                noResultsMsg.innerHTML = `
                    <td colspan="8" class="text-center py-8 text-gray-500">
                        <i class="fas fa-inbox text-4xl mb-2"></i>
                        <p>검색 결과가 없습니다.</p>
                    </td>
                `;
                document.querySelector('tbody').appendChild(noResultsMsg);
            }
        } else if (noResultsMsg) {
            noResultsMsg.remove();
        }
    }
    
    function updateFileStates(fileIds, action) {
        fileIds.forEach(id => {
            const row = document.querySelector(`[data-file-id="${id}"]`);
            if (row) {
                const toggleButton = row.querySelector('[data-action="active"]');
                if (toggleButton) {
                    const newState = action === 'activate';
                    updateToggleButton(toggleButton, newState, 'active');
                }
            }
        });
    }
});

// CSS 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slide-in {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slide-out {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .animate-slide-in { animation: slide-in 0.3s ease-out; }
    .animate-slide-out { animation: slide-out 0.3s ease-in; }
    
    .drag-handle { cursor: move; }
    
    .file-row.sortable-ghost {
        opacity: 0.4;
        background: #f3f4f6;
    }
`;
document.head.appendChild(style);
