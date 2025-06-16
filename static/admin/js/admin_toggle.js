/* Django Admin 사이드바 카테고리 토글 기능 JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Django Admin 사이드바 토글 기능
    const sidebar = document.querySelector('#nav-sidebar');
    if (!sidebar) {
        // 대안적 접근법 시도
        const potentialSidebars = [
            document.querySelector('div[role="navigation"]'),
            document.querySelector('.sidebar'),
            document.querySelector('#sidebar')
        ];
        
        for (let potential of potentialSidebars) {
            if (potential) {
                setupSidebarToggle(potential);
                break;
            }
        }
        return;
    }

    setupSidebarToggle(sidebar);
});

function setupSidebarToggle(sidebar) {
    // 사이드바 접기/펼치기 기능 설정
    
    // 토글 버튼 생성
    const toggleButton = document.createElement('button');
    toggleButton.innerHTML = '◀';
    toggleButton.className = 'sidebar-toggle-btn';
    toggleButton.style.cssText = `
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 9999;
        background: #417690;
        color: white;
        border: none;
        border-radius: 3px;
        padding: 5px 8px;
        cursor: pointer;
        font-size: 12px;
        transition: all 0.3s ease;
    `;
    
    document.body.appendChild(toggleButton);
    
    // 사이드바 토글 상태 관리
    let isCollapsed = localStorage.getItem('admin_sidebar_collapsed') === 'true';
    
    // 앱별 접기/펼치기 기능 추가
    const apps = sidebar.querySelectorAll('.app-label, .app-sidebar, .module');
    
    if (apps.length > 0) {
        apps.forEach((app, index) => setupAppToggle(app, index));
    }
    
    // 초기 상태 설정
    if (isCollapsed) {
        sidebar.style.left = '-200px';
        toggleButton.innerHTML = '▶';
        toggleButton.style.left = '10px';
    }
    
    // 토글 버튼 클릭 이벤트
    toggleButton.addEventListener('click', function() {
        isCollapsed = !isCollapsed;
        
        if (isCollapsed) {
            sidebar.style.left = '-200px';
            toggleButton.innerHTML = '▶';
            toggleButton.style.left = '10px';
        } else {
            sidebar.style.left = '0';
            toggleButton.innerHTML = '◀';
            toggleButton.style.left = '210px';
        }
        
        localStorage.setItem('admin_sidebar_collapsed', isCollapsed);
    });
    
    // 사이드바 호버 효과
    sidebar.addEventListener('mouseenter', function() {
        if (isCollapsed) {
            sidebar.style.left = '0';
        }
    });
    
    sidebar.addEventListener('mouseleave', function() {
        if (isCollapsed) {
            sidebar.style.left = '-200px';
        }
    });
}

function setupAppToggle(headerElement, index, appContainer = null) {
    // 앱별 토글 기능 설정
    
    // 앱 구조 찾기 (다양한 Django Admin 버전 호환)
    let app, appLabel, appList;
    
    if (headerElement.classList.contains('app-label')) {
        // Django 표준 구조
        appLabel = headerElement;
        app = headerElement.parentElement;
        appList = app.querySelector('.app-list, .model-list, ul');
    } else if (headerElement.classList.contains('module')) {
        // 대안 구조
        app = headerElement;
        appLabel = app.querySelector('h2, .section-header, .module-header');
        appList = app.querySelector('ul, .module-content');
    } else {
        // 일반적인 경우
        app = headerElement.closest('.app-sidebar, .module, .section');
        if (!app) {
            app = headerElement.parentElement;
        }
        appLabel = headerElement;
        appList = app ? app.querySelector('ul, .app-list, .model-list') : null;
    }
    
    if (!appLabel || !appList || !app) {
        return;
    }
    
    // 기본적으로 모든 앱을 닫힌 상태로 설정
    app.classList.add('app-collapsed');
    appList.style.display = 'none';
    
    // 클릭 이벤트 추가
    appLabel.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        // 토글 상태 변경
        app.classList.toggle('app-collapsed');
        
        // 상태를 로컬 스토리지에 저장
        const collapsed = app.classList.contains('app-collapsed');
        localStorage.setItem('admin_sidebar_app_' + index, collapsed);
        
        // 간단한 show/hide 토글
        if (collapsed) {
            appList.style.display = 'none';
        } else {
            appList.style.display = 'block';
        }
    });
    
    // 저장된 상태 복원
    const savedState = localStorage.getItem('admin_sidebar_app_' + index);
    if (savedState === 'false') {
        app.classList.remove('app-collapsed');
        appList.style.display = 'block';
    }
    
    // 스타일 개선
    appLabel.style.cursor = 'pointer';
    appLabel.style.userSelect = 'none';
    
    // 토글 아이콘 추가
    if (!appLabel.querySelector('.toggle-icon')) {
        const icon = document.createElement('span');
        icon.className = 'toggle-icon';
        icon.innerHTML = '▼';
        icon.style.cssText = `
            float: right;
            transition: transform 0.3s ease;
            font-size: 10px;
            margin-top: 2px;
        `;
        appLabel.appendChild(icon);
        
        // 접힌 상태일 때 아이콘 회전
        if (app.classList.contains('app-collapsed')) {
            icon.style.transform = 'rotate(-90deg)';
        }
        
        // 토글 시 아이콘 애니메이션
        appLabel.addEventListener('click', function() {
            if (app.classList.contains('app-collapsed')) {
                icon.style.transform = 'rotate(-90deg)';
            } else {
                icon.style.transform = 'rotate(0deg)';
            }
        });
    }
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