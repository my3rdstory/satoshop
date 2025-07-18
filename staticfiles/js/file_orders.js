// file_orders.js - 파일 주문 관리 페이지를 위한 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 요소 선택
    const searchInput = document.getElementById('order-search');
    const filterButtons = document.querySelectorAll('.filter-button');
    const dateRangeInputs = document.querySelectorAll('.date-range');
    const orderRows = document.querySelectorAll('.order-row');
    const exportButton = document.getElementById('export-orders');
    const detailModals = document.querySelectorAll('.order-detail-modal');
    const refreshButton = document.getElementById('refresh-orders');
    
    // 주문 검색 기능
    if (searchInput) {
        let searchTimer;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimer);
            const searchTerm = this.value.toLowerCase();
            
            searchTimer = setTimeout(() => {
                searchOrders(searchTerm);
            }, 300);
        });
    }
    
    // 주문 검색 함수
    function searchOrders(searchTerm) {
        orderRows.forEach(row => {
            const orderId = row.querySelector('.order-id')?.textContent.toLowerCase() || '';
            const customerEmail = row.querySelector('.customer-email')?.textContent.toLowerCase() || '';
            const fileName = row.querySelector('.file-name')?.textContent.toLowerCase() || '';
            
            const shouldShow = orderId.includes(searchTerm) || 
                               customerEmail.includes(searchTerm) || 
                               fileName.includes(searchTerm);
            
            row.style.display = shouldShow ? '' : 'none';
        });
        
        updateResultsCount();
    }
    
    // 필터 버튼 기능
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filter = this.dataset.filter;
            
            // 버튼 활성화 상태
            filterButtons.forEach(btn => {
                btn.classList.remove('bg-purple-500', 'text-white');
                btn.classList.add('bg-gray-200', 'text-gray-700');
            });
            this.classList.remove('bg-gray-200', 'text-gray-700');
            this.classList.add('bg-purple-500', 'text-white');
            
            applyFilter(filter);
        });
    });
    
    // 필터 적용
    function applyFilter(filter) {
        orderRows.forEach(row => {
            let shouldShow = true;
            
            switch(filter) {
                case 'paid':
                    shouldShow = row.querySelector('.status-paid') !== null;
                    break;
                case 'pending':
                    shouldShow = row.querySelector('.status-pending') !== null;
                    break;
                case 'downloaded':
                    shouldShow = row.querySelector('.downloaded-badge') !== null;
                    break;
                case 'expired':
                    shouldShow = row.querySelector('.expired-badge') !== null;
                    break;
                case 'all':
                default:
                    shouldShow = true;
            }
            
            row.style.display = shouldShow ? '' : 'none';
        });
        
        updateResultsCount();
    }
    
    // 날짜 범위 필터
    if (dateRangeInputs.length > 0) {
        // Flatpickr 초기화
        if (typeof flatpickr !== 'undefined') {
            flatpickr('.date-range', {
                mode: 'range',
                dateFormat: 'Y-m-d',
                locale: 'ko',
                onChange: function(selectedDates) {
                    if (selectedDates.length === 2) {
                        filterByDateRange(selectedDates[0], selectedDates[1]);
                    }
                }
            });
        }
    }
    
    // 날짜 범위로 필터링
    function filterByDateRange(startDate, endDate) {
        orderRows.forEach(row => {
            const orderDate = new Date(row.dataset.orderDate);
            const shouldShow = orderDate >= startDate && orderDate <= endDate;
            
            row.style.display = shouldShow ? '' : 'none';
        });
        
        updateResultsCount();
    }
    
    // 결과 개수 업데이트
    function updateResultsCount() {
        const visibleRows = document.querySelectorAll('.order-row:not([style*="display: none"])').length;
        const totalRows = orderRows.length;
        
        const countDisplay = document.getElementById('results-count');
        if (countDisplay) {
            countDisplay.textContent = `${visibleRows}/${totalRows}개 주문 표시`;
        }
    }
    
    // 주문 상세 모달
    document.querySelectorAll('.view-detail-btn').forEach(button => {
        button.addEventListener('click', function() {
            const orderId = this.dataset.orderId;
            showOrderDetail(orderId);
        });
    });
    
    // 주문 상세 표시
    function showOrderDetail(orderId) {
        // 로딩 표시
        showLoadingModal();
        
        fetch(`/file/api/order-detail/${orderId}/`)
            .then(response => response.json())
            .then(data => {
                hideLoadingModal();
                
                if (data.success) {
                    displayOrderDetailModal(data.order);
                } else {
                    showNotification('주문 정보를 불러올 수 없습니다.', 'error');
                }
            })
            .catch(error => {
                hideLoadingModal();
                console.error('주문 상세 로드 오류:', error);
                showNotification('네트워크 오류가 발생했습니다.', 'error');
            });
    }
    
    // 주문 상세 모달 표시
    function displayOrderDetailModal(order) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                <div class="p-6">
                    <div class="flex justify-between items-start mb-4">
                        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">주문 상세</h2>
                        <button class="close-modal text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                    
                    <div class="space-y-4">
                        <!-- 주문 정보 -->
                        <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            <h3 class="font-semibold text-gray-900 dark:text-white mb-2">주문 정보</h3>
                            <dl class="grid grid-cols-2 gap-2 text-sm">
                                <dt class="text-gray-600 dark:text-gray-400">주문 번호:</dt>
                                <dd class="font-mono">${order.order_id}</dd>
                                <dt class="text-gray-600 dark:text-gray-400">주문 일시:</dt>
                                <dd>${formatDate(order.created_at)}</dd>
                                <dt class="text-gray-600 dark:text-gray-400">상태:</dt>
                                <dd>${getStatusBadge(order.status)}</dd>
                                <dt class="text-gray-600 dark:text-gray-400">결제 금액:</dt>
                                <dd class="font-semibold">${order.amount} ${order.currency}</dd>
                            </dl>
                        </div>
                        
                        <!-- 파일 정보 -->
                        <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            <h3 class="font-semibold text-gray-900 dark:text-white mb-2">파일 정보</h3>
                            <dl class="grid grid-cols-2 gap-2 text-sm">
                                <dt class="text-gray-600 dark:text-gray-400">파일명:</dt>
                                <dd>${order.file_name}</dd>
                                <dt class="text-gray-600 dark:text-gray-400">크기:</dt>
                                <dd>${order.file_size}</dd>
                                <dt class="text-gray-600 dark:text-gray-400">다운로드 횟수:</dt>
                                <dd>${order.download_count}회</dd>
                                <dt class="text-gray-600 dark:text-gray-400">다운로드 만료:</dt>
                                <dd>${order.download_expires_at ? formatDate(order.download_expires_at) : '무제한'}</dd>
                            </dl>
                        </div>
                        
                        <!-- 구매자 정보 -->
                        <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            <h3 class="font-semibold text-gray-900 dark:text-white mb-2">구매자 정보</h3>
                            <dl class="grid grid-cols-2 gap-2 text-sm">
                                <dt class="text-gray-600 dark:text-gray-400">이메일:</dt>
                                <dd>${order.customer_email}</dd>
                                <dt class="text-gray-600 dark:text-gray-400">사용자명:</dt>
                                <dd>${order.customer_username || '-'}</dd>
                            </dl>
                        </div>
                        
                        <!-- 다운로드 기록 -->
                        ${order.download_logs ? `
                        <div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                            <h3 class="font-semibold text-gray-900 dark:text-white mb-2">다운로드 기록</h3>
                            <div class="space-y-2">
                                ${order.download_logs.map(log => `
                                    <div class="text-sm">
                                        <span class="text-gray-600 dark:text-gray-400">${formatDate(log.downloaded_at)}</span>
                                        <span class="text-gray-500">- IP: ${log.ip_address}</span>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                    </div>
                    
                    <div class="mt-6 flex justify-end space-x-3">
                        ${order.status === 'paid' && !order.is_expired ? `
                            <button onclick="resendDownloadLink('${order.order_id}')" 
                                    class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
                                <i class="fas fa-envelope mr-2"></i>다운로드 링크 재발송
                            </button>
                        ` : ''}
                        <button class="close-modal px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600">
                            닫기
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // 모달 닫기 이벤트
        modal.querySelectorAll('.close-modal').forEach(btn => {
            btn.addEventListener('click', () => {
                document.body.removeChild(modal);
            });
        });
        
        // 배경 클릭으로 닫기
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
        
        document.body.appendChild(modal);
    }
    
    // 다운로드 링크 재발송
    window.resendDownloadLink = function(orderId) {
        if (!confirm('다운로드 링크를 이메일로 재발송하시겠습니까?')) return;
        
        fetch('/file/api/resend-download-link/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ order_id: orderId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('다운로드 링크가 발송되었습니다.', 'success');
            } else {
                showNotification(data.error || '발송에 실패했습니다.', 'error');
            }
        })
        .catch(error => {
            console.error('링크 재발송 오류:', error);
            showNotification('네트워크 오류가 발생했습니다.', 'error');
        });
    };
    
    // 주문 내보내기
    if (exportButton) {
        exportButton.addEventListener('click', function() {
            const format = this.dataset.format || 'csv';
            const visibleOrderIds = Array.from(document.querySelectorAll('.order-row:not([style*="display: none"])'))
                .map(row => row.dataset.orderId);
            
            const params = new URLSearchParams({
                format: format,
                orders: visibleOrderIds.join(',')
            });
            
            window.location.href = `/file/export/orders/?${params.toString()}`;
        });
    }
    
    // 자동 새로고침
    if (refreshButton) {
        let autoRefreshInterval;
        let isAutoRefresh = false;
        
        refreshButton.addEventListener('click', function() {
            isAutoRefresh = !isAutoRefresh;
            
            if (isAutoRefresh) {
                this.classList.add('bg-green-500', 'text-white');
                this.innerHTML = '<i class="fas fa-sync fa-spin mr-2"></i>자동 새로고침 중';
                
                autoRefreshInterval = setInterval(() => {
                    refreshOrders();
                }, 30000); // 30초마다
            } else {
                this.classList.remove('bg-green-500', 'text-white');
                this.innerHTML = '<i class="fas fa-sync mr-2"></i>자동 새로고침';
                
                clearInterval(autoRefreshInterval);
            }
        });
    }
    
    // 주문 목록 새로고침
    function refreshOrders() {
        fetch(window.location.href, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newOrdersTable = doc.querySelector('#orders-table tbody');
            
            if (newOrdersTable) {
                document.querySelector('#orders-table tbody').innerHTML = newOrdersTable.innerHTML;
                
                // 이벤트 리스너 재등록
                reinitializeEventListeners();
                
                showNotification('주문 목록이 업데이트되었습니다.', 'info');
            }
        })
        .catch(error => {
            console.error('주문 새로고침 오류:', error);
        });
    }
    
    // 통계 차트
    const revenueChart = document.getElementById('revenue-chart');
    if (revenueChart && typeof Chart !== 'undefined') {
        fetch('/file/api/revenue-stats/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    new Chart(revenueChart.getContext('2d'), {
                        type: 'bar',
                        data: {
                            labels: data.labels,
                            datasets: [{
                                label: '매출 (sats)',
                                data: data.revenue,
                                backgroundColor: 'rgba(168, 85, 247, 0.5)',
                                borderColor: 'rgb(168, 85, 247)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }
            });
    }
    
    // 유틸리티 함수들
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    function getStatusBadge(status) {
        const badges = {
            'paid': '<span class="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs">결제완료</span>',
            'pending': '<span class="px-2 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs">대기중</span>',
            'cancelled': '<span class="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs">취소됨</span>',
            'expired': '<span class="px-2 py-1 bg-gray-100 text-gray-800 rounded-full text-xs">만료됨</span>'
        };
        return badges[status] || status;
    }
    
    function getCsrfToken() {
        const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
        return tokenElement ? tokenElement.value : '';
    }
    
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-6 py-4 rounded-lg shadow-lg max-w-md animate-slide-in z-50`;
        
        const colors = {
            success: 'bg-green-100 text-green-800',
            error: 'bg-red-100 text-red-800',
            info: 'bg-blue-100 text-blue-800'
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
    
    function showLoadingModal() {
        const modal = document.createElement('div');
        modal.id = 'loading-modal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
        modal.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg p-6">
                <i class="fas fa-spinner fa-spin text-4xl text-purple-500"></i>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    function hideLoadingModal() {
        const modal = document.getElementById('loading-modal');
        if (modal) {
            modal.remove();
        }
    }
    
    function reinitializeEventListeners() {
        // 상세보기 버튼 이벤트 재등록
        document.querySelectorAll('.view-detail-btn').forEach(button => {
            button.addEventListener('click', function() {
                const orderId = this.dataset.orderId;
                showOrderDetail(orderId);
            });
        });
    }
    
    // 초기 결과 개수 표시
    updateResultsCount();
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
`;
document.head.appendChild(style);