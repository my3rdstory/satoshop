document.addEventListener('DOMContentLoaded', function () {
  // 폼 제출 검증
  const apiSettingsForm = document.getElementById('apiSettingsForm');
  if (apiSettingsForm) {
    apiSettingsForm.addEventListener('submit', function (e) {
      const apiInput = document.getElementById('blink_api_info');
      const walletInput = document.getElementById('blink_wallet_id');
      const apiInfo = apiInput ? apiInput.value.trim() : '';
      const walletId = walletInput ? walletInput.value.trim() : '';

      // 확인 대화상자
      let confirmMessage = '';
      if (apiInfo || walletId) {
        confirmMessage = '입력한 API 정보가 정확한지 확인하셨나요?\n잘못된 정보는 결제 처리에 문제를 일으킬 수 있습니다.';
      } else {
        confirmMessage = '기존 설정을 그대로 유지하시겠습니까?';
      }

      if (confirmMessage && !confirm(confirmMessage)) {
        e.preventDefault();
        return false;
      }
    });
  }

  // 테스트 인보이스 관련 요소들
  const generateInvoiceBtn = document.getElementById('generateInvoiceBtn');
  const qrCodeImage = document.getElementById('qrCodeImage');
  const loadingSpinner = document.getElementById('loadingSpinner');
  const invoiceDetails = document.getElementById('invoiceDetails');
  const paymentStatus = document.getElementById('paymentStatus');
  const paymentMessage = document.getElementById('paymentMessage');
  const invoiceTextContainer = document.getElementById('invoiceTextContainer');
  const invoiceTextArea = document.getElementById('invoiceTextArea');
  const copyInvoiceBtn = document.getElementById('copyInvoiceBtn');

  let currentPaymentHash = null;
  let paymentCheckInterval = null;
  let currentInvoice = null;

  // 테스트 인보이스 생성 버튼이 있을 때만 이벤트 리스너 추가
  if (generateInvoiceBtn) {
    generateInvoiceBtn.addEventListener('click', function () {
      generateTestInvoice();
    });
  }

  // 인보이스 복사 버튼이 있을 때만 이벤트 리스너 추가
  if (copyInvoiceBtn) {
    copyInvoiceBtn.addEventListener('click', function () {
      copyInvoiceToClipboard();
    });
  }

  // QRious 라이브러리 로딩 확인
  function waitForQRious() {
    return new Promise((resolve) => {
      let attempts = 0;
      const maxAttempts = 50; // 5초 대기

      function check() {
        attempts++;

        if (typeof QRious !== 'undefined') {
          resolve();
          return;
        }

        if (attempts >= maxAttempts) {
          resolve(); // 실패해도 계속 진행
          return;
        }

        setTimeout(check, 100);
      }

      check();
    });
  }

  // 테스트 인보이스 생성
  async function generateTestInvoice() {
    try {
      const storeId = window.STORE_ID || '';
      const storeName = window.STORE_NAME || '테스트 스토어';

      // 버튼 숨기고 로딩 표시
      generateInvoiceBtn.style.display = 'none';
      loadingSpinner.classList.remove('hidden');

      const requestBody = {
        amount: 10,  // 10 사토시
        memo: `${storeName || '테스트 스토어'} - 블링크 API 테스트 (10 sats)`,
        store_id: storeId
      };

      const response = await fetch('/ln_payment/create_invoice/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.CSRF_TOKEN
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP 오류: ${response.status} ${response.statusText}`);
      }

      const responseText = await response.text();

      if (!responseText.trim()) {
        throw new Error('서버에서 빈 응답을 받았습니다.');
      }

      let data;
      try {
        data = JSON.parse(responseText);
      } catch (parseError) {
        throw new Error(`서버 응답 파싱 오류: ${parseError.message}`);
      }

      if (data.success) {
        if (!data.invoice) {
          throw new Error('인보이스 데이터가 없습니다.');
        }
        if (!data.payment_hash) {
          throw new Error('payment_hash가 없습니다.');
        }

        // 로딩 숨기고 QR 코드 생성
        loadingSpinner.classList.add('hidden');
        await generateQRCode(data.invoice);

        // 인보이스 정보 표시
        invoiceDetails.classList.remove('hidden');
        invoiceTextArea.value = data.invoice;
        invoiceTextContainer.classList.remove('hidden');

        // 결제 해시 저장
        currentPaymentHash = data.payment_hash;
        currentInvoice = data.invoice;

        // 결제 상태 확인 시작
        startPaymentStatusCheck();

        // 결제 대기 상태 표시
        showPaymentStatus('결제를 기다리고 있습니다. QR 코드를 스캔하거나 인보이스를 복사하여 결제해주세요.', 'info');
      } else {
        throw new Error(data.error || '인보이스 생성에 실패했습니다.');
      }
    } catch (error) {
      console.error('Error:', error);
      // 로딩 숨기고 버튼 다시 표시
      loadingSpinner.classList.add('hidden');
      generateInvoiceBtn.style.display = 'inline-flex';

      // 오류 메시지 표시
      showPaymentStatus('인보이스 생성 중 오류가 발생했습니다: ' + error.message, 'danger');
    }
  }

  // QR 코드 생성
  async function generateQRCode(invoice) {
    try {
      // QRious 라이브러리 로딩 대기
      await waitForQRious();

      if (typeof QRious === 'undefined') {
        qrCodeImage.classList.add('hidden');
        showPaymentStatus('QR 코드를 생성할 수 없습니다. 결제 앱에서 직접 인보이스를 입력해주세요.', 'warning');
        return;
      }

      // 캔버스 생성
      const canvas = document.createElement('canvas');

      // QRious 인스턴스 생성
      const qr = new QRious({
        element: canvas,
        value: invoice,
        size: 160,
        foreground: '#000000',
        background: '#FFFFFF',
        level: 'M'
      });

      // 캔버스를 이미지로 변환
      const dataURL = canvas.toDataURL();
      qrCodeImage.src = dataURL;
      qrCodeImage.classList.remove('hidden');

    } catch (error) {
      console.error('QR Code generation error:', error);
      qrCodeImage.classList.add('hidden');
      showPaymentStatus('QR 코드 생성에 실패했습니다. 결제 앱에서 직접 인보이스를 입력해주세요.', 'warning');
    }
  }

  // 결제 상태 확인 시작
  function startPaymentStatusCheck() {
    if (paymentCheckInterval) {
      clearInterval(paymentCheckInterval);
    }

    // 즉시 한 번 확인
    checkPaymentStatus();

    // 1초마다 확인
    paymentCheckInterval = setInterval(checkPaymentStatus, 1000);

    // 20분 후 자동으로 확인 중단
    setTimeout(function () {
      if (paymentCheckInterval) {
        clearInterval(paymentCheckInterval);
        showPaymentStatus('결제 시간이 만료되었습니다. 다시 시도해주세요.', 'warning');
      }
    }, 1200000); // 20분
  }

  // 결제 상태 확인
  async function checkPaymentStatus() {
    if (!currentPaymentHash) return;

    try {
      const response = await fetch('/ln_payment/check_payment/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': window.CSRF_TOKEN
        },
        body: JSON.stringify({
          payment_hash: currentPaymentHash
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP 오류: ${response.status}`);
      }

      const data = await response.json();

      // API 응답 성공/실패 먼저 확인
      if (!data.success) {
        clearInterval(paymentCheckInterval);
        showPaymentStatus('결제 상태 확인 중 오류가 발생했습니다: ' + (data.error || '알 수 없는 오류'), 'danger');
        return;
      }

      // 결제 상태 확인
      if (data.status === 'paid') {
        // 결제 완료
        clearInterval(paymentCheckInterval);
        onPaymentCompleted();
      } else if (data.status === 'expired') {
        // 인보이스 만료
        clearInterval(paymentCheckInterval);
        showPaymentStatus('인보이스가 만료되었습니다. 다시 시도해주세요.', 'warning');
      }
      // 'pending' 상태는 계속 대기
    } catch (error) {
      console.error('Payment check error:', error);
      // 에러 발생시 조용히 처리 (계속 폴링)
    }
  }

  // 결제 완료 처리
  function onPaymentCompleted() {
    // QR 코드와 인보이스 영역 숨기기
    qrCodeImage.classList.add('hidden');
    invoiceTextContainer.classList.add('hidden');
    invoiceDetails.classList.add('hidden');

    // QR 코드 컨테이너에 성공 메시지 표시
    const qrCodeContainer = document.getElementById('qrCodeContainer');
    qrCodeContainer.innerHTML = `
      <div class="text-center py-4">
        <div class="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full mb-3">
          <i class="fas fa-check-circle text-2xl text-green-600 dark:text-green-400"></i>
        </div>
        <h3 class="text-lg font-bold text-green-600 dark:text-green-400 mb-2">결제 성공!</h3>
        <p class="text-xs text-gray-600 dark:text-gray-400">
          <strong>🎉 테스트 결제가 성공적으로 완료되었습니다!</strong><br>
          블링크 API 설정이 올바르게 확인되었습니다.
        </p>
      </div>
    `;

    // 결제 상태 메시지도 업데이트
    showPaymentStatus('✅ 테스트 결제 완료! 블링크 API 연동이 성공적으로 확인되었습니다.', 'success');
  }

  // 결제 상태 메시지 표시
  function showPaymentStatus(message, type) {
    let iconHtml = '';
    let className = 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-3';

    switch (type) {
      case 'success':
        className = 'bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-3';
        iconHtml = '<i class="fas fa-check-circle text-green-600 dark:text-green-400 mr-2"></i>';
        break;
      case 'danger':
        className = 'bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-3';
        iconHtml = '<i class="fas fa-exclamation-triangle text-red-600 dark:text-red-400 mr-2"></i>';
        break;
      case 'warning':
        className = 'bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3';
        iconHtml = '<i class="fas fa-clock text-yellow-600 dark:text-yellow-400 mr-2"></i>';
        break;
      default:
        iconHtml = '<i class="fas fa-clock text-blue-600 dark:text-blue-400 mr-2"></i>';
    }

    paymentStatus.className = className;
    paymentMessage.innerHTML = `<div class="flex items-center">${iconHtml}<span class="text-xs">${message}</span></div>`;
    paymentStatus.classList.remove('hidden');
  }

  // 페이지 언로드 시 폴링 정리
  window.addEventListener('beforeunload', function () {
    if (paymentCheckInterval) {
      clearInterval(paymentCheckInterval);
    }
  });

  // 인보이스 복사 함수
  function copyInvoiceToClipboard() {
    if (currentInvoice) {
      const tempInput = document.createElement('input');
      tempInput.value = currentInvoice;
      document.body.appendChild(tempInput);
      tempInput.select();
      document.execCommand('copy');
      document.body.removeChild(tempInput);
      showPaymentStatus('인보이스가 클립보드에 복사되었습니다.', 'success');
    }
  }
}); 