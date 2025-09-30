(function () {
  const app = document.getElementById('paymentWorkflowApp');
  if (!app) {
    return;
  }

  const startUrl = app.dataset.startUrl;
  const statusUrlTemplate = app.dataset.statusUrlTemplate;
  const verifyUrlTemplate = app.dataset.verifyUrlTemplate;
  const cancelUrlTemplate = app.dataset.cancelUrlTemplate;
  const csrfToken = app.dataset.csrfToken || getCookie('csrftoken');
  const inventoryRedirectUrl = app.dataset.inventoryRedirectUrl || '';
  const cartFallbackUrl = app.dataset.cartUrl || '';

  const startButton = document.getElementById('startPaymentButton');
  const panel = document.getElementById('paymentWorkflowPanel');
  const defaultStartButtonMarkup = startButton ? startButton.innerHTML : '';
  const invoicePanel = document.getElementById('invoicePanel');
  const invoiceArea = document.getElementById('invoiceArea');
  const invoiceQrContainer = document.getElementById('invoiceQrContainer');
  const invoiceText = document.getElementById('invoiceText');
  const copyInvoiceButton = document.getElementById('copyInvoiceButton');
  const cancelPaymentButton = document.getElementById('cancelPaymentButton');
  const invoiceQrImage = document.getElementById('invoiceQrImage');
  const paymentStatusText = document.getElementById('paymentStatusText');
  const workflowLogList = document.getElementById('workflowLogList');
  const workflowLogContainer = document.getElementById('workflowLogContainer');
  const stepElements = Array.from(document.querySelectorAll('[data-step-index]'));
  const invoiceTimer = document.getElementById('invoiceTimer');
  const invoiceTimerValue = document.getElementById('invoiceTimerValue');
  const openWalletButton = document.getElementById('openWalletButton');

  let transactionId = null;
  let countdownInterval = null;
  let pollInterval = null;
  let expiresAt = null;
  let isInventoryRedirectMode = false;

  const stageLabelMap = {
    1: '1단계 · 재고 확인',
    2: '2단계 · 인보이스 발행',
    3: '3단계 · 결제 확인',
    4: '4단계 · 입금 확인',
    5: '5단계 · 주문 확정',
  };

  const statusLabelMap = {
    pending: '대기 중',
    processing: '진행 중',
    failed: '문제 발생',
    completed: '완료',
  };

  const logMessageMap = {
    '재고 예약 및 결제 준비 완료': '재고 확보가 완료되어 결제를 준비했습니다.',
    '인보이스 생성 완료': '결제에 사용할 인보이스를 발급했습니다.',
    '사용자 결제 대기 중': '지갑에서 결제 승인 신호를 기다리고 있습니다.',
    '사용자 결제 완료 감지': '결제 완료 신호를 받아 후속 단계를 진행합니다.',
    '인보이스 만료': '인보이스가 만료되었습니다. 새 결제가 필요합니다.',
    '결제 상태 확인 실패': '결제 상태 확인에 실패했습니다.',
    '스토어 지갑 입금 확인': '스토어 지갑으로 입금이 확인되었습니다.',
    '주문 저장 완료': '결제가 완료되어 주문을 저장했습니다.',
    '인보이스 생성 실패': '인보이스 생성에 실패했습니다.',
  };

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop().split(';').shift();
    }
    return '';
  }

  function formatUrl(template, id) {
    return template.replace('11111111-1111-1111-1111-111111111111', id);
  }

  function setStepState(currentStage, status) {
    stepElements.forEach((element) => {
      const idx = Number(element.dataset.stepIndex);
      element.classList.remove('is-active', 'is-complete');
      if (idx < currentStage) {
        element.classList.add('is-complete');
      } else if (idx === currentStage) {
        element.classList.add('is-active');
      }
    });

    if (status === 'completed') {
      stepElements.forEach((element) => element.classList.add('is-complete'));
    }

    if (status === 'failed') {
      paymentStatusText.classList.remove('bg-gray-50', 'dark:bg-gray-900');
      paymentStatusText.classList.add('bg-red-50', 'dark:bg-red-900/20', 'text-red-700', 'dark:text-red-300');
    } else {
      paymentStatusText.classList.remove('bg-red-50', 'dark:bg-red-900/20', 'text-red-700', 'dark:text-red-300');
      paymentStatusText.classList.add('bg-gray-50', 'dark:bg-gray-900', 'text-gray-700', 'dark:text-gray-300');
    }
  }

  function renderLogs(logs) {
    if (!workflowLogList) {
      return;
    }
    workflowLogList.innerHTML = '';
    if (workflowLogContainer) {
      if (!logs || logs.length === 0) {
        workflowLogContainer.classList.add('hidden');
      } else {
        workflowLogContainer.classList.remove('hidden');
      }
    }

    logs.forEach((log) => {
      const li = document.createElement('li');
      const translated = translateLogMessage(log);
      const statusText = statusLabelMap[log.status] || '진행 업데이트';
      const detailHint = extractDetailHint(log.detail, log.status);
      li.innerHTML = `
        <div class="log-entry">
          <div class="log-meta">
            <span class="log-time">${formatLogTime(log.created_at)}</span>
            <span class="log-status ${getStatusBadgeClass(log.status)}">${escapeHtml(statusText)}</span>
          </div>
          <p class="log-message"><span class="log-stage-label">${escapeHtml(translated.stage)}</span>${escapeHtml(translated.message)}</p>
          ${detailHint ? `<p class="log-detail">${escapeHtml(detailHint)}</p>` : ''}
        </div>
      `;
      workflowLogList.prepend(li);
    });
  }

  function escapeHtml(text) {
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    };
    return text ? text.replace(/[&<>"']/g, (m) => map[m]) : '';
  }

  function formatLogTime(isoString) {
    if (!isoString) {
      return '';
    }
    const date = new Date(isoString);
    if (Number.isNaN(date.getTime())) {
      return '';
    }
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }

  function getStatusBadgeClass(status) {
    switch (status) {
      case 'completed':
        return 'log-status--completed';
      case 'failed':
        return 'log-status--failed';
      case 'processing':
        return 'log-status--processing';
      case 'pending':
      default:
        return 'log-status--pending';
    }
  }

  function translateLogMessage(log) {
    const stage = stageLabelMap[log.stage] || '단계 진행';
    const mappedMessage = logMessageMap[log.message] || log.message || '단계가 업데이트되었습니다.';
    return {
      stage,
      message: mappedMessage,
    };
  }

  function extractDetailHint(detail, status) {
    if (!detail || typeof detail !== 'object') {
      return '';
    }
    if (typeof detail.error === 'string' && detail.error.trim()) {
      return detail.error;
    }
    if (typeof detail.status === 'string') {
      if (detail.status === 'paid') {
        return '결제 완료 신호를 확인했습니다.';
      }
      if (detail.status === 'pending') {
        return '결제 승인 신호를 기다리는 중입니다.';
      }
      if (detail.status === 'expired') {
        return '결제 시간이 만료되었습니다.';
      }
    }
    if (detail.previous_payment_hash) {
      return '이전 인보이스를 취소하고 새 인보이스를 준비했습니다.';
    }
    if (detail.order_number) {
      return `주문 번호 ${detail.order_number}로 저장되었습니다.`;
    }
    if (status === 'failed') {
      return '문제를 해결한 뒤 다시 시도해주세요.';
    }
    return '';
  }

  function updateInvoice(invoice) {
    if (!invoice) {
      return;
    }
    invoiceArea.classList.remove('hidden');
    if (invoicePanel) {
      invoicePanel.classList.remove('hidden');
    }
    invoiceText.value = invoice.payment_request || '';
    if (invoice.payment_request) {
      const qrApi = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(invoice.payment_request)}&ts=${Date.now()}`;
      if (invoiceQrContainer) {
        invoiceQrContainer.classList.remove('hidden');
      }
      invoiceQrImage.src = qrApi;
      if (openWalletButton) {
        const lightningUri = invoice.payment_request.startsWith('lightning:')
          ? invoice.payment_request
          : `lightning:${invoice.payment_request}`;
        openWalletButton.href = lightningUri;
        openWalletButton.classList.remove('hidden');
      }
    } else if (invoiceQrContainer) {
      invoiceQrContainer.classList.add('hidden');
      if (openWalletButton) {
        openWalletButton.classList.add('hidden');
        openWalletButton.removeAttribute('href');
      }
    }
    if (invoice.expires_at) {
      expiresAt = new Date(invoice.expires_at);
      startCountdown();
    }
  }

  function updateTransaction(transaction) {
    if (!transaction) {
      return;
    }
    if (panel) {
      panel.classList.remove('hidden');
    }
    setStepState(Number(transaction.current_stage || 1), transaction.status);
    renderLogs(transaction.logs || []);
    if (transaction.invoice) {
      updateInvoice(transaction.invoice);
    }

    if (transaction.redirect_url) {
      setTimeout(() => {
        window.location.href = transaction.redirect_url;
      }, 1200);
    }
  }

  function updateStatusText(message, variant = 'info') {
    if (!paymentStatusText) {
      return;
    }
    paymentStatusText.textContent = message;
    paymentStatusText.classList.remove('status-banner--error');
    if (variant === 'error') {
      paymentStatusText.classList.add('status-banner--error');
    }
  }

  async function startWorkflow() {
    if (!startUrl) {
      return;
    }
    restoreStartButtonDefault();
    startButton.disabled = true;
    startButton.innerHTML = '<span class="flex items-center gap-2"><i class="fas fa-spinner fa-spin"></i> 준비 중...</span>';
    updateStatusText('재고 확인과 결제 준비를 진행하고 있습니다. 잠시만 기다려 주세요.');
    try {
      const response = await fetch(startUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({})
      });

      let data;
      try {
        data = await response.json();
      } catch (parseError) {
        data = {};
      }

      if (!response.ok || !data.success) {
        handleStartError((data && data.error) || '결제 준비에 실패했습니다.', data && data.error_code);
        return;
      }

      transactionId = data.transaction.id;
      startButton.innerHTML = '<i class="fas fa-bolt"></i> 진행 중';
      updateTransaction(data.transaction);
      updateInvoice(data.invoice);
      updateStatusText('인보이스가 생성되었습니다. 라이트닝 지갑으로 QR을 스캔하거나 인보이스를 복사해 결제를 진행하세요.');
      startPolling();
    } catch (error) {
      handleStartError(error.message || '결제 준비 중 오류가 발생했습니다. 다시 시도해 주세요.', error && error.code);
    }
  }

  function resetWorkflowView() {
    stopPolling();
    clearInterval(countdownInterval);
    countdownInterval = null;
    expiresAt = null;

    if (panel) {
      panel.classList.add('hidden');
    }
    if (invoiceArea) {
      invoiceArea.classList.add('hidden');
    }
    if (invoicePanel) {
      invoicePanel.classList.add('hidden');
    }
    if (invoiceQrContainer) {
      invoiceQrContainer.classList.add('hidden');
    }
    if (invoiceQrImage) {
      invoiceQrImage.removeAttribute('src');
    }
    if (invoiceText) {
      invoiceText.value = '';
    }
    if (openWalletButton) {
      openWalletButton.classList.add('hidden');
      openWalletButton.removeAttribute('href');
    }
    if (workflowLogContainer) {
      workflowLogContainer.classList.add('hidden');
    }
    if (workflowLogList) {
      workflowLogList.innerHTML = '';
    }
    if (invoiceTimer) {
      invoiceTimer.classList.add('hidden');
    }
    if (invoiceTimerValue) {
      invoiceTimerValue.textContent = '02:00';
    }
  }

  function handleStartError(message, errorCode) {
    const displayMessage = errorCode === 'inventory_unavailable'
      ? '재고가 부족하여 결제를 진행할 수 없습니다. 상품 정보를 다시 확인한 뒤 다시 시도해주세요.'
      : message;
    updateStatusText(displayMessage || '결제 준비에 실패했습니다.', 'error');
    resetWorkflowView();
    transactionId = null;
    if (!startButton) {
      return;
    }
    startButton.disabled = false;
    if (errorCode === 'inventory_unavailable') {
      setStartButtonToRedirect();
    } else {
      restoreStartButtonDefault();
    }
  }

  function redirectToProduct(event) {
    if (event) {
      event.preventDefault();
    }
    const targetUrl = inventoryRedirectUrl || cartFallbackUrl || '/';
    window.location.href = targetUrl;
  }

  function setStartButtonToRedirect() {
    if (!startButton) {
      return;
    }
    if (!isInventoryRedirectMode) {
      startButton.removeEventListener('click', startWorkflow);
      startButton.addEventListener('click', redirectToProduct);
    }
    startButton.innerHTML = '<span class="flex items-center gap-2"><i class="fas fa-store"></i> 상품 다시 확인하기</span>';
    isInventoryRedirectMode = true;
  }

  function restoreStartButtonDefault() {
    if (!startButton) {
      return;
    }
    if (isInventoryRedirectMode) {
      startButton.removeEventListener('click', redirectToProduct);
      startButton.addEventListener('click', startWorkflow);
    }
    startButton.innerHTML = defaultStartButtonMarkup || '<i class="fas fa-bolt"></i> 결제 절차 진행하기';
    isInventoryRedirectMode = false;
  }

  async function cancelDueToExpiration() {
    if (!transactionId || !cancelUrlTemplate) {
      return;
    }
    try {
      await fetch(formatUrl(cancelUrlTemplate, transactionId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ reason: 'invoice_expired_client' }),
      });
    } catch (error) {
      /* no-op: 상태 배너로 안내 */
    } finally {
      transactionId = null;
      resetWorkflowView();
    }
  }

  function startCountdown() {
    if (!expiresAt) {
      return;
    }
    clearInterval(countdownInterval);
    if (invoiceTimer) {
      invoiceTimer.classList.remove('hidden');
    }

    const tick = () => {
      const remaining = expiresAt.getTime() - Date.now();
      if (remaining <= 0) {
        clearInterval(countdownInterval);
        countdownInterval = null;
        if (invoiceTimerValue) {
          invoiceTimerValue.textContent = '만료됨';
        }
        updateStatusText('인보이스가 만료되었습니다. 잠시 후 화면이 새로고침되어 새 결제를 준비할 수 있습니다.', 'error');
        stopPolling();
        resetWorkflowView();
        cancelDueToExpiration()
          .catch(() => null)
          .finally(() => {
            if (startButton) {
              startButton.disabled = false;
              restoreStartButtonDefault();
            }
            setTimeout(() => {
              window.location.reload();
            }, 1500);
          });
        return;
      }
      const minutes = Math.floor(remaining / 1000 / 60);
      const seconds = Math.floor((remaining / 1000) % 60);
      if (invoiceTimerValue) {
        invoiceTimerValue.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      }
    };

    tick();
    countdownInterval = setInterval(tick, 1000);
  }

  function startPolling() {
    stopPolling();
    pollInterval = setInterval(verifyPayment, 4000);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  async function verifyPayment() {
    if (!transactionId) {
      return;
    }
    try {
      const response = await fetch(formatUrl(verifyUrlTemplate, transactionId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({})
      });
      if (!response.ok) {
        throw new Error('결제 상태를 확인할 수 없습니다.');
      }
      const data = await response.json();
      if (!data.success) {
        if (data.error) {
          updateStatusText(data.error, 'error');
          stopPolling();
        }
        return;
      }
      updateTransaction(data.transaction);
      if (data.status === 'paid') {
        updateStatusText('결제가 확인되었습니다. 주문을 저장하고 있습니다...');
        stopPolling();
      } else if (data.status === 'pending') {
        updateStatusText('결제를 확인 중입니다. 잠시만 기다려 주세요.');
      }
    } catch (error) {
      updateStatusText('결제 상태 확인 중 오류가 발생했습니다. 네트워크 상태를 확인한 후 다시 시도해주세요.', 'error');
    }
  }

  async function cancelPayment() {
    if (!transactionId) {
      return;
    }
    cancelPaymentButton.disabled = true;
    cancelPaymentButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>취소 중';
    try {
      const response = await fetch(formatUrl(cancelUrlTemplate, transactionId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ reason: 'user_cancel' })
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || '결제를 취소할 수 없습니다.');
      }
      stopPolling();
      clearInterval(countdownInterval);
      updateTransaction(data.transaction);
      updateStatusText('결제가 취소되었습니다. 새로운 결제를 진행하려면 다시 시도하세요.');
      setTimeout(() => {
        window.location.reload();
      }, 800);
    } catch (error) {
      updateStatusText(error.message, 'error');
    } finally {
      cancelPaymentButton.disabled = false;
      cancelPaymentButton.innerHTML = '<i class="fas fa-ban mr-2"></i>결제 취소';
    }
  }

  function copyInvoice() {
    if (!invoiceText.value) {
      return;
    }
    navigator.clipboard.writeText(invoiceText.value)
      .then(() => {
        updateStatusText('인보이스가 복사되었습니다. 라이트닝 지갑에 붙여넣어 결제를 진행하세요.');
      })
      .catch(() => {
        updateStatusText('인보이스 복사에 실패했습니다. 직접 선택하여 복사해주세요.', 'error');
      });
  }

  function openWallet(event) {
    if (!openWalletButton || !invoiceText) {
      return;
    }
    if (event) {
      event.preventDefault();
    }
    const invoiceValue = invoiceText.value.trim();
    if (!invoiceValue) {
      updateStatusText('인보이스가 준비되면 지갑을 열 수 있습니다.', 'error');
      return;
    }
    const lightningUri = invoiceValue.startsWith('lightning:') ? invoiceValue : `lightning:${invoiceValue}`;
    openWalletButton.href = lightningUri;
    window.location.href = lightningUri;
  }

  startButton?.addEventListener('click', startWorkflow);
  cancelPaymentButton?.addEventListener('click', cancelPayment);
  copyInvoiceButton?.addEventListener('click', copyInvoice);
  openWalletButton?.addEventListener('click', openWallet);

})();
