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

  const startButton = document.getElementById('startPaymentButton');
  const panel = document.getElementById('paymentWorkflowPanel');
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

  let transactionId = null;
  let countdownInterval = null;
  let pollInterval = null;
  let expiresAt = null;

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
      li.innerHTML = `
        <p class="log-title">${escapeHtml(log.message || '단계 업데이트')}</p>
        <span class="log-timestamp">${new Date(log.created_at).toLocaleString()}</span>
        ${log.detail && Object.keys(log.detail).length ? `<pre class="mt-2 text-xs text-gray-500 dark:text-gray-400 whitespace-pre-wrap">${escapeHtml(JSON.stringify(log.detail, null, 2))}</pre>` : ''}
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
    } else if (invoiceQrContainer) {
      invoiceQrContainer.classList.add('hidden');
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
    startButton.disabled = true;
    startButton.innerHTML = '<span class="flex items-center gap-2"><i class="fas fa-spinner fa-spin"></i> 준비 중...</span>';
    updateStatusText('재고 확인과 결제 준비를 진행하고 있습니다. 잠시만 기다려 주세요.');
    panel.classList.remove('hidden');

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
        handleStartError((data && data.error) || '결제 준비에 실패했습니다.');
        return;
      }

      transactionId = data.transaction.id;
      startButton.innerHTML = '<i class="fas fa-bolt"></i> 진행 중';
      updateTransaction(data.transaction);
      updateInvoice(data.invoice);
      updateStatusText('인보이스가 생성되었습니다. 라이트닝 지갑으로 QR을 스캔하거나 인보이스를 복사해 결제를 진행하세요.');
      startPolling();
    } catch (error) {
      console.warn(error);
      handleStartError(error.message || '결제 준비 중 오류가 발생했습니다. 다시 시도해 주세요.');
    }
  }

  function handleStartError(message) {
    updateStatusText(message, 'error');
    startButton.disabled = false;
    startButton.innerHTML = '<i class="fas fa-bolt"></i> 결제 절차 진행하기';
    transactionId = null;
    if (invoiceArea) {
      invoiceArea.classList.add('hidden');
    }
    if (invoicePanel) {
      invoicePanel.classList.add('hidden');
    }
    if (workflowLogContainer) {
      workflowLogContainer.classList.add('hidden');
    }
    if (invoiceQrContainer) {
      invoiceQrContainer.classList.add('hidden');
    }
    if (workflowLogList) {
      workflowLogList.innerHTML = '';
    }
  }

  function startCountdown() {
    if (!expiresAt) {
      return;
    }
    clearInterval(countdownInterval);
    invoiceTimer.classList.remove('hidden');
    countdownInterval = setInterval(() => {
      const remaining = expiresAt.getTime() - Date.now();
      if (remaining <= 0) {
        clearInterval(countdownInterval);
        invoiceTimerValue.textContent = '만료됨';
        updateStatusText('인보이스가 만료되었습니다. 잠시 후 화면이 새로고침되어 새 결제를 준비할 수 있습니다.', 'error');
        stopPolling();
        setTimeout(() => {
          window.location.reload();
        }, 1500);
        return;
      }
      const minutes = Math.floor(remaining / 1000 / 60);
      const seconds = Math.floor((remaining / 1000) % 60);
      invoiceTimerValue.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }, 1000);
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
      console.warn(error);
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
      console.warn(error);
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

  startButton?.addEventListener('click', startWorkflow);
  cancelPaymentButton?.addEventListener('click', cancelPayment);
  copyInvoiceButton?.addEventListener('click', copyInvoice);

})();
