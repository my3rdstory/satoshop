// 공통 JavaScript 함수들

// 로그아웃 함수
function logout() {
  // CSRF 토큰 가져오기
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                   document.querySelector('meta[name=csrf-token]')?.getAttribute('content') ||
                   window.csrfToken;
  
  if (!csrfToken) {
    console.error('CSRF token not found');
    return;
  }

  // 폼을 동적으로 생성해서 POST 요청으로 로그아웃
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = window.logoutUrl || '/accounts/logout/';

  // CSRF 토큰 추가
  const csrfInput = document.createElement('input');
  csrfInput.type = 'hidden';
  csrfInput.name = 'csrfmiddlewaretoken';
  csrfInput.value = csrfToken;
  form.appendChild(csrfInput);

  // 로그아웃 후 홈페이지로 이동하도록 설정 (현재 페이지가 아닌)
  const nextInput = document.createElement('input');
  nextInput.type = 'hidden';
  nextInput.name = 'next';
  nextInput.value = window.homeUrl || '/';
  form.appendChild(nextInput);

  document.body.appendChild(form);
  form.submit();
}

// 로그인 페이지로 리다이렉트 (current URL을 next 파라미터로 전달)
function redirectToLogin() {
  const currentUrl = encodeURIComponent(window.location.pathname + window.location.search);
  const loginUrl = window.loginUrl || '/accounts/login/';
  window.location.href = loginUrl + "?next=" + currentUrl;
}

// 회원가입 페이지로 리다이렉트 (current URL을 next 파라미터로 전달)
function redirectToSignup() {
  const currentUrl = encodeURIComponent(window.location.pathname + window.location.search);
  const signupUrl = window.signupUrl || '/accounts/signup/';
  window.location.href = signupUrl + "?next=" + currentUrl;
}

// 드롭다운 메뉴 초기화 (데스크톱용)
function initDropdownMenus() {
  document.addEventListener('DOMContentLoaded', () => {
    // 드롭다운 메뉴들 (데스크톱)
    const dropdowns = document.querySelectorAll('.group');
    dropdowns.forEach(dropdown => {
      const button = dropdown.querySelector('button');
      const menu = dropdown.querySelector('div[class*="absolute"]');
      
      if (button && menu) {
        let timeout;
        
        dropdown.addEventListener('mouseenter', () => {
          clearTimeout(timeout);
          menu.classList.remove('opacity-0', 'invisible');
          menu.classList.add('opacity-100', 'visible');
        });
        
        dropdown.addEventListener('mouseleave', () => {
          timeout = setTimeout(() => {
            menu.classList.remove('opacity-100', 'visible');
            menu.classList.add('opacity-0', 'invisible');
          }, 150);
        });
      }
    });
  });
}

// 알림 메시지 자동 닫기
function initNotifications() {
  document.addEventListener('DOMContentLoaded', function () {
    // 닫기 버튼이 있는 알림들
    const notifications = document.querySelectorAll('[onclick*="parentElement.remove"]');
    
    // 3초 후 자동으로 알림 제거
    setTimeout(function () {
      const autoCloseNotifications = document.querySelectorAll('.bg-success-100, .bg-info-100, .bg-warning-100, .bg-error-100');
      autoCloseNotifications.forEach(function (notification) {
        if (notification.parentElement) {
          notification.style.transition = 'opacity 0.5s';
          notification.style.opacity = '0';
          setTimeout(function () {
            notification.remove();
          }, 500);
        }
      });
    }, 3000);
  });
}

// 초기화 함수들 실행
initDropdownMenus();
initNotifications();

// 플랫폼 네비게이션 초기화
document.addEventListener('DOMContentLoaded', () => {
  // 플랫폼 네비게이션 로드 완료
});

// 전역 공통 JavaScript 기능

// CSRF 토큰 가져오기 함수
function getCsrfToken() {
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  
  return cookieValue || window.csrfToken || document.querySelector('[name=csrfmiddlewaretoken]')?.value;
}

// 전역 변수로 설정
window.getCsrfToken = getCsrfToken;

// 공통 AJAX 설정
function setupAjaxDefaults() {
  // jQuery가 있는 경우
  if (typeof $ !== 'undefined') {
    $.ajaxSetup({
      beforeSend: function(xhr, settings) {
        if (!this.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", getCsrfToken());
        }
      }
    });
  }
  
  // Fetch API 래퍼
  window.fetchWithCsrf = function(url, options = {}) {
    return fetch(url, {
      ...options,
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
  };
}

// 사용자 테마 설정 감지 및 적용
function setupThemeDetection() {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
  
  function updateTheme(e) {
    if (e.matches) {
      document.body.classList.add('dark-theme');
      document.body.classList.remove('light-theme');
    } else {
      document.body.classList.add('light-theme');
      document.body.classList.remove('dark-theme');
    }
  }
  
  // 초기 테마 설정
  updateTheme(prefersDark);
  
  // 테마 변경 감지
  prefersDark.addListener(updateTheme);
}

// 반응형 네비게이션 토글
function setupResponsiveNavigation() {
  const mobileMenuButtons = document.querySelectorAll('[data-mobile-menu-toggle]');
  
  mobileMenuButtons.forEach(button => {
    button.addEventListener('click', function() {
      const targetId = this.getAttribute('data-target');
      const targetMenu = document.getElementById(targetId);
      
      if (targetMenu) {
        targetMenu.classList.toggle('hidden');
        
        // 아이콘 변경
        const icon = this.querySelector('i');
        if (icon) {
          if (targetMenu.classList.contains('hidden')) {
            icon.className = 'fas fa-bars';
          } else {
            icon.className = 'fas fa-times';
          }
        }
      }
    });
  });
}

// 외부 링크 처리
function setupExternalLinks() {
  const externalLinks = document.querySelectorAll('a[href^="http"]:not([href*="' + window.location.hostname + '"])');
  
  externalLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      // 외부 링크는 새 탭에서 열기
      this.target = '_blank';
      this.rel = 'noopener noreferrer';
    });
  });
}

// DOMContentLoaded 이벤트에서 초기화
document.addEventListener('DOMContentLoaded', function() {
  setupAjaxDefaults();
  setupThemeDetection();
  setupResponsiveNavigation();
  setupExternalLinks();
}); 