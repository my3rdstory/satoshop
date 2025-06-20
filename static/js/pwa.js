// PWA 관련 JavaScript 코드

(function() {
  'use strict';

  // PWA 관련 변수들
  let deferredPrompt;
  let installButtonsInitialized = false;

  // 환경 확인
  const isProduction = window.location.hostname === 'store.btcmap.kr' || 
                      window.location.hostname === 'satoshop.onrender.com' ||
                      window.location.hostname.endsWith('.onrender.com');

  // 디버깅 모드 확인
  const isDebugMode = window.location.hostname === 'localhost' || 
                     window.location.hostname === '127.0.0.1' || 
                     window.location.hostname.includes('dev') ||
                     window.location.hostname === 'satoshop-dev.onrender.com';

  const shouldDebug = isDebugMode && !isProduction;

  // 디버깅 함수들
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

  // PWA 기능 설정 - 운영 환경에서는 브라우저 기본 배너 사용
  const enableCustomPWA = !isProduction;

  // Service Worker 등록
  function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js', {
        scope: '/',
        updateViaCache: 'none'
      })
      .then(function(registration) {
        debugLog('Service Worker registered successfully:', registration);
        
        // 업데이트 확인
        registration.addEventListener('updatefound', function() {
          debugLog('Service Worker update found');
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', function() {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                debugLog('Service Worker updated, refresh recommended');
                showUpdateAvailableNotification();
              }
            });
          }
        });
      })
      .catch(function(error) {
        debugError('Service Worker registration failed:', error);
      });
    } else {
      debugLog('이 브라우저는 Service Worker를 지원하지 않습니다.');
    }
  }

  // PWA 설치 가능성 확인
  function checkPWAInstallability() {
    // 이미 설치된 경우 확인
    if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
      debugLog('PWA가 이미 설치되어 있습니다.');
      return false;
    }

    // iOS Safari 확인
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isSafari = /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent);
    
    if (isIOS && isSafari) {
      debugLog('iOS에서 PWA 설치 가능합니다. Safari 공유 메뉴에서 "홈 화면에 추가"를 찾아보세요.');
      return 'ios';
    }

    return true;
  }

  // PWA 설치 프롬프트 이벤트 처리
  function handleInstallPrompt() {
    window.addEventListener('beforeinstallprompt', (e) => {
      debugLog('PWA 설치 프롬프트 준비됨');

      // 운영 환경에서는 PWA 설치 배너 완전히 차단
      if (isProduction) {
        debugLog('운영 환경에서 PWA 설치 배너 차단됨');
        e.preventDefault();
        return;
      }

      if (enableCustomPWA && checkPWAInstallability() && !installButtonsInitialized) {
        e.preventDefault();
        const installButton = document.getElementById('pwa-install-button');
        const installButtonMobile = document.getElementById('pwa-install-button-mobile');
        
        if (installButton || installButtonMobile) {
          deferredPrompt = e;
          showInstallButtons();
          installButtonsInitialized = true;
          debugLog('커스텀 PWA 설치 기능 활성화됨');
        } else {
          debugLog('PWA 설치 버튼이 없어 기본 브라우저 동작을 허용합니다');
        }
      }
    });
  }

  // PWA 설치 버튼 표시
  function showInstallButtons() {
    const installButton = document.getElementById('pwa-install-button');
    const installButtonMobile = document.getElementById('pwa-install-button-mobile');
    const siteInstallButtonMobile = document.getElementById('site-pwa-install-button-mobile');
    const storeInstallButtonMobile = document.getElementById('store-pwa-install-button-mobile');

    // 모든 설치 버튼 표시
    [installButton, installButtonMobile, siteInstallButtonMobile, storeInstallButtonMobile].forEach(button => {
      if (button) {
        button.style.display = 'block';
        button.classList.add('pwa-fade-in');
        
        // 클릭 이벤트 추가
        button.addEventListener('click', function() {
          installPWA();
        });
      }
    });
  }

  // PWA 설치 실행
  function installPWA() {
    if (deferredPrompt) {
      debugLog('PWA 설치 프롬프트 표시');
      deferredPrompt.prompt();
      
      deferredPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === 'accepted') {
          debugLog('사용자가 PWA 설치를 수락했습니다');
        } else {
          debugLog('사용자가 PWA 설치를 거부했습니다');
        }
        deferredPrompt = null;
      });
    } else {
      // iOS인 경우 설치 안내 모달 표시
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
      const isSafari = /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent);
      
      if (isIOS && isSafari) {
        showIOSInstallModal();
      } else {
        debugLog('PWA 설치 프롬프트가 준비되지 않았습니다');
      }
    }
  }

  // 설치 완료 후 버튼 숨기기
  function hideInstallButtons() {
    const buttons = [
      'pwa-install-button',
      'pwa-install-button-mobile', 
      'site-pwa-install-button-mobile',
      'store-pwa-install-button-mobile'
    ];

    buttons.forEach(buttonId => {
      const button = document.getElementById(buttonId);
      if (button) {
        button.style.display = 'none';
      }
    });
  }

  // PWA 설치 완료 감지
  function handleAppInstalled() {
    window.addEventListener('appinstalled', (evt) => {
      debugLog('PWA가 설치되었습니다');
      hideInstallButtons();
      showInstallSuccessMessage();
    });
  }

  // iOS PWA 설치 모달 관련 함수들
  window.showIOSInstallModal = function() {
    const modal = document.getElementById('ios-install-modal');
    if (modal) {
      modal.classList.remove('hidden');
      modal.classList.add('pwa-fade-in');
      debugLog('iOS 설치 안내 모달 표시됨');
    }
  };

  window.hideIOSInstallModal = function() {
    const modal = document.getElementById('ios-install-modal');
    if (modal) {
      modal.classList.add('hidden');
      modal.classList.remove('pwa-fade-in');
      debugLog('iOS 설치 안내 모달 숨김');
    }
  };

  // 모달 외부 클릭 시 닫기
  function handleModalOutsideClick() {
    document.addEventListener('click', function(event) {
      const modal = document.getElementById('ios-install-modal');
      if (modal && event.target === modal) {
        hideIOSInstallModal();
      }
    });
  }

  // Service Worker 업데이트 알림
  function showUpdateAvailableNotification() {
    // 업데이트 가능 알림을 표시하는 로직
    if (window.createNotification) {
      window.createNotification('info', '앱 업데이트가 가능합니다. 페이지를 새로고침해주세요.');
    } else {
      debugLog('앱 업데이트가 가능합니다');
    }
  }

  // 설치 성공 메시지
  function showInstallSuccessMessage() {
    if (window.createNotification) {
      window.createNotification('success', 'PWA가 성공적으로 설치되었습니다!');
    } else {
      debugLog('PWA 설치 완료');
    }
  }

  // PWA 상태 확인 및 UI 업데이트
  function updatePWAStatus() {
    const isStandalone = window.matchMedia && window.matchMedia('(display-mode: standalone)').matches;
    const isInstalled = isStandalone || window.navigator.standalone;

    if (isInstalled) {
      hideInstallButtons();
      
      // PWA 상태 표시 요소가 있다면 업데이트
      const statusElements = document.querySelectorAll('.pwa-status');
      statusElements.forEach(element => {
        element.classList.remove('available', 'not-supported');
        element.classList.add('installed');
        element.innerHTML = '<i class="fas fa-check-circle"></i> 앱으로 설치됨';
      });
    }
  }

  // PWA 초기화
  function initPWA() {
    debugLog('PWA 초기화 시작');

    // Service Worker 등록
    registerServiceWorker();

    // PWA 설치 관련 이벤트 처리
    handleInstallPrompt();
    handleAppInstalled();
    handleModalOutsideClick();

    // PWA 상태 확인
    updatePWAStatus();

    // 초기 설치 가능성 확인
    const installability = checkPWAInstallability();
    if (installability === 'ios') {
      // iOS용 설치 안내 버튼 표시 로직 (필요시)
      debugLog('iOS PWA 설치 가능');
    } else if (!installability) {
      debugLog('PWA가 이미 설치되어 있거나 설치할 수 없습니다');
    } else {
      debugLog('PWA 설치 프롬프트가 아직 트리거되지 않았습니다.');
    }

    debugLog('PWA 초기화 완료');
  }

  // DOM 로드 완료 후 PWA 초기화
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPWA);
  } else {
    initPWA();
  }

  // 전역 PWA 함수들 내보내기
  window.PWA = {
    install: installPWA,
    checkInstallability: checkPWAInstallability,
    showIOSModal: showIOSInstallModal,
    hideIOSModal: hideIOSInstallModal,
    updateStatus: updatePWAStatus
  };

})(); 