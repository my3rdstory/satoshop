// 테마 전환 기능
(function() {
    'use strict';
    
    // DOM 요소
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const html = document.documentElement;
    
    // 현재 테마 확인
    function getCurrentTheme() {
        return localStorage.getItem('theme') || 'light';
    }
    
    // 테마 적용
    function applyTheme(theme) {
        // Tailwind CSS 다크모드 클래스 적용
        if (theme === 'dark') {
            html.classList.add('dark');
            document.body.classList.add('dark');
        } else {
            html.classList.remove('dark');
            document.body.classList.remove('dark');
        }
        
        // 기존 data-theme 속성도 유지 (호환성)
        html.setAttribute('data-theme', theme);
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        // 아이콘 업데이트 (플로팅 버튼)
        if (themeIcon) {
            if (theme === 'dark') {
                themeIcon.className = 'fas fa-sun';
                themeToggle.title = '라이트 모드로 전환';
            } else {
                themeIcon.className = 'fas fa-moon';
                themeToggle.title = '다크 모드로 전환';
            }
        }
        
        // 기존 네비게이션 메뉴 아이템들 업데이트
        updateThemeMenuItems(theme);
    }
    
    // 테마 메뉴 아이템들 업데이트 (기존 코드와 호환)
    function updateThemeMenuItems(theme) {
        const themeMenuItems = document.querySelectorAll('.theme-toggle-menu-item');
        themeMenuItems.forEach(menuItem => {
            const sunIcon = menuItem.querySelector('.theme-sun-icon');
            const moonIcon = menuItem.querySelector('.theme-moon-icon');
            const themeText = menuItem.querySelector('.theme-text');

            if (theme === 'dark') {
                // 현재 다크모드이므로 라이트모드로 전환 가능함을 표시
                if (sunIcon) sunIcon.style.display = 'inline-block';
                if (moonIcon) moonIcon.style.display = 'none';
                if (themeText) themeText.textContent = '라이트 모드로';
            } else {
                // 현재 라이트모드이므로 다크모드로 전환 가능함을 표시
                if (sunIcon) sunIcon.style.display = 'none';
                if (moonIcon) moonIcon.style.display = 'inline-block';
                if (themeText) themeText.textContent = '다크 모드로';
            }
        });
    }
    
    // 테마 전환
    function toggleTheme() {
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
    }
    
    // 초기 테마 설정
    function initTheme() {
        const savedTheme = getCurrentTheme();
        
        // 시스템 다크 모드 감지 (저장된 설정이 없는 경우)
        if (!localStorage.getItem('theme')) {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const systemTheme = prefersDark ? 'dark' : 'light';
            applyTheme(systemTheme);
        } else {
            applyTheme(savedTheme);
        }
    }
    
    // 시스템 테마 변경 감지
    function watchSystemTheme() {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        
        mediaQuery.addEventListener('change', (e) => {
            // 사용자가 수동으로 설정한 테마가 없는 경우에만 시스템 테마 따라감
            if (!localStorage.getItem('theme')) {
                const systemTheme = e.matches ? 'dark' : 'light';
                applyTheme(systemTheme);
            }
        });
    }
    
    // 이벤트 리스너 등록
    function initEventListeners() {
        if (themeToggle) {
            themeToggle.addEventListener('click', toggleTheme);
            
            // 키보드 접근성
            themeToggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    toggleTheme();
                }
            });
        }
    }
    
    // 초기화
    function init() {
        initTheme();
        initEventListeners();
        watchSystemTheme();
    }
    
    // DOM 로드 완료 후 실행
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // 전역 함수로 노출 (기존 코드와 호환)
    window.toggleTheme = toggleTheme;
    window.themeToggle = {
        getCurrentTheme,
        applyTheme,
        toggleTheme
    };
})(); 