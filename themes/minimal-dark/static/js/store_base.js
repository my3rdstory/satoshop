'use strict';

(function() {
  const mobileMenuButton = document.getElementById('store-mobile-menu-button');
  const mobileMenu = document.getElementById('store-mobile-menu');
  const bodyClass = document.body;

  if (!mobileMenuButton || !mobileMenu) {
    return;
  }

  function setStoreMenu(open) {
    mobileMenu.classList.toggle('is-open', open);
    mobileMenuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
    mobileMenu.setAttribute('aria-hidden', open ? 'false' : 'true');
  }

  mobileMenuButton.setAttribute('aria-expanded', 'false');
  mobileMenu.setAttribute('aria-hidden', 'true');

  function syncBodyScroll(open) {
    if (!bodyClass) {
      return;
    }

    if (open) {
      bodyClass.style.overflow = 'hidden';
    } else {
      bodyClass.style.overflow = '';
    }
  }

  mobileMenuButton.addEventListener('click', function(event) {
    event.preventDefault();
    const isOpen = !mobileMenu.classList.contains('is-open');
    setStoreMenu(isOpen);
    syncBodyScroll(isOpen);
  });

  mobileMenuButton.addEventListener('keydown', function(event) {
    if (event.key !== 'Enter' && event.key !== ' ') {
      return;
    }
    event.preventDefault();
    const isOpen = !mobileMenu.classList.contains('is-open');
    setStoreMenu(isOpen);
    syncBodyScroll(isOpen);
  });

  mobileMenu.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', function() {
      setStoreMenu(false);
      syncBodyScroll(false);
    });
  });

  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      setStoreMenu(false);
      syncBodyScroll(false);
    }
  });

  window.addEventListener('scroll', function() {
    const header = document.querySelector('.minimal-shell__header');
    if (!header) {
      return;
    }

    if (window.scrollY > 8) {
      header.style.boxShadow = '0 2px 20px rgba(0,0,0,0.18)';
    } else {
      header.style.boxShadow = 'none';
    }
  });
})();
