'use strict';

(function() {
  const FEATHER_SPRITE_URL = window.__featherSpriteUrl || '/static/icons/feather/feather-sprite.svg';
  const ICON_OBSERVER_TARGET_SELECTORS = ['i.fa', 'i.fas', 'i.far', 'i.fab'];
  const DEFAULT_ICON_REPLACEMENTS = new Map([
    ['arrow-left', 'arrow-left'],
    ['arrow-right', 'arrow-right'],
    ['arrow-down', 'arrow-down'],
    ['arrow-up', 'arrow-up'],
    ['angle-left', 'arrow-left'],
    ['angle-right', 'arrow-right'],
    ['angle-double-left', 'chevrons-left'],
    ['angle-double-right', 'chevrons-right'],
    ['chevron-left', 'chevron-left'],
    ['chevron-right', 'chevron-right'],
    ['caret-left', 'chevron-left'],
    ['caret-right', 'chevron-right'],
    ['chevron-up', 'chevron-up'],
    ['chevron-down', 'chevron-down'],
    ['check', 'check'],
    ['check-circle', 'check-circle'],
    ['times', 'x'],
    ['times-circle', 'x-circle'],
    ['window-close', 'x'],
    ['plus', 'plus'],
    ['minus', 'minus'],
    ['search', 'search'],
    ['edit', 'edit-3'],
    ['pencil-alt', 'edit-3'],
    ['user', 'user'],
    ['users', 'users'],
    ['user-circle', 'user'],
    ['user-plus', 'user-plus'],
    ['user-check', 'user-check'],
    ['phone', 'phone'],
    ['envelope', 'mail'],
    ['envelope-open', 'mail'],
    ['map-marker-alt', 'map-pin'],
    ['map-pin', 'map-pin'],
    ['store', 'shopping-bag'],
    ['store-alt', 'shopping-bag'],
    ['shopping-bag', 'shopping-bag'],
    ['shopping-cart', 'shopping-cart'],
    ['home', 'home'],
    ['key', 'key'],
    ['lock', 'lock'],
    ['unlock', 'unlock'],
    ['calendar', 'calendar'],
    ['calendar-alt', 'calendar'],
    ['calendar-check', 'calendar-check'],
    ['calendar-plus', 'calendar'],
    ['calendar-minus', 'calendar'],
    ['calendar-times', 'calendar'],
    ['calendar-day', 'calendar'],
    ['gift', 'gift'],
    ['box', 'box'],
    ['box-open', 'box'],
    ['receipt', 'file-text'],
    ['file', 'file'],
    ['file-alt', 'file-text'],
    ['file-text', 'file-text'],
    ['folder', 'folder'],
    ['folder-open', 'folder'],
    ['download', 'download'],
    ['upload', 'upload'],
    ['image', 'image'],
    ['camera', 'camera'],
    ['bolt', 'zap'],
    ['bitcoin-sign', 'zap'],
    ['wallet', 'credit-card'],
    ['credit-card', 'credit-card'],
    ['bar-chart', 'bar-chart-2'],
    ['chart-bar', 'bar-chart-2'],
    ['bell', 'bell'],
    ['cog', 'settings'],
    ['cogs', 'settings'],
    ['tools', 'settings'],
    ['palette', 'droplet'],
    ['info-circle', 'info'],
    ['question-circle', 'help-circle'],
    ['exclamation-circle', 'alert-circle'],
    ['exclamation-triangle', 'alert-triangle'],
    ['exclamation', 'alert-triangle'],
    ['exclamation-square', 'alert-triangle'],
    ['truck', 'truck'],
    ['shipping-fast', 'truck'],
    ['clock', 'clock'],
    ['history', 'clock'],
    ['bell', 'bell'],
    ['heart', 'heart'],
    ['heart-pulse', 'activity'],
    ['heart-broken', 'heart'],
    ['flag-checkered', 'flag'],
    ['flag', 'flag'],
    ['barcode', 'hash'],
    ['barcode-alt', 'hash'],
    ['barcode', 'hash'],
    ['link', 'link-2'],
    ['external-link-alt', 'external-link'],
    ['external-link-square-alt', 'external-link'],
    ['eye', 'eye'],
    ['eye-slash', 'eye-off'],
    ['video', 'video'],
    ['video-slash', 'video-off'],
    ['pause', 'pause'],
    ['play', 'play'],
    ['copy', 'copy'],
    ['paste', 'clipboard'],
    ['trash', 'trash-2'],
    ['trash-alt', 'trash-2'],
    ['check-square', 'check-square'],
    ['square', 'square'],
    ['bookmark', 'bookmark'],
    ['bookmark-o', 'bookmark'],
    ['undo', 'corner-up-left'],
    ['redo', 'corner-up-right'],
    ['list', 'list'],
    ['list-alt', 'list'],
    ['clipboard-list', 'list'],
    ['tasks', 'check-square'],
    ['spinner', 'refresh-cw'],
    ['sync', 'refresh-cw'],
    ['sync-alt', 'refresh-cw'],
    ['redo-alt', 'corner-up-right'],
    ['undo-alt', 'corner-up-left'],
    ['filter', 'filter'],
    ['gift', 'gift'],
    ['headset', 'headphones'],
    ['bug', 'alert-octagon'],
    ['ban', 'x'],
    ['close', 'x'],
    ['sign-in-alt', 'log-in'],
    ['sign-out-alt', 'log-out'],
    ['sign-in', 'log-in'],
    ['sign-out', 'log-out'],
    ['mobile-alt', 'smartphone'],
    ['desktop', 'monitor'],
    ['laptop', 'monitor'],
    ['qrcode', 'qr-code'],
    ['barcode', 'hash'],
    ['coins', 'dollar-sign'],
    ['money-bill-wave', 'dollar-sign'],
    ['money-bill', 'dollar-sign'],
    ['money-check-alt', 'check-square'],
    ['star', 'star'],
    ['star-half', 'star'],
    ['fire', 'flame'],
    ['smile', 'smile'],
    ['meh', 'meh'],
    ['grin', 'smile'],
    ['comment', 'message-circle'],
    ['comments', 'message-circle'],
    ['paper-plane', 'send'],
    ['paperclip', 'paperclip'],
    ['share', 'share-2'],
    ['share-alt', 'share-2'],
    ['times-hexagon', 'x-octagon'],
    ['search-plus', 'search'],
    ['search-minus', 'search'],
    ['shield-alt', 'shield'],
    ['shield', 'shield'],
    ['user-tie', 'user'],
    ['users-slash', 'users'],
    ['user-clock', 'clock'],
    ['crown', 'award'],
    ['award', 'award'],
    ['id-badge', 'tag'],
    ['tag', 'tag'],
    ['tags', 'tags'],
    ['map', 'map'],
    ['wifi', 'wifi'],
    ['camera-retro', 'camera'],
    ['expand', 'maximize'],
    ['compress', 'minimize'],
    ['plus-circle', 'plus-circle'],
    ['minus-circle', 'minus-circle'],
    ['check-circle', 'check-circle'],
    ['certificate', 'award'],
    ['book-open', 'book-open'],
    ['book', 'book-open'],
    ['newspaper', 'newspaper'],
    ['newspaper-o', 'newspaper'],
    ['folder-plus', 'folder-plus'],
    ['folder-minus', 'folder-minus'],
    ['folder-open', 'folder'],
    ['file-download', 'download'],
    ['file-upload', 'upload'],
    ['download', 'download'],
    ['upload', 'upload'],
    ['link', 'link-2'],
    ['user-secret', 'users'],
    ['bitcoin', 'circle'],
    ['bitcoins', 'circle']
  ]);

  const themeIconLabels = {
    dark: '다크 모드',
    light: '라이트 모드'
  };

  let isLegacyObserverStarted = false;

  function getFeatherSpriteHref() {
    return window.__featherSpriteUrl || FEATHER_SPRITE_URL;
  }

  function hasFaMarker(token) {
    return token === 'fa' || token === 'fas' || token === 'far' || token === 'fab';
  }

  function normalizeIconToken(token) {
    if (!token || !token.startsWith('fa-')) {
      return '';
    }

    const normalized = token.replace(/^fa-/, '');
    if (normalized === 'spin' || normalized === 'pulse' || normalized === '2x' || normalized === 'lg') {
      return '';
    }
    return normalized;
  }

  function getLegacyIconInfo(classList) {
    const tokens = Array.from(classList || []);
    let name = '';
    let spin = false;

    for (const token of tokens) {
      if (token === 'fa-spin' || token === 'fa-pulse') {
        spin = true;
      }
    }

    for (const token of tokens) {
      if (!token || token.startsWith('fa-') === false) {
        continue;
      }
      if (hasFaMarker(token) || token === 'fa-spin' || token === 'fa-pulse') {
        continue;
      }

      const normalized = normalizeIconToken(token);
      if (normalized) {
        name = normalized;
        break;
      }
    }

    return { name, spin };
  }

  function toFeatherName(iconName) {
    if (!iconName) {
      return '';
    }
    return DEFAULT_ICON_REPLACEMENTS.get(iconName) || iconName;
  }

  function setFeatherUseTarget(svg, iconName) {
    if (!(svg instanceof SVGElement)) {
      return;
    }

    const name = toFeatherName(iconName);
    const fallback = 'circle';
    const finalName = name || fallback;
    const use = svg.querySelector('use');
    const href = `${getFeatherSpriteHref()}#${finalName}`;

    if (use) {
      use.setAttribute('href', href);
      use.setAttribute('xlink:href', href);
      return;
    }

    const freshUse = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    freshUse.setAttribute('href', href);
    freshUse.setAttribute('xlink:href', href);
    svg.appendChild(freshUse);
  }

  function createFeatherIconElement(className, isSpinning) {
    const svgNs = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNs, 'svg');

    if (className) {
      const tokens = className
        .split(/\s+/)
        .filter(Boolean);
      svg.classList.add(...tokens);
    }

    if (!svg.classList.contains('icon')) {
      svg.classList.add('icon');
    }

    if (isSpinning) {
      svg.classList.add('is-spinning');
    }

    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    return svg;
  }

  function convertLegacyIconElement(icon) {
    if (!(icon instanceof HTMLElement)) {
      return;
    }

    const iconTokens = icon.classList;
    if (!Array.from(iconTokens).some((token) => hasFaMarker(token))) {
      return;
    }

    if (icon.dataset.legacyIconProcessed || icon.dataset.legacyIcon) {
      return;
    }

    const { name, spin } = getLegacyIconInfo(iconTokens);
    if (!name) {
      return;
    }

    const keepClasses = Array.from(iconTokens)
      .filter((token) => token && !token.startsWith('fa-') && !hasFaMarker(token))
      .join(' ');

    const svg = createFeatherIconElement(keepClasses, spin);
    svg.dataset.legacyIcon = name;
    svg.dataset.legacyIconProcessed = '1';
    svg.dataset.legacySpinning = spin ? '1' : '0';
    setFeatherUseTarget(svg, name);
    icon.replaceWith(svg);
  }

function refreshLegacySvgIcon(svg) {
    if (!(svg instanceof SVGElement) || !svg.dataset.legacyIconProcessed) {
      return;
    }

    const { name, spin } = getLegacyIconInfo(svg.classList);
    const baseName = name || svg.dataset.legacyIcon || 'circle';

    svg.dataset.legacyIcon = baseName;
    svg.dataset.legacySpinning = spin ? '1' : '0';

    setFeatherUseTarget(svg, baseName);
    svg.classList.toggle('is-spinning', spin || svg.dataset.legacySpinning === '1');
  }

  function replaceInTree(scope) {
    if (!scope) {
      return;
    }

    ICON_OBSERVER_TARGET_SELECTORS.forEach((selector) => {
      scope.querySelectorAll?.(selector).forEach((el) => convertLegacyIconElement(el));
    });

    if (scope.matches && scope.matches(ICON_OBSERVER_TARGET_SELECTORS.join(','))) {
      convertLegacyIconElement(scope);
    }

    scope.querySelectorAll?.('svg[data-legacy-icon-processed="1"]').forEach((el) => {
      refreshLegacySvgIcon(el);
    });

    if (scope instanceof SVGElement && scope.dataset && scope.dataset.legacyIconProcessed === '1') {
      refreshLegacySvgIcon(scope);
    }
  }

  function initLegacyIconCompat() {
    replaceInTree(document.body);

    if (isLegacyObserverStarted || typeof MutationObserver === 'undefined') {
      return;
    }

    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'attributes' && mutation.target instanceof Element) {
          const target = mutation.target;
          if (target instanceof SVGElement && target.dataset && target.dataset.legacyIconProcessed === '1') {
            refreshLegacySvgIcon(target);
          } else {
            convertLegacyIconElement(target);
          }
          continue;
        }

        if (mutation.type !== 'childList') {
          continue;
        }

        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) {
            return;
          }
          replaceInTree(node);
        });
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class']
    });

    isLegacyObserverStarted = true;
  }

  function hydrateThemeIcon(element, nextTheme) {
    if (!element) {
      return;
    }

    const themeToFeather = nextTheme === 'dark' ? 'sun' : 'moon';

    if (element.tagName === 'SVG') {
      const themeData =
        element.getAttribute('data-theme-icon-sun') ||
        element.getAttribute('data-theme-icon') ||
        `${getFeatherSpriteHref()}#${themeToFeather}`;
      const normalizedThemeData = themeData.split('#')[0] || getFeatherSpriteHref();
      const href = `${normalizedThemeData}#${themeToFeather}`;
      const use = element.querySelector('use');
      if (use) {
        use.setAttribute('href', href);
        use.setAttribute('xlink:href', href);
      }

      element.dataset.state = nextTheme === 'dark' ? 'light' : 'dark';
      return;
    }

    if (element.tagName === 'SPAN' || element.tagName === 'BUTTON' || element.tagName === 'A') {
      const target = element.querySelector('svg') || element;
      if (!target) {
        return;
      }
      const use = target.querySelector('use');
      const href = `${getFeatherSpriteHref()}#${themeToFeather}`;
      if (use) {
        use.setAttribute('href', href);
        use.setAttribute('xlink:href', href);
      }
    }
  }

  function updateToggleText(themeManagerTheme) {
    const activeThemeLabel = themeManagerTheme === 'dark' ? '라이트 모드로' : '다크 모드로';
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');

    if (themeIcon) {
      hydrateThemeIcon(themeIcon, themeManagerTheme);
    }

    if (themeText) {
      themeText.textContent = activeThemeLabel;
    }

    const menuItems = document.querySelectorAll('.theme-toggle-menu-item');
    menuItems.forEach((menuItem) => {
      const itemIcon = menuItem.querySelector('.theme-sun-icon, .theme-moon-icon, [data-theme-icon]');
      if (itemIcon) {
        hydrateThemeIcon(itemIcon, themeManagerTheme);
      }

      const itemText = menuItem.querySelector('.theme-text');
      if (itemText) {
        const lightText = itemText.dataset.themeLightText || '다크 모드로';
        const darkText = itemText.dataset.themeDarkText || '라이트 모드로';
        itemText.textContent = themeManagerTheme === 'dark' ? darkText : lightText;
      } else if (menuItem.textContent && menuItem.textContent.trim() === '테마') {
        menuItem.textContent = activeThemeLabel;
      }
    });

    const mobileTexts = document.querySelectorAll('.theme-toggle-text');
    mobileTexts.forEach((el) => {
      el.textContent = themeManagerTheme === 'dark' ? '라이트 모드 전환' : '다크 모드 전환';
    });
  }

  class ThemeManager {
    constructor() {
      const presetTheme = document.documentElement.getAttribute('data-theme');
      this.currentTheme = presetTheme || this.getStoredTheme() || this.getSystemTheme();
      this.isInitialized = false;
      this.init();
    }

    getStoredTheme() {
      try {
        return localStorage.getItem('theme');
      } catch (_e) {
        return null;
      }
    }

    saveTheme(theme) {
      try {
        localStorage.setItem('theme', theme);
      } catch (_e) {
        // 로컬 스토리지 접근 제한일 때는 무시
      }
    }

    getSystemTheme() {
      try {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      } catch (_e) {
        return 'light';
      }
    }

    applyTheme(theme) {
      const html = document.documentElement;
      const body = document.body;

      html.classList.remove('dark', 'light');
      body.classList.remove('dark', 'light');

      html.classList.add(theme);
      body.classList.add(theme);
      html.setAttribute('data-theme', theme);
      body.setAttribute('data-theme', theme);

      this.currentTheme = theme;
      this.saveTheme(theme);
      updateToggleText(theme);
      this.notifyThemeChange(theme);
    }

    notifyThemeChange(theme) {
      window.dispatchEvent(
        new CustomEvent('themechange', {
          detail: { theme }
        })
      );
    }

    toggle() {
      this.applyTheme(this.currentTheme === 'dark' ? 'light' : 'dark');
    }

    init() {
      if (this.isInitialized) {
        return;
      }

      updateToggleText(this.currentTheme);
      this.applyTheme(this.currentTheme);
      this.watchSystemTheme();
      this.isInitialized = true;
    }

    watchSystemTheme() {
      try {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', (event) => {
          const shouldFollowSystem = !this.getStoredTheme();
          if (!shouldFollowSystem) {
            return;
          }
          this.applyTheme(event.matches ? 'dark' : 'light');
        });
      } catch (_e) {
        // passive
      }
    }
  }

  let themeManager;

  const themeManagerApi = {
    get current() {
      return themeManager?.currentTheme || 'dark';
    },
    toggle: () => {
      if (!themeManager) {
        initThemeSystem();
      }
      themeManager.toggle();
    },
    apply: (theme) => {
      if (!themeManager) {
        initThemeSystem();
      }
      themeManager.applyTheme(theme);
    }
  };

  function initThemeSystem() {
    if (!themeManager) {
      themeManager = new ThemeManager();
    }
  }

  function initThemeApi() {
    window.themeManager = themeManagerApi;
  }

  window.toggleTheme = function() {
    themeManagerApi.toggle();
  };

  window.refreshThemeIcons = function() {
    replaceInTree(document.body);
    updateToggleText(themeManager ? themeManager.currentTheme : document.documentElement.getAttribute('data-theme') || 'dark');
  };

  window.addEventListener('themechange', function(event) {
    if (!event?.detail?.theme) {
      return;
    }
    // 하위 코드 확장 포인트
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initThemeSystem();
      initThemeApi();
      initLegacyIconCompat();
    });
  } else {
    initThemeSystem();
    initThemeApi();
    initLegacyIconCompat();
  }

  window.addEventListener('load', () => {
    if (!themeManager) {
      initThemeSystem();
      initThemeApi();
    }
    initLegacyIconCompat();
  });
})();
