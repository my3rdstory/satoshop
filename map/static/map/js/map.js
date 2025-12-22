(() => {
  const mapWorld = document.getElementById('mapWorld');
  if (!mapWorld) {
    return;
  }

  const mapViewport = document.getElementById('mapViewport');
  const mapRoot = document.getElementById('mapRoot');
  const mapPlayer = document.getElementById('mapPlayer');
  const mapLinkHint = document.getElementById('mapLinkHint');
  const mapLinkStatus = document.getElementById('mapLinkStatus');
  const mapLinkForm = document.getElementById('mapLinkForm');
  const mapLinkInput = document.getElementById('mapLinkInput');
  const mapBase = document.getElementById('mapBase');
  const mapBaseFrame = document.getElementById('mapBaseFrame');
  const modal = document.getElementById('mapModal');
  const modalTitle = document.getElementById('mapModalTitle');
  const modalFrame = document.getElementById('mapModalFrame');
  const modalClose = document.getElementById('mapModalClose');

  const worldWidth = Number.parseInt(mapWorld.dataset.width, 10) || 1800;
  const worldHeight = Number.parseInt(mapWorld.dataset.height, 10) || 1000;
  mapWorld.style.width = `${worldWidth}px`;
  mapWorld.style.height = `${worldHeight}px`;

  const playerSize = 44;
  const state = {
    x: 120,
    y: 160,
    speed: 2.6,
    cameraX: 0,
    cameraY: 0,
  };

  const characters = [
    {
      symbol: 'A',
      color: '#f97316',
      glow: 'rgba(249, 115, 22, 0.65)',
      text: '#0f172a',
    },
    {
      symbol: 'B',
      color: '#38bdf8',
      glow: 'rgba(56, 189, 248, 0.65)',
      text: '#0f172a',
    },
    {
      symbol: 'C',
      color: '#facc15',
      glow: 'rgba(250, 204, 21, 0.65)',
      text: '#0f172a',
    },
    {
      symbol: 'D',
      color: '#a855f7',
      glow: 'rgba(168, 85, 247, 0.65)',
      text: '#f8fafc',
    },
  ];

  const selected = characters[Math.floor(Math.random() * characters.length)];
  mapPlayer.textContent = selected.symbol;
  mapPlayer.style.setProperty('--player-color', selected.color);
  mapPlayer.style.setProperty('--player-glow', selected.glow);
  mapPlayer.style.setProperty('--player-text', selected.text);

  const keys = {
    ArrowUp: false,
    ArrowDown: false,
    ArrowLeft: false,
    ArrowRight: false,
    Shift: false,
  };

  const viewport = {
    width: mapViewport.clientWidth,
    height: mapViewport.clientHeight,
  };

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  const updateViewport = () => {
    viewport.width = mapViewport.clientWidth;
    viewport.height = mapViewport.clientHeight;
  };

  const updateCamera = () => {
    const targetX = viewport.width / 2 - (state.x + playerSize / 2);
    const targetY = viewport.height / 2 - (state.y + playerSize / 2);
    const minX = viewport.width - worldWidth;
    const minY = viewport.height - worldHeight;
    const clampedX = clamp(targetX, minX, 0);
    const clampedY = clamp(targetY, minY, 0);
    state.cameraX = clampedX;
    state.cameraY = clampedY;
    mapWorld.style.transform = `translate3d(${clampedX}px, ${clampedY}px, 0)`;
  };

  const updateLinkHintPosition = () => {
    if (!mapLinkHint) {
      return;
    }
    mapLinkHint.style.left = `${state.x + playerSize / 2}px`;
    mapLinkHint.style.top = `${state.y}px`;
  };

  const placePlayer = () => {
    mapPlayer.style.left = `${state.x}px`;
    mapPlayer.style.top = `${state.y}px`;
    updateLinkHintPosition();
  };

  const pickSafeStart = () => {
    state.x = 140 + Math.random() * (worldWidth - 280);
    state.y = 140 + Math.random() * (worldHeight - 280);
  };

  const openMapLayer = () => {
    if (mapRoot) {
      mapRoot.classList.remove('is-hidden');
    }
    document.body.classList.add('map-mode');
  };

  const closeMapLayer = () => {
    if (mapRoot) {
      mapRoot.classList.add('is-hidden');
    }
    document.body.classList.remove('map-mode');
    closeModal();
  };

  window.MapLayer = {
    open: openMapLayer,
    close: closeMapLayer,
  };

  const openModal = (link) => {
    if (!modal || !modalFrame || !link) {
      return;
    }
    modalTitle.textContent = link.title || '링크 보기';
    modalFrame.src = link.url;
    modal.classList.remove('is-hidden');
    modal.setAttribute('aria-hidden', 'false');
  };

  const closeModal = () => {
    if (!modal || !modalFrame) {
      return;
    }
    modal.classList.add('is-hidden');
    modal.setAttribute('aria-hidden', 'true');
    modalFrame.src = 'about:blank';
  };

  const normalizeUrl = (value) => {
    if (!value) {
      return null;
    }
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
    try {
      const url = new URL(withProtocol);
      if (!['http:', 'https:'].includes(url.protocol)) {
        return null;
      }
      return url.href;
    } catch (error) {
      return null;
    }
  };

  const setBaseUrl = (value) => {
    const normalized = normalizeUrl(value);
    if (!normalized) {
      if (mapBase) {
        mapBase.classList.add('is-hidden');
      }
      if (mapRoot) {
        mapRoot.classList.remove('has-base');
      }
      if (mapBaseFrame) {
        mapBaseFrame.src = 'about:blank';
      }
      return;
    }

    if (mapBaseFrame) {
      mapBaseFrame.src = normalized;
    }
    if (mapBase) {
      mapBase.classList.remove('is-hidden');
    }
    if (mapRoot) {
      mapRoot.classList.add('has-base');
    }
  };

  const getBaseDocument = () => {
    if (!mapBaseFrame || !mapBase || mapBase.classList.contains('is-hidden')) {
      return null;
    }
    try {
      return mapBaseFrame.contentDocument;
    } catch (error) {
      return null;
    }
  };

  const getBaseLocation = () => {
    if (!mapBaseFrame || !mapBase || mapBase.classList.contains('is-hidden')) {
      return window.location.href;
    }
    try {
      return mapBaseFrame.contentWindow?.location?.href || window.location.href;
    } catch (error) {
      return window.location.href;
    }
  };

  const extractLink = (element, baseHref) => {
    if (!element) {
      return null;
    }
    const anchor = element.closest ? element.closest('a[href]') : null;
    if (!anchor) {
      return null;
    }
    const rawHref = anchor.getAttribute('href');
    if (!rawHref) {
      return null;
    }
    if (rawHref.startsWith('#') || rawHref.startsWith('javascript:') || rawHref.startsWith('mailto:')) {
      return null;
    }
    let url;
    try {
      url = new URL(rawHref, baseHref);
    } catch (error) {
      return null;
    }
    if (!['http:', 'https:'].includes(url.protocol)) {
      return null;
    }
    const title = anchor.textContent ? anchor.textContent.trim() : '';
    return {
      url: url.href,
      title: title || url.href,
    };
  };

  const findLinkAtPoint = (clientX, clientY) => {
    const baseDocument = getBaseDocument();
    const baseHref = getBaseLocation();

    if (baseDocument && mapBaseFrame) {
      const frameRect = mapBaseFrame.getBoundingClientRect();
      if (
        clientX >= frameRect.left &&
        clientX <= frameRect.right &&
        clientY >= frameRect.top &&
        clientY <= frameRect.bottom
      ) {
        const localX = clientX - frameRect.left;
        const localY = clientY - frameRect.top;
        const element = baseDocument.elementFromPoint(localX, localY);
        return {
          link: extractLink(element, baseHref),
          restricted: false,
        };
      }
    } else if (mapBaseFrame && mapBase && !mapBase.classList.contains('is-hidden')) {
      return { link: null, restricted: true };
    }

    const elements = document.elementsFromPoint(clientX, clientY);
    const target = elements.find((element) => !element.closest('#mapRoot')) || null;
    return {
      link: extractLink(target, baseHref),
      restricted: false,
    };
  };

  const getPlayerScreenPoint = () => {
    const viewportRect = mapViewport.getBoundingClientRect();
    return {
      x: viewportRect.left + state.x + playerSize / 2 + state.cameraX,
      y: viewportRect.top + state.y + playerSize / 2 + state.cameraY,
    };
  };

  let activeLink = null;
  let linkRestricted = false;
  let lastLinkCheck = 0;

  const updateLinkUI = () => {
    if (!mapLinkStatus || !mapLinkHint) {
      return;
    }

    if (activeLink) {
      mapLinkStatus.textContent = activeLink.url;
      mapLinkHint.textContent = `링크 감지\n${activeLink.url}\nT 새 탭 / M 모달`;
      mapLinkHint.classList.remove('is-hidden');
    } else if (linkRestricted) {
      mapLinkStatus.textContent = '외부 사이트는 링크 감지가 제한됩니다.';
      mapLinkHint.classList.add('is-hidden');
    } else {
      mapLinkStatus.textContent = '링크 없음';
      mapLinkHint.classList.add('is-hidden');
    }
  };

  const updateLinkTarget = () => {
    const now = performance.now();
    if (now - lastLinkCheck < 120) {
      return;
    }
    lastLinkCheck = now;
    const point = getPlayerScreenPoint();
    const { link, restricted } = findLinkAtPoint(point.x, point.y);
    if (link?.url !== activeLink?.url || restricted !== linkRestricted) {
      activeLink = link;
      linkRestricted = restricted;
      updateLinkUI();
    }
  };

  const movePlayer = (dx, dy) => {
    state.x = clamp(state.x + dx, 0, worldWidth - playerSize);
    state.y = clamp(state.y + dy, 0, worldHeight - playerSize);
  };

  const step = () => {
    let dx = 0;
    let dy = 0;

    if (keys.ArrowUp) {
      dy -= 1;
    }
    if (keys.ArrowDown) {
      dy += 1;
    }
    if (keys.ArrowLeft) {
      dx -= 1;
    }
    if (keys.ArrowRight) {
      dx += 1;
    }

    const moving = dx !== 0 || dy !== 0;
    if (moving) {
      const length = Math.hypot(dx, dy) || 1;
      const boost = keys.Shift ? 2 : 1;
      movePlayer((dx / length) * state.speed * boost, (dy / length) * state.speed * boost);
      mapPlayer.classList.add('is-moving');
    } else {
      mapPlayer.classList.remove('is-moving');
    }

    placePlayer();
    updateCamera();
    updateLinkTarget();
    requestAnimationFrame(step);
  };

  const isTypingTarget = () => {
    const active = document.activeElement;
    if (!active) {
      return false;
    }
    const tagName = active.tagName;
    return tagName === 'INPUT' || tagName === 'TEXTAREA' || active.isContentEditable;
  };

  window.addEventListener('keydown', (event) => {
    if (isTypingTarget()) {
      return;
    }

    if (Object.prototype.hasOwnProperty.call(keys, event.key)) {
      keys[event.key] = true;
      event.preventDefault();
    }

    if (event.key === 'Escape') {
      closeModal();
    }

    const key = event.key.toLowerCase();
    if (key === 't' && activeLink) {
      window.open(activeLink.url, '_blank', 'noopener');
      event.preventDefault();
    }

    if (key === 'm' && activeLink) {
      openModal(activeLink);
      event.preventDefault();
    }
  });

  window.addEventListener('keyup', (event) => {
    if (Object.prototype.hasOwnProperty.call(keys, event.key)) {
      keys[event.key] = false;
      event.preventDefault();
    }
  });

  window.addEventListener('resize', () => {
    updateViewport();
    updateCamera();
  });

  if (modalClose) {
    modalClose.addEventListener('click', closeModal);
  }

  if (modal) {
    modal.addEventListener('click', (event) => {
      if (event.target === modal) {
        closeModal();
      }
    });
  }

  if (mapLinkForm) {
    mapLinkForm.addEventListener('submit', (event) => {
      event.preventDefault();
      setBaseUrl(mapLinkInput?.value || '');
      updateLinkTarget();
    });
  }

  pickSafeStart();
  placePlayer();
  updateViewport();
  updateCamera();
  updateLinkUI();
  requestAnimationFrame(step);
})();
