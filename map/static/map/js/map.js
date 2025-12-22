(() => {
  const mapWorld = document.getElementById('mapWorld');
  if (!mapWorld) {
    return;
  }

  const mapViewport = document.getElementById('mapViewport');
  const mapRoot = document.getElementById('mapRoot');
  const mapPlayer = document.getElementById('mapPlayer');
  const mapZones = document.getElementById('mapZones');
  const playerName = document.getElementById('playerName');
  const playerPosition = document.getElementById('playerPosition');
  const zoneStatus = document.getElementById('zoneStatus');
  const zoneActions = document.getElementById('zoneActions');
  const modal = document.getElementById('mapModal');
  const modalTitle = document.getElementById('mapModalTitle');
  const modalFrame = document.getElementById('mapModalFrame');
  const modalClose = document.getElementById('mapModalClose');

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

  const worldWidth = Number.parseInt(mapWorld.dataset.width, 10) || 1800;
  const worldHeight = Number.parseInt(mapWorld.dataset.height, 10) || 1000;
  mapWorld.style.width = `${worldWidth}px`;
  mapWorld.style.height = `${worldHeight}px`;

  const playerSize = 44;
  const state = {
    x: 120,
    y: 160,
    speed: 2.6,
  };

  const characters = [
    {
      name: '빛의 러너',
      symbol: 'A',
      color: '#f97316',
      glow: 'rgba(249, 115, 22, 0.65)',
      text: '#0f172a',
    },
    {
      name: '네온 탐험가',
      symbol: 'B',
      color: '#38bdf8',
      glow: 'rgba(56, 189, 248, 0.65)',
      text: '#0f172a',
    },
    {
      name: '새벽 스트라이더',
      symbol: 'C',
      color: '#facc15',
      glow: 'rgba(250, 204, 21, 0.65)',
      text: '#0f172a',
    },
    {
      name: '미드나잇 워커',
      symbol: 'D',
      color: '#a855f7',
      glow: 'rgba(168, 85, 247, 0.65)',
      text: '#f8fafc',
    },
  ];

  const selected = characters[Math.floor(Math.random() * characters.length)];
  playerName.textContent = selected.name;
  mapPlayer.textContent = selected.symbol;
  mapPlayer.style.setProperty('--player-color', selected.color);
  mapPlayer.style.setProperty('--player-glow', selected.glow);
  mapPlayer.style.setProperty('--player-text', selected.text);

  const zones = [
    {
      id: 'zone-community',
      name: '커뮤니티 라운지',
      description: '새 탭으로 열리는 외부 링크 존',
      action: { type: 'new_tab', url: 'https://example.org' },
      x: 280,
      y: 730,
      width: 240,
      height: 140,
    },
    {
      id: 'zone-showcase',
      name: '스토리 전시관',
      description: '모달로 열리는 링크 프리뷰 존',
      action: { type: 'modal', url: 'https://example.com' },
      x: 980,
      y: 640,
      width: 260,
      height: 160,
    },
    {
      id: 'zone-portal',
      name: '포털 게이트',
      description: '새 탭으로 이동하는 링크 존',
      action: { type: 'new_tab', url: 'https://example.com' },
      x: 1380,
      y: 320,
      width: 220,
      height: 140,
    },
  ];

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

  const rectsOverlap = (a, b) =>
    a.x < b.x + b.width &&
    a.x + a.width > b.x &&
    a.y < b.y + b.height &&
    a.y + a.height > b.y;

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
    mapWorld.style.transform = `translate3d(${clampedX}px, ${clampedY}px, 0)`;
  };

  const placePlayer = () => {
    mapPlayer.style.left = `${state.x}px`;
    mapPlayer.style.top = `${state.y}px`;
    playerPosition.textContent = `${Math.round(state.x)}, ${Math.round(state.y)}`;
  };

  const pickSafeStart = () => {
    state.x = 140 + Math.random() * (worldWidth - 280);
    state.y = 140 + Math.random() * (worldHeight - 280);
  };

  const renderZones = () => {
    mapZones.innerHTML = '';
    zones.forEach((zone) => {
      const element = document.createElement('div');
      element.className = 'map-zone';
      element.dataset.zoneId = zone.id;
      element.style.left = `${zone.x}px`;
      element.style.top = `${zone.y}px`;
      element.style.width = `${zone.width}px`;
      element.style.height = `${zone.height}px`;

      const label = document.createElement('span');
      label.className = 'map-zone-name';
      label.textContent = zone.name;
      element.appendChild(label);

      mapZones.appendChild(element);
    });
  };

  const renderZoneActions = (zone) => {
    if (!zone) {
      zoneActions.classList.add('is-hidden');
      zoneActions.innerHTML = '';
      return;
    }

    zoneActions.classList.remove('is-hidden');
    zoneActions.innerHTML = '';

    const description = document.createElement('p');
    description.className = 'map-panel-muted';
    description.textContent = zone.description;
    zoneActions.appendChild(description);

    if (zone.action.type === 'new_tab') {
      const link = document.createElement('a');
      link.className = 'map-zone-button is-primary';
      link.href = zone.action.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = '새 탭으로 열기';
      zoneActions.appendChild(link);
    }

    if (zone.action.type === 'modal') {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'map-zone-button is-secondary';
      button.textContent = '모달로 보기';
      button.addEventListener('click', () => openModal(zone));
      zoneActions.appendChild(button);
    }
  };

  const highlightZone = (zoneId) => {
    const zoneElements = mapZones.querySelectorAll('.map-zone');
    zoneElements.forEach((element) => {
      if (element.dataset.zoneId === zoneId) {
        element.classList.add('is-active');
      } else {
        element.classList.remove('is-active');
      }
    });
  };

  const openModal = (zone) => {
    if (!modal || !modalFrame) {
      return;
    }
    modalTitle.textContent = zone.name;
    modalFrame.src = zone.action.url;
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

  let currentZone = null;

  const updateZoneStatus = () => {
    const playerRect = {
      x: state.x,
      y: state.y,
      width: playerSize,
      height: playerSize,
    };

    const activeZone = zones.find((zone) => rectsOverlap(playerRect, zone)) || null;
    if (activeZone?.id !== currentZone?.id) {
      currentZone = activeZone;
      if (currentZone) {
        zoneStatus.textContent = `${currentZone.name}에 진입했습니다.`;
      } else {
        zoneStatus.textContent = '아직 발견된 존이 없습니다.';
      }
      renderZoneActions(currentZone);
      highlightZone(currentZone?.id ?? null);
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
    updateZoneStatus();
    requestAnimationFrame(step);
  };

  window.addEventListener('keydown', (event) => {
    if (Object.prototype.hasOwnProperty.call(keys, event.key)) {
      keys[event.key] = true;
      event.preventDefault();
    }
    if (event.key === 'Escape') {
      closeModal();
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

  renderZones();
  pickSafeStart();
  placePlayer();
  updateViewport();
  updateCamera();
  updateZoneStatus();
  requestAnimationFrame(step);
})();
