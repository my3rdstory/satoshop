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

  // next 파라미터 추가
  const nextInput = document.createElement('input');
  nextInput.type = 'hidden';
  nextInput.name = 'next';
  nextInput.value = window.location.pathname + window.location.search;
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

// 플랫폼 네비게이션 로드 완료 로그
document.addEventListener('DOMContentLoaded', () => {
  console.log('Platform navigation loaded');
}); 