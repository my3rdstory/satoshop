/* Django Admin 사이드바 토글 기능 비활성화 */

document.addEventListener('DOMContentLoaded', function() {
    // 토글 기능을 비활성화하고 현재 페이지 하이라이트만 유지
    highlightCurrentMenu();
});

function setupSidebarToggle(sidebar) {
    // 토글 기능 비활성화됨
}

function setupAppToggle(headerElement, index, appContainer = null) {
    // 앱별 토글 기능 비활성화됨
}

// 현재 페이지 메뉴 하이라이트 개선
function highlightCurrentMenu() {
    const currentPath = window.location.pathname;
    const menuLinks = document.querySelectorAll('#nav-sidebar a, .sidebar a');
    
    menuLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.backgroundColor = '#79aec8';
            link.style.color = 'white';
            link.style.fontWeight = 'bold';
            
            // 상위 앱도 펼치기
            const parentApp = link.closest('.app-sidebar, .module');
            if (parentApp) {
                parentApp.classList.remove('app-collapsed');
                const appList = parentApp.querySelector('ul, .app-list');
                if (appList) {
                    appList.style.display = 'block';
                }
            }
        }
    });
}

// 비동기 콘텐츠 로딩 개선
function setupAsyncContentLoading() {
    const mainContent = document.querySelector('#content-main, .main-content, main');
    
    if (!mainContent) {
        return;
    }
    
    // 폼 제출 시 로딩 인디케이터
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitButton = form.querySelector('input[type="submit"], button[type="submit"]');
            if (submitButton) {
                const originalText = submitButton.value || submitButton.textContent;
                submitButton.value = '처리 중...';
                submitButton.textContent = '처리 중...';
                submitButton.disabled = true;
                
                // 5초 후 원래 상태로 복원 (타임아웃 방지)
                setTimeout(() => {
                    submitButton.value = originalText;
                    submitButton.textContent = originalText;
                    submitButton.disabled = false;
                }, 5000);
            }
        });
    });
}

// 키보드 단축키 추가
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+Shift+S: 사이드바 토글
        if (e.ctrlKey && e.shiftKey && e.key === 'S') {
            e.preventDefault();
            const toggleButton = document.querySelector('.sidebar-toggle-btn');
            if (toggleButton) {
                toggleButton.click();
            }
        }
        
        // Escape: 모달이나 드롭다운 닫기
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal, .popup, .dropdown-menu');
            modals.forEach(modal => {
                if (modal.style.display !== 'none') {
                    modal.style.display = 'none';
                }
            });
        }
    });
}

// URL 변경 감지 및 메뉴 업데이트
function setupURLChangeDetection() {
    let currentURL = window.location.href;
    
    setInterval(() => {
        if (window.location.href !== currentURL) {
            currentURL = window.location.href;
            highlightCurrentMenu();
        }
    }, 1000);
}

// 모든 기능 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 약간의 지연을 두고 실행 (DOM 완전 로드 보장)
    setTimeout(() => {
        highlightCurrentMenu();
        setupAsyncContentLoading();
        setupKeyboardShortcuts();
        setupURLChangeDetection();
    }, 100);
});

// 페이지 언로드 시 현재 메뉴 상태 업데이트
window.addEventListener('beforeunload', function() {
    const activeLink = document.querySelector('#nav-sidebar a[style*="background-color"], .sidebar a[style*="background-color"]');
    if (activeLink) {
        localStorage.setItem('admin_last_menu', activeLink.getAttribute('href'));
    }
});

// 페이지 로드 시 이전 메뉴 상태 복원
window.addEventListener('load', function() {
    const lastMenu = localStorage.getItem('admin_last_menu');
    if (lastMenu) {
        const menuLink = document.querySelector(`#nav-sidebar a[href="${lastMenu}"], .sidebar a[href="${lastMenu}"]`);
        if (menuLink) {
            menuLink.style.backgroundColor = '#79aec8';
            menuLink.style.color = 'white';
            menuLink.style.fontWeight = 'bold';
        }
    }
}); 