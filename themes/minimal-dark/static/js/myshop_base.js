'use strict';

(function() {
  const mobileMenuButton = document.getElementById('mobile-menu-button');
  const mobileMenu = document.getElementById('mobile-menu');

  function setMenuState(open) {
    if (!mobileMenu) {
      return;
    }

    mobileMenu.classList.toggle('is-open', open);
    mobileMenu.setAttribute('aria-expanded', open ? 'true' : 'false');
    mobileMenu.setAttribute('aria-hidden', open ? 'false' : 'true');
    const icon = mobileMenuButton ? mobileMenuButton.querySelector('.icon') : null;

    if (icon) {
      icon.dataset.state = open ? 'open' : 'closed';
    }
  }

  if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.setAttribute('aria-expanded', 'false');
    mobileMenu.setAttribute('aria-hidden', 'true');

    mobileMenuButton.addEventListener('click', function(event) {
      event.preventDefault();
      const isOpen = !mobileMenu.classList.contains('is-open');
      setMenuState(isOpen);
    });

    mobileMenuButton.addEventListener('keydown', function(event) {
      if (event.key !== 'Enter' && event.key !== ' ') {
        return;
      }
      event.preventDefault();
      const isOpen = !mobileMenu.classList.contains('is-open');
      setMenuState(isOpen);
    });

    mobileMenu.querySelectorAll('a').forEach(function(link) {
      link.addEventListener('click', function() {
        setMenuState(false);
      });
    });
  }

  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      setMenuState(false);
    }
  });

  const mobileMenuTextOnly = document.querySelectorAll('.theme-toggle-text');
  const themeTextElements = document.querySelectorAll('.theme-text');
  if (themeTextElements.length && mobileMenuTextOnly.length) {
    const updateText = function(theme) {
      themeTextElements.forEach(function(element) {
        element.textContent = theme === 'dark' ? '라이트 모드' : '다크 모드';
      });
    };

    const savedTheme = localStorage.getItem('theme') || 'dark';
    updateText(savedTheme);

    window.addEventListener('load', function() {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
      updateText(currentTheme);
    });

    window.themeManager = window.themeManager || {};
    const previousApply = window.themeManager.apply;
    if (typeof previousApply === 'function') {
      window.themeManager.apply = function(theme) {
        previousApply.call(window.themeManager, theme);
        updateText(theme);
      };
    }
  }
})();
