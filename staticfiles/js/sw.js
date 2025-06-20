const CACHE_NAME = 'satoshop-v1.0.0';
const STATIC_CACHE_NAME = 'satoshop-static-v1.0.0';
const DYNAMIC_CACHE_NAME = 'satoshop-dynamic-v1.0.0';

// 디버깅 모드 확인 (프로덕션에서는 로그 비활성화)
const isDebugMode = self.location.hostname === 'localhost' || 
                   self.location.hostname === '127.0.0.1' || 
                   self.location.hostname.includes('dev') ||
                   self.location.hostname === 'satoshop-dev.onrender.com';

// 프로덕션 도메인에서는 명시적으로 디버깅 비활성화
const isProduction = self.location.hostname === 'store.btcmap.kr' || 
                    self.location.hostname === 'satoshop.onrender.com' ||
                    self.location.hostname.endsWith('.onrender.com');
const shouldDebug = isDebugMode && !isProduction;

function debugLog(...args) {
  if (shouldDebug) {
    console.log(...args);
  }
}

function debugError(...args) {
  if (shouldDebug) {
    console.error(...args);
  }
}

// 운영 환경에서는 모든 콘솔 로그 비활성화
if (isProduction) {
  console.log = function() {};
  console.error = function() {};
  console.warn = function() {};
  console.info = function() {};
  console.debug = function() {};
}

// 캐시할 정적 리소스 (실제 존재하는 파일들만, 동적 페이지 제외)
const STATIC_ASSETS = [
  '/static/css/bulma.min.css',
  '/static/css/custom.css',
  '/static/css/components.css',
  '/static/css/pages.css',
  '/static/css/products.css',
  '/static/css/stores.css',
  '/static/css/themes.css',
  '/static/css/board-notice.css',
  '/static/css/document.css',
  '/static/css/mobile-menu.css',
  '/static/css/markdown-renderer.css',
  '/static/js/common.js',
  '/static/js/theme-toggle.js',
  '/static/js/cart-common.js',
  '/static/js/markdown-renderer.js',
  '/static/images/satoshop-logo-1x1-favicon.png',
  '/static/images/btcmap-logo-basic-200x43.webp',
  '/static/images/btcmap-simbol-1vs1-100x100.webp',
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// 오프라인 페이지
const OFFLINE_PAGE = '/offline/';

// 개별 파일 캐싱 함수 (실패해도 전체가 실패하지 않음)
async function cacheAssetsIndividually(cache, assets) {
  const results = await Promise.allSettled(
    assets.map(async (asset) => {
      try {
        // 외부 리소스에 대해서는 no-cors 모드로 요청
        const fetchOptions = asset.startsWith('http') && !asset.includes(self.location.origin) 
          ? { mode: 'no-cors' } 
          : {};
          
        const response = await fetch(asset, fetchOptions);
        
        if (response.ok || response.type === 'opaque') {
          await cache.put(asset, response);
          debugLog(`Service Worker: Cached ${asset}`);
          return { asset, success: true };
        } else {
          debugError(`Service Worker: Failed to fetch ${asset} - Status: ${response.status}`);
          return { asset, success: false, error: `Status: ${response.status}` };
        }
      } catch (error) {
        debugError(`Service Worker: Error caching ${asset}:`, error);
        return { asset, success: false, error: error.message };
      }
    })
  );

  const successful = results.filter(result => result.value?.success).length;
  const failed = results.filter(result => !result.value?.success);
  
  debugLog(`Service Worker: Cached ${successful}/${assets.length} assets`);
  
  if (failed.length > 0) {
    debugError('Service Worker: Failed to cache assets:', failed.map(f => f.value?.asset));
  }
  
  return results;
}

// Service Worker 설치
self.addEventListener('install', event => {
  debugLog('Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then(cache => {
        debugLog('Service Worker: Caching static assets individually');
        return cacheAssetsIndividually(cache, STATIC_ASSETS);
      })
      .then((results) => {
        debugLog('Service Worker: Static asset caching completed');
        return self.skipWaiting();
      })
      .catch(err => {
        debugError('Service Worker: Error during installation', err);
        // 설치는 계속 진행 (일부 파일 캐싱 실패해도 Service Worker는 작동)
        return self.skipWaiting();
      })
  );
});

// Service Worker 활성화
self.addEventListener('activate', event => {
  debugLog('Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            // 이전 버전의 캐시 삭제
            if (cacheName !== STATIC_CACHE_NAME && cacheName !== DYNAMIC_CACHE_NAME) {
              debugLog('Service Worker: Deleting old cache', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        debugLog('Service Worker: Activated');
        return self.clients.claim();
      })
  );
});

// 네트워크 요청 가로채기
self.addEventListener('fetch', event => {
  const { request } = event;
  
  // GET 요청만 처리
  if (request.method !== 'GET') {
    return;
  }

  // Chrome extension 요청 무시
  if (request.url.startsWith('chrome-extension://')) {
    return;
  }

  event.respondWith(
    handleRequest(request)
  );
});

async function handleRequest(request) {
  const url = new URL(request.url);
  
  try {
    // 정적 리소스 캐시 전략 (Cache First)
    if (isStaticAsset(request.url)) {
      return await cacheFirst(request, STATIC_CACHE_NAME);
    }
    
    // HTML 페이지 캐시 전략 (Network First)
    if (request.headers.get('accept')?.includes('text/html')) {
      return await networkFirst(request, DYNAMIC_CACHE_NAME);
    }
    
    // 기타 리소스는 네트워크 우선
    return await networkFirst(request, DYNAMIC_CACHE_NAME);
    
  } catch (error) {
    debugError('Service Worker: Error handling request', error);
    
    // HTML 요청에 대해서는 오프라인 페이지 반환
    if (request.headers.get('accept')?.includes('text/html')) {
      const offlineResponse = await caches.match(OFFLINE_PAGE);
      if (offlineResponse) {
        return offlineResponse;
      }
    }
    
    // 기본 오프라인 응답
    return new Response('오프라인 상태입니다.', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: { 'Content-Type': 'text/plain; charset=utf-8' }
    });
  }
}

// 정적 리소스 판별
function isStaticAsset(url) {
  // manifest.json은 정적 리소스에서 제외하여 항상 네트워크에서 가져오도록 함
  if (url.includes('/manifest.json')) {
    return false;
  }
  
  return url.includes('/static/') || 
         url.includes('fonts.googleapis.com') ||
         url.includes('cdnjs.cloudflare.com');
}

// Cache First 전략
async function cacheFirst(request, cacheName) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  const networkResponse = await fetch(request);
  
  if (networkResponse.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, networkResponse.clone());
  }
  
  return networkResponse;
}

// Network First 전략
async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    throw error;
  }
}

// 백그라운드 동기화 (향후 사용)
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    debugLog('Service Worker: Background sync triggered');
    // 백그라운드에서 처리할 작업들
  }
});

// 푸시 알림 (향후 사용)
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    debugLog('Service Worker: Push notification received', data);
    
    const options = {
      body: data.body,
      icon: '/static/images/satoshop-logo-1x1-favicon.png',
      badge: '/static/images/satoshop-logo-1x1-favicon.png',
      vibrate: [100, 50, 100],
      data: data.data
    };
    
    event.waitUntil(
      self.registration.showNotification(data.title, options)
    );
  }
});

// 알림 클릭 처리
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  event.waitUntil(
    clients.openWindow(event.notification.data?.url || '/')
  );
}); 