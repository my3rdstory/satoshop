/* Django Admin 사이드바 카테고리 토글 기능 JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin toggle script loaded');
    
    // 페이지 로드 후 약간의 지연을 두고 실행 (DOM이 완전히 로드되도록)
    setTimeout(function() {
        initSidebarToggle();
        initAsyncMenuLoading();
        highlightCurrentMenu(); // 현재 메뉴 하이라이트 추가
    }, 100);
});

function initSidebarToggle() {
    // 다양한 사이드바 셀렉터 시도
    const sidebar = document.querySelector('#nav-sidebar') || 
                   document.querySelector('.sidebar') || 
                   document.querySelector('#navigation') ||
                   document.querySelector('.navigation') ||
                   document.querySelector('[id*="nav"]') ||
                   document.querySelector('[class*="sidebar"]');
    
    if (!sidebar) {
        console.log('Sidebar not found, trying alternative approach');
        // 대안: 전체 문서에서 앱 구조 찾기
        findAndSetupApps();
        return;
    }
    
    console.log('Sidebar found:', sidebar);
    
    // 앱 구조 찾기 및 설정
    setupSidebarApps(sidebar);
}

function findAndSetupApps() {
    // Django 어드민의 일반적인 앱 구조 패턴 찾기
    const possibleAppContainers = document.querySelectorAll('div[class*="app"], .module, [id*="app"]');
    
    possibleAppContainers.forEach(function(container, index) {
        const header = container.querySelector('h2, .app-label, a[class*="section"]') ||
                      container.querySelector('a:first-child');
        
        if (header && header.textContent.includes('관리')) {
            setupAppToggle(header, index, container);
        }
    });
}

function setupSidebarApps(sidebar) {
    // 다양한 앱 셀렉터 시도
    let apps = sidebar.querySelectorAll('.app');
    
    if (apps.length === 0) {
        apps = sidebar.querySelectorAll('.module');
    }
    
    if (apps.length === 0) {
        apps = sidebar.querySelectorAll('div:has(h2), div:has(.app-label)');
    }
    
    console.log('Found apps:', apps.length);
    
    if (apps.length === 0) {
        // 최후의 수단: h2나 링크 요소들을 직접 찾기
        const headers = sidebar.querySelectorAll('h2, a[href*="admin"]');
        headers.forEach(function(header, index) {
            if (header.textContent.includes('관리')) {
                setupAppToggle(header, index);
            }
        });
        return;
    }
    
    apps.forEach(function(app, index) {
        setupAppToggle(null, index, app);
    });
}

function setupAppToggle(headerElement, index, appContainer = null) {
    let appLabel, appList, app;
    
    if (headerElement && !appContainer) {
        // 헤더 요소가 주어진 경우
        appLabel = headerElement;
        app = headerElement.closest('.app') || 
              headerElement.closest('.module') || 
              headerElement.parentElement;
        
        // 리스트 찾기
        appList = app.querySelector('ul') || 
                 app.querySelector('.app-list') ||
                 headerElement.nextElementSibling;
        
        // 다음 형제 요소들 중에서 ul 찾기
        if (!appList) {
            let sibling = headerElement.nextElementSibling;
            while (sibling) {
                if (sibling.tagName === 'UL' || sibling.querySelector('a')) {
                    appList = sibling;
                    break;
                }
                sibling = sibling.nextElementSibling;
            }
        }
    } else if (appContainer) {
        // 앱 컨테이너가 주어진 경우
        app = appContainer;
        appLabel = app.querySelector('a.section') || 
                  app.querySelector('h2') || 
                  app.querySelector('.app-label') ||
                  app.querySelector('a:first-child');
        
        // Django 어드민의 실제 구조에 맞게 리스트 찾기
        appList = app.querySelector('ul') || 
                 app.querySelector('.app-list');
        
        // a.section 다음에 오는 모든 요소들을 찾기
        if (!appList && appLabel) {
            let sibling = appLabel.nextElementSibling;
            while (sibling) {
                if (sibling.tagName === 'UL' || 
                    sibling.classList.contains('app-list') ||
                    sibling.querySelector('a[href*="admin"]')) {
                    appList = sibling;
                    break;
                }
                sibling = sibling.nextElementSibling;
            }
            
            // 여전히 찾지 못했다면 app 내의 모든 링크들을 포함하는 컨테이너 찾기
            if (!appList) {
                const links = app.querySelectorAll('a[href*="admin"]:not(.section)');
                if (links.length > 0) {
                    // 링크들의 공통 부모 찾기
                    let commonParent = links[0].parentElement;
                    for (let i = 1; i < links.length; i++) {
                        while (!commonParent.contains(links[i])) {
                            commonParent = commonParent.parentElement;
                        }
                    }
                    appList = commonParent;
                }
            }
        }
    }
    
    console.log(`Debug app ${index}:`, {
        appLabel: appLabel,
        appLabelText: appLabel ? appLabel.textContent : 'null',
        appList: appList,
        appListTag: appList ? appList.tagName : 'null',
        app: app,
        appClass: app ? app.className : 'null'
    });
    
    if (!appLabel || !appList || !app) {
        console.log(`Setup failed for app ${index}:`, {appLabel, appList, app});
        return;
    }
    
    console.log(`Setting up toggle for app ${index}:`, appLabel.textContent);
    
    // 기본적으로 모든 앱을 닫힌 상태로 설정
    app.classList.add('app-collapsed');
    appList.style.display = 'none';
    
    // 클릭 이벤트 추가
    appLabel.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log(`Toggling app ${index}:`, appLabel.textContent);
        
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
}

function highlightCurrentMenu() {
    const currentUrl = window.location.pathname;
    const sidebar = document.querySelector('#nav-sidebar') || 
                   document.querySelector('.sidebar') || 
                   document.querySelector('#navigation');
    
    if (!sidebar) return;
    
    // 모든 메뉴 링크에서 활성 상태 제거
    const allLinks = sidebar.querySelectorAll('a');
    allLinks.forEach(link => {
        link.classList.remove('active', 'current');
        link.parentElement.classList.remove('active', 'current');
    });
    
    // 현재 URL과 일치하는 링크 찾기
    let activeLink = null;
    let bestMatch = '';
    
    allLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentUrl.includes(href) && href.length > bestMatch.length) {
            bestMatch = href;
            activeLink = link;
        }
    });
    
    // 정확한 매치를 찾지 못했다면 부분 매치 시도
    if (!activeLink) {
        allLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && href !== '/admin/' && currentUrl.startsWith(href)) {
                if (!activeLink || href.length > activeLink.getAttribute('href').length) {
                    activeLink = link;
                }
            }
        });
    }
    
    if (activeLink) {
        updateActiveMenu(activeLink);
        console.log('Current menu highlighted:', activeLink.textContent.trim());
    }
}

function initAsyncMenuLoading() {
    // 어드민 메뉴 링크들에 비동기 로딩 기능 추가
    const sidebar = document.querySelector('#nav-sidebar') || 
                   document.querySelector('.sidebar') || 
                   document.querySelector('#navigation');
    
    if (!sidebar) return;
    
    // 메인 콘텐츠 영역 찾기
    const mainContent = document.querySelector('#content-main') || 
                       document.querySelector('.main') ||
                       document.querySelector('#main');
    
    if (!mainContent) {
        console.log('Main content area not found, async loading disabled');
        return;
    }
    
    // 사이드바의 모든 링크에 이벤트 리스너 추가
    const menuLinks = sidebar.querySelectorAll('a[href*="/admin/"]');
    
    menuLinks.forEach(function(link) {
        // 이미 처리된 링크는 스킵
        if (link.hasAttribute('data-async-processed')) return;
        
        link.setAttribute('data-async-processed', 'true');
        
        link.addEventListener('click', function(e) {
            // 특정 링크들은 비동기 로딩 제외 (로그아웃, 비밀번호 변경 등)
            const href = link.getAttribute('href');
            if (href.includes('logout') || 
                href.includes('password') || 
                href.includes('login') ||
                link.target === '_blank') {
                return; // 기본 동작 유지
            }
            
            e.preventDefault();
            
            // 로딩 표시
            showLoadingIndicator(mainContent);
            
            // 현재 활성 메뉴 상태 업데이트
            updateActiveMenu(link);
            
            // 비동기로 페이지 로드
            loadPageAsync(href, mainContent);
        });
    });
}

function showLoadingIndicator(container) {
    container.innerHTML = `
        <div style="display: flex; justify-content: center; align-items: center; height: 200px;">
            <div style="text-align: center;">
                <div style="border: 4px solid #f3f3f3; border-top: 4px solid #007cba; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px;"></div>
                <p style="color: #666;">로딩 중...</p>
            </div>
        </div>
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    `;
}

function updateActiveMenu(activeLink) {
    const sidebar = document.querySelector('#nav-sidebar') || 
                   document.querySelector('.sidebar') || 
                   document.querySelector('#navigation');
    
    if (!sidebar) return;
    
    // 모든 메뉴 링크에서 active 클래스 제거
    const allLinks = sidebar.querySelectorAll('a');
    allLinks.forEach(link => {
        link.classList.remove('active', 'current');
        link.parentElement.classList.remove('active', 'current');
        
        // 부모 li 요소도 확인
        const parentLi = link.closest('li');
        if (parentLi) {
            parentLi.classList.remove('active', 'current');
        }
    });
    
    // 클릭된 링크에 active 클래스 추가
    activeLink.classList.add('active', 'current');
    activeLink.parentElement.classList.add('active', 'current');
    
    // 부모 li 요소에도 추가
    const parentLi = activeLink.closest('li');
    if (parentLi) {
        parentLi.classList.add('active', 'current');
    }
    
    // 부모 앱도 펼치기
    const parentApp = activeLink.closest('.app');
    if (parentApp) {
        parentApp.classList.remove('app-collapsed');
        const appList = parentApp.querySelector('ul, .app-list');
        if (appList) {
            appList.style.display = 'block';
        }
        
        // 앱 헤더에도 활성 표시
        const appHeader = parentApp.querySelector('.app-label, a.section, h2');
        if (appHeader) {
            appHeader.classList.add('app-active');
        }
    }
    
    console.log('Active menu updated:', activeLink.textContent.trim());
}

function loadPageAsync(url, container) {
    fetch(url, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.text();
    })
    .then(html => {
        // HTML 파싱하여 메인 콘텐츠만 추출
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // 메인 콘텐츠 영역 찾기
        const newContent = doc.querySelector('#content-main') || 
                          doc.querySelector('.main') ||
                          doc.querySelector('#main') ||
                          doc.querySelector('body');
        
        if (newContent) {
            container.innerHTML = newContent.innerHTML;
            
            // 새로 로드된 콘텐츠의 스크립트 실행
            executeScripts(container);
            
            // URL 업데이트 (브라우저 히스토리)
            history.pushState({}, '', url);
            
            // 페이지 제목 업데이트
            const title = doc.querySelector('title');
            if (title) {
                document.title = title.textContent;
            }
            
            // 새 페이지 로드 후 메뉴 하이라이트 업데이트
            setTimeout(highlightCurrentMenu, 100);
        } else {
            throw new Error('콘텐츠를 찾을 수 없습니다.');
        }
    })
    .catch(error => {
        console.error('페이지 로드 실패:', error);
        container.innerHTML = `
            <div style="padding: 20px; text-align: center; color: #d63384;">
                <h3>페이지 로드 실패</h3>
                <p>${error.message}</p>
                <button onclick="location.reload()" style="padding: 8px 16px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    페이지 새로고침
                </button>
            </div>
        `;
    });
}

function executeScripts(container) {
    // 새로 로드된 콘텐츠의 스크립트 태그들을 실행
    const scripts = container.querySelectorAll('script');
    scripts.forEach(script => {
        if (script.src) {
            // 외부 스크립트
            const newScript = document.createElement('script');
            newScript.src = script.src;
            document.head.appendChild(newScript);
        } else {
            // 인라인 스크립트
            try {
                eval(script.textContent);
            } catch (e) {
                console.warn('스크립트 실행 실패:', e);
            }
        }
    });
}

// 브라우저 뒤로가기/앞으로가기 지원
window.addEventListener('popstate', function(event) {
    // 뒤로가기/앞으로가기 시에도 메뉴 하이라이트 업데이트
    setTimeout(highlightCurrentMenu, 100);
});

// 사이드바 앱 라벨을 일반 텍스트로 변경 (링크 제거)
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.querySelector('#nav-sidebar');
    if (!sidebar) return;
    
    const appLabels = sidebar.querySelectorAll('.app-label');
    appLabels.forEach(function(label) {
        // 링크를 일반 div로 변경
        if (label.tagName === 'A') {
            const newLabel = document.createElement('div');
            newLabel.className = label.className;
            newLabel.textContent = label.textContent;
            newLabel.style.cssText = label.style.cssText;
            
            label.parentNode.replaceChild(newLabel, label);
        }
    });
}); 