'use strict';

(function() {
  // ---------- Auth helpers ----------
  function getCsrfToken() {
    const cookiePair = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='));

    return (
      cookiePair?.split('=')[1] ||
      window.csrfToken ||
      document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
      ''
    );
  }

  function logout() {
    const csrfToken = getCsrfToken();

    if (!csrfToken) {
      console.error('CSRF token not found');
      return;
    }

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.logoutUrl || '/accounts/logout/';

    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);

    const nextInput = document.createElement('input');
    nextInput.type = 'hidden';
    nextInput.name = 'next';
    nextInput.value = window.homeUrl || '/';
    form.appendChild(nextInput);

    document.body.appendChild(form);
    form.submit();
  }

  function redirectToLogin() {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    const loginUrl = window.loginUrl || '/accounts/login/';
    window.location.href = `${loginUrl}?next=${next}`;
  }

  function redirectToSignup() {
    const next = encodeURIComponent(window.location.pathname + window.location.search);
    const signupUrl = window.signupUrl || '/accounts/signup/';
    window.location.href = `${signupUrl}?next=${next}`;
  }

  // ---------- Dropdowns ----------
  function initDropdownMenus() {
    document.querySelectorAll('.group').forEach((dropdown) => {
      const menu = dropdown.querySelector('div[class*="absolute"]');
      const button = dropdown.querySelector('button');

      if (!menu || !button) {
        return;
      }

      let timeoutId;
      dropdown.addEventListener('mouseenter', () => {
        clearTimeout(timeoutId);
        menu.classList.remove('opacity-0', 'invisible');
        menu.classList.add('opacity-100', 'visible');
      });

      dropdown.addEventListener('mouseleave', () => {
        timeoutId = setTimeout(() => {
          menu.classList.remove('opacity-100', 'visible');
          menu.classList.add('opacity-0', 'invisible');
        }, 160);
      });
    });
  }

  // ---------- CSRF/fetch defaults ----------
  function setupAjaxDefaults() {
    if (typeof $ !== 'undefined') {
      $.ajaxSetup({
        beforeSend: function(xhr, settings) {
          if (!this.crossDomain) {
            xhr.setRequestHeader('X-CSRFToken', getCsrfToken());
          }
        }
      });
    }

    window.fetchWithCsrf = function(url, options = {}) {
      return fetch(url, {
        ...options,
        headers: {
          'X-CSRFToken': getCsrfToken(),
          ...options.headers
        }
      });
    };
  }

  function initNotifications() {
    document.querySelectorAll('.bg-success-100, .bg-info-100, .bg-warning-100, .bg-error-100').forEach((notification) => {
      if (!notification.dataset.boundAutoClose) {
        notification.dataset.boundAutoClose = 'true';
        setTimeout(() => {
          notification.style.transition = 'opacity 0.5s';
          notification.style.opacity = '0';
          setTimeout(() => notification.remove(), 500);
        }, 3000);
      }
    });
  }

  function setupExternalLinks() {
    document.querySelectorAll('a[href^="http"]:not([href*="' + window.location.hostname + '"])').forEach((link) => {
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initDropdownMenus();
    initNotifications();
    setupAjaxDefaults();
    setupExternalLinks();
  });

  window.getCsrfToken = getCsrfToken;
  window.logout = logout;
  window.redirectToLogin = redirectToLogin;
  window.redirectToSignup = redirectToSignup;
})();
