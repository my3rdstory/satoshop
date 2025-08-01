// 완전히 새로운 테마 전환 시스템
// 중복 로드 방지 - IIFE 사용
(function() {
  // 이미 로드되어 있으면 건너뛰기
  if (typeof window.ThemeManager !== 'undefined') {
    return;
  }

class ThemeManager {
    constructor() {
        // HTML에 이미 설정된 테마가 있으면 그것을 사용
        const presetTheme = document.documentElement.getAttribute('data-theme');
        this.currentTheme = presetTheme || this.getStoredTheme() || this.getSystemTheme();
        this.isInitialized = false;
        this.init();
    }

    // 저장된 테마 가져오기
    getStoredTheme() {
        try {
            return localStorage.getItem('theme');
        } catch (e) {
            console.warn('localStorage 접근 실패:', e);
            return null;
        }
    }

    // 시스템 테마 감지
    getSystemTheme() {
        try {
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        } catch (e) {
            return 'light';
        }
    }

    // 테마 저장
    saveTheme(theme) {
        try {
            localStorage.setItem('theme', theme);
        } catch (e) {
            console.warn('localStorage 저장 실패:', e);
        }
    }

    // 테마 적용
    applyTheme(theme) {
        const html = document.documentElement;
        const body = document.body;

        // 클래스 제거
        html.classList.remove('dark', 'light');
        body.classList.remove('dark', 'light');

        // 새 클래스 추가
        if (theme === 'dark') {
            html.classList.add('dark');
            body.classList.add('dark');
        } else {
            html.classList.add('light');
            body.classList.add('light');
        }

        // data-theme 속성 설정 (호환성)
        html.setAttribute('data-theme', theme);
        body.setAttribute('data-theme', theme);

        // 테마 저장
        this.saveTheme(theme);
        this.currentTheme = theme;

        // 플로팅 버튼 업데이트
        this.updateFloatingButton(theme);

        // 메뉴 아이템 업데이트
        this.updateMenuItems(theme);
    }

    // 플로팅 버튼 업데이트
    updateFloatingButton(theme) {
        const themeToggle = document.getElementById('theme-toggle');
        const themeIcon = document.getElementById('theme-icon');

        if (themeToggle && themeIcon) {
            if (theme === 'dark') {
                themeIcon.className = 'fas fa-sun';
                themeToggle.title = '라이트 모드로 전환';
            } else {
                themeIcon.className = 'fas fa-moon';
                themeToggle.title = '다크 모드로 전환';
            }
        }
    }

    // 메뉴 아이템들 업데이트
    updateMenuItems(theme) {
        const menuItems = document.querySelectorAll('.theme-toggle-menu-item');
        
        menuItems.forEach(item => {
            const sunIcon = item.querySelector('.theme-sun-icon');
            const moonIcon = item.querySelector('.theme-moon-icon');
            const text = item.querySelector('.theme-text');

            if (theme === 'dark') {
                // 다크 모드 → 라이트 모드로 변경 가능
                if (sunIcon) sunIcon.style.display = 'inline-block';
                if (moonIcon) moonIcon.style.display = 'none';
                if (text) text.textContent = '라이트 모드로';
            } else {
                // 라이트 모드 → 다크 모드로 변경 가능
                if (sunIcon) sunIcon.style.display = 'none';
                if (moonIcon) moonIcon.style.display = 'inline-block';
                if (text) text.textContent = '다크 모드로';
            }
        });
    }

    // 테마 토글
    toggle() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
    }

    // 초기화
    init() {
        if (this.isInitialized) return;
        
        // 현재 설정된 테마와 원하는 테마가 다를 때만 적용
        const currentDataTheme = document.documentElement.getAttribute('data-theme');
        if (currentDataTheme !== this.currentTheme) {
            this.applyTheme(this.currentTheme);
        } else {
            // 이미 올바른 테마가 설정되어 있으므로 UI만 업데이트
            this.updateFloatingButton(this.currentTheme);
            this.updateMenuItems(this.currentTheme);
        }
        
        // 시스템 테마 변경 감지
        this.watchSystemTheme();
        
        this.isInitialized = true;
    }

    // 시스템 테마 변경 감지
    watchSystemTheme() {
        try {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                // 사용자가 수동으로 설정하지 않은 경우에만 시스템 테마 따라감
                if (!this.getStoredTheme()) {
                    const systemTheme = e.matches ? 'dark' : 'light';
                    this.applyTheme(systemTheme);
                }
            });
        } catch (e) {
            console.warn('시스템 테마 감지 실패:', e);
        }
    }
}

// 전역 인스턴스 생성
let themeManager;

// DOM 로드 완료 후 초기화
function initThemeSystem() {
    if (!themeManager) {
        themeManager = new ThemeManager();
    }
}

// 전역 함수 (하위 호환성)
window.toggleTheme = function() {
    if (!themeManager) {
        initThemeSystem();
    }
    themeManager.toggle();
};

// 다양한 초기화 시점 지원
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThemeSystem);
} else {
    initThemeSystem();
}

// 추가 안전장치
window.addEventListener('load', function() {
    if (!themeManager) {
        initThemeSystem();
    }
});

// 전역 접근용 (디버깅/테스트용)
window.themeManager = {
    get current() { return themeManager?.currentTheme || 'light'; },
    toggle: () => window.toggleTheme(),
    apply: (theme) => themeManager?.applyTheme(theme)
};

// ThemeManager 클래스를 전역에 등록
window.ThemeManager = ThemeManager;

})(); // IIFE 닫기 