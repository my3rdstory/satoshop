const CACHE_NAME = 'satoshop-v1.0.0';
const STATIC_CACHE_NAME = 'satoshop-static-v1.0.0';
const DYNAMIC_CACHE_NAME = 'satoshop-dynamic-v1.0.0';

// 캐시할 정적 리소스
const STATIC_ASSETS = [
  '/',
  '/static/css/bulma.min.css',
  '/static/css/custom.css',
  '/static/css/components.css',
  '/static/css/pages.css',
  '/static/css/products.css',
  '/static/css/stores.css',
  '/static/css/themes.css',
  '/static/js/common.js',
  '/static/js/theme-toggle.js',
  '/static/images/satoshop-logo-1x1-favicon.png',
  '/static/images/btcmap-logo-basic-200x43.webp',
  'https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// 오프라인 페이지
const OFFLINE_PAGE = '/offline/';

// Service Worker 설치
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('Service Worker: Static assets cached');
        return self.skipWaiting();
      })
      .catch(err => {
        console.error('Service Worker: Error caching static assets', err);
      })
  );
});

// Service Worker 활성화
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            // 이전 버전의 캐시 삭제
            if (cacheName !== STATIC_CACHE_NAME && cacheName !== DYNAMIC_CACHE_NAME) {
              console.log('Service Worker: Deleting old cache', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('Service Worker: Activated');
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
    console.error('Service Worker: Error handling request', error);
    
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
  return url.includes('/static/') || 
         url.includes('fonts.googleapis.com') ||
         url.includes('cdnjs.cloudflare.com') ||
         url.includes('.css') ||
         url.includes('.js') ||
         url.includes('.png') ||
         url.includes('.jpg') ||
         url.includes('.jpeg') ||
         url.includes('.webp') ||
         url.includes('.svg');
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
    console.log('Service Worker: Background sync triggered');
    // 백그라운드에서 처리할 작업들
  }
});

// 푸시 알림 (향후 사용)
self.addEventListener('push', event => {
  if (event.data) {
    const data = event.data.json();
    console.log('Service Worker: Push notification received', data);
    
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