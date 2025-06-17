/* Django Admin 사이드바 메뉴 하이라이트 */

document.addEventListener('DOMContentLoaded', function() {
    highlightCurrentMenu();
});

// 현재 페이지 메뉴 하이라이트
function highlightCurrentMenu() {
    try {
        const currentPath = window.location.pathname;
        const menuLinks = document.querySelectorAll('a[href]');
        
        // 이전 하이라이트 제거
        menuLinks.forEach(link => {
            link.classList.remove('active', 'current');
            link.style.backgroundColor = '';
            link.style.color = '';
            link.style.fontWeight = '';
            
            const parentElement = link.closest('li, tr, th, td, .model');
            if (parentElement) {
                parentElement.classList.remove('active', 'current');
                parentElement.style.backgroundColor = '';
                parentElement.style.borderRadius = '';
                parentElement.style.margin = '';
            }
        });
        
        // 현재 페이지와 일치하는 링크 찾기
        let exactMatch = null;
        let partialMatch = null;
        
        menuLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (!href) return;
            
            if (href === currentPath) {
                exactMatch = link;
            } else if (currentPath.startsWith(href) && href.length > 1) {
                if (!partialMatch || href.length > partialMatch.getAttribute('href').length) {
                    partialMatch = link;
                }
            }
        });
        
        // 매칭된 링크 하이라이트
        const targetLink = exactMatch || partialMatch;
        if (targetLink) {
            targetLink.classList.add('current', 'active');
            
            const parentElement = targetLink.closest('li, tr, th, td, .model');
            if (parentElement) {
                parentElement.classList.add('current', 'active');
                
                // tr 요소인 경우 current-model 클래스도 추가
                if (parentElement.tagName.toLowerCase() === 'tr') {
                    parentElement.classList.add('current-model');
                }
            }
            
            // 상위 앱 펼치기
            const parentApp = targetLink.closest('.app, .module');
            if (parentApp) {
                parentApp.classList.remove('app-collapsed');
                const appList = parentApp.querySelector('ul, .app-list, tbody');
                if (appList) {
                    appList.style.display = 'block';
                }
            }
        }
    } catch (error) {
        console.error('메뉴 하이라이트 오류:', error);
    }
}

// 윈도우 로드 후에도 실행
window.addEventListener('load', function() {
    setTimeout(highlightCurrentMenu, 100);
});

// Ajax 페이지 변경 감지
if (window.history && window.history.pushState) {
    const originalPushState = window.history.pushState;
    window.history.pushState = function() {
        originalPushState.apply(this, arguments);
        setTimeout(highlightCurrentMenu, 100);
    };
} 