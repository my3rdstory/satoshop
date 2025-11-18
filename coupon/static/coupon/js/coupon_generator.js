(function () {
  const state = {
    amount: 0,
    invoice: '',
    paymentHash: '',
    invoiceExpiresAt: null,
    countdownTimer: null,
    statusTimer: null,
    invoicePaid: false,
    couponBaseCanvas: null,
    couponMetadata: null,
  };

  document.addEventListener('DOMContentLoaded', initCouponPage);

  function initCouponPage() {
    const configNode = document.getElementById('coupon-config');
    if (!configNode) return;

    const config = JSON.parse(configNode.textContent || '{}');
    const grid = document.querySelector('.coupon-grid');
    if (!grid) return;

    const routes = {
      create: grid.dataset.createUrl,
      status: grid.dataset.statusUrl,
    };

    const elements = {
      presetButtons: document.querySelectorAll('.preset-button'),
      amountInput: document.getElementById('coupon-amount'),
      selectedAmount: document.getElementById('selected-amount'),
      totalAmount: document.getElementById('total-amount'),
      createButton: document.getElementById('create-invoice-btn'),
      invoiceCard: document.querySelector('.coupon-card--invoice'),
      invoicePlaceholder: document.getElementById('invoice-placeholder'),
      invoicePanel: document.getElementById('invoice-panel'),
      invoiceCanvas: document.getElementById('invoice-qr-canvas'),
      invoiceTextarea: document.getElementById('invoice-text'),
      invoiceCopyButton: document.getElementById('copy-invoice-btn'),
      invoiceBadge: document.getElementById('invoice-status-badge'),
      invoiceCountdown: document.getElementById('invoice-countdown'),
      invoiceAlert: document.getElementById('invoice-alert'),
      settledMessage: document.getElementById('invoice-settled-message'),
      messageInput: document.getElementById('coupon-message'),
      messageCount: document.getElementById('message-count'),
      downloadButton: document.getElementById('download-coupon-btn'),
      previewCanvas: document.getElementById('coupon-preview-canvas'),
      previewContainer: document.getElementById('coupon-preview'),
      paymentHint: document.getElementById('payment-gate-hint'),
    };

    attachPresetHandlers(elements, config);
    attachInputHandlers(elements, config);
    attachInvoiceHandlers(elements, routes);
    attachMessageHandlers(elements);
  }

  function attachPresetHandlers(elements, config) {
    elements.presetButtons.forEach((button) => {
      button.addEventListener('click', () => {
        elements.presetButtons.forEach((btn) => btn.classList.remove('is-active'));
        button.classList.add('is-active');
        const value = Number(button.dataset.amount || '0');
        updateAmount(value, elements, config);
      });
    });
  }

  function attachInputHandlers(elements, config) {
    elements.amountInput.addEventListener('input', (event) => {
      const value = Number(event.target.value || '0');
      updateAmount(value, elements, config, true);
      elements.presetButtons.forEach((btn) => btn.classList.remove('is-active'));
    });
  }

  function attachInvoiceHandlers(elements, routes) {
    elements.createButton.addEventListener('click', () => {
      if (!state.amount) {
        showInlineToast('먼저 쿠폰 수량을 선택하세요.');
        return;
      }
      requestInvoice(routes, elements);
    });

    elements.invoiceCopyButton.addEventListener('click', () => {
      if (!state.invoice) return;
      navigator.clipboard?.writeText(state.invoice).then(() => {
        showInlineToast('인보이스를 복사했어요.');
      }).catch(() => showInlineToast('복사에 실패했어요. 직접 선택해서 복사해 주세요.'));
    });

    elements.downloadButton.addEventListener('click', () => {
      if (!state.invoicePaid) return;
      downloadCouponImage(elements);
    });
  }

  function attachMessageHandlers(elements) {
    if (!elements.messageInput) return;
    elements.messageInput.addEventListener('input', () => {
      const length = elements.messageInput.value.length;
      elements.messageCount.textContent = `${length} / ${elements.messageInput.maxLength}`;
      if (state.invoicePaid) {
        renderCouponPreview(elements);
      }
    });
  }

  function updateAmount(value, elements, config, skipSanitize) {
    const max = config.max_amount || 10000;
    const sanitized = skipSanitize ? clamp(value, 0, max) : value;
    state.amount = clamp(sanitized, 0, max);
    elements.amountInput.value = state.amount || '';
    elements.selectedAmount.textContent = state.amount.toLocaleString('en-US');
    const total = state.amount + (config.service_fee || 5);
    elements.totalAmount.textContent = total.toLocaleString('en-US');
  }

  function requestInvoice(routes, elements) {
    lockCreateButton(elements.createButton, true);
    resetInvoiceState(elements);

    fetch(routes.create, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ amount: state.amount }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (!data.success) {
          throw new Error(data.error || '인보이스 생성 실패');
        }
        state.invoice = data.invoice;
        state.paymentHash = data.payment_hash;
        elements.invoiceTextarea.value = data.invoice;
        drawInvoiceQr(elements.invoiceCanvas, data.invoice);
        toggleInvoicePanel(true, elements);
        updateTotalsFromResponse(data, elements);
        startCountdown(data.expires_at, elements);
        const statusUrl = buildStatusUrl(routes, data.payment_hash);
        startStatusPolling(statusUrl, elements);
        showInlineToast('라이트닝 인보이스가 준비됐습니다.');
      })
      .catch((error) => {
        console.error(error);
        showInlineToast(error.message || '인보이스 생성 중 오류가 발생했습니다.');
      })
      .finally(() => lockCreateButton(elements.createButton, false));
  }

  function buildStatusUrl(routes, hash) {
    const placeholder = routes.status || '';
    if (placeholder.includes('__HASH__')) {
      return placeholder.replace('__HASH__', encodeURIComponent(hash));
    }
    if (placeholder) {
      return `${placeholder}${encodeURIComponent(hash)}/status/`;
    }
    const fallbackBase = (routes.create || '/coupon/invoice/').replace(/invoice\/?$/, '');
    return `${fallbackBase}invoice/${encodeURIComponent(hash)}/status/`;
  }

  function resetInvoiceState(elements) {
    elements.invoicePlaceholder?.classList.remove('hidden');
    elements.invoicePanel?.classList.add('hidden');
    elements.invoicePanel?.classList.remove('settled');
    elements.invoiceTextarea.value = '';
    elements.invoiceBadge.textContent = '대기중';
    elements.invoiceBadge.classList.remove('badge--success');
    elements.invoiceBadge.classList.add('badge--pending');
    elements.invoiceAlert.textContent = '결제가 확인되면 다음 단계에서 쿠폰 이미지를 만들 수 있습니다.';
    elements.invoiceCard?.classList.remove('hidden');
    elements.settledMessage?.classList.add('hidden');
    if (elements.paymentHint) {
      elements.paymentHint.textContent = '⚠️ 결제가 완료되면 다운로드 버튼이 활성화됩니다.';
    }
    state.invoicePaid = false;
    toggleDownloadButton(elements.downloadButton, false);
    const previewPlaceholder = elements.previewContainer?.querySelector('p');
    previewPlaceholder?.classList.remove('hidden');
    elements.previewCanvas?.classList.add('hidden');
    state.couponBaseCanvas = null;
    state.couponMetadata = null;
    elements.invoicePanel?.querySelector('.invoice-panel__qr')?.classList.remove('hidden');
    elements.invoicePanel?.querySelector('.invoice-panel__details')?.classList.remove('hidden');
    elements.invoiceBadge.classList.remove('hidden');
    elements.invoiceCountdown?.closest('.invoice-panel__status')?.classList.remove('hidden');
    clearTimers();
  }

  function toggleInvoicePanel(show, elements) {
    if (show) {
      elements.invoicePlaceholder.classList.add('hidden');
      elements.invoicePanel.classList.remove('hidden');
    } else {
      elements.invoicePlaceholder.classList.remove('hidden');
      elements.invoicePanel.classList.add('hidden');
    }
  }

  function drawInvoiceQr(canvas, invoice) {
    if (!canvas || typeof QRious === 'undefined') return;
    const lightningUri = invoice.startsWith('lightning:') ? invoice : `lightning:${invoice}`;
    new QRious({
      element: canvas,
      value: lightningUri,
      size: 340,
      background: '#ffffff',
      foreground: '#111827',
      level: 'H',
    });
  }

  function updateTotalsFromResponse(data, elements) {
    elements.selectedAmount.textContent = Number(data.coupon_amount_sats || 0).toLocaleString('en-US');
    elements.totalAmount.textContent = Number(data.total_amount_sats || 0).toLocaleString('en-US');
  }

  function startCountdown(expiresAt, elements) {
    if (!expiresAt) return;
    const deadline = new Date(expiresAt).getTime();
    state.invoiceExpiresAt = deadline;
    elements.invoiceCountdown.textContent = formatCountdown(deadline - Date.now());

    state.countdownTimer = window.setInterval(() => {
      const diff = deadline - Date.now();
      if (diff <= 0) {
        clearInterval(state.countdownTimer);
        state.countdownTimer = null;
        elements.invoiceCountdown.textContent = '만료됨';
        if (!state.invoicePaid) {
          showInlineToast('인보이스가 만료되었어요. 다시 생성해 주세요.');
        }
        return;
      }
      elements.invoiceCountdown.textContent = formatCountdown(diff);
    }, 1_000);
  }

  function startStatusPolling(statusUrl, elements) {
    if (!statusUrl) return;
    state.statusTimer = window.setInterval(() => {
      fetch(statusUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then((response) => response.json())
        .then((data) => {
          if (!data.success) return;
          if (data.status === 'paid') {
            markInvoicePaid(elements);
          }
        })
        .catch(() => {
          // 무시하고 다음 루프에서 재시도
        });
    }, 3_000);
  }

  function markInvoicePaid(elements) {
    clearInterval(state.statusTimer);
    state.statusTimer = null;
    state.invoicePaid = true;
    elements.invoiceBadge.textContent = '결제완료';
    elements.invoiceBadge.classList.remove('badge--pending');
    elements.invoiceBadge.classList.add('badge--success');
    elements.invoiceAlert.textContent = '입금이 확인되었습니다! 메시지를 적고 쿠폰 이미지를 내려받으세요.';
    elements.invoicePlaceholder?.classList.add('hidden');
    elements.invoicePanel?.classList.remove('hidden');
    elements.invoicePanel?.classList.add('settled');
    elements.invoicePanel?.querySelector('.invoice-panel__qr')?.classList.add('hidden');
    elements.invoicePanel?.querySelector('.invoice-panel__details')?.classList.add('hidden');
    elements.invoiceBadge.classList.add('hidden');
    elements.invoiceCountdown?.closest('.invoice-panel__status')?.classList.add('hidden');
    elements.settledMessage?.classList.remove('hidden');
    if (elements.paymentHint) {
      elements.paymentHint.textContent = '✅ 결제가 확인됐어요! 메시지를 적고 이미지를 내려받으세요.';
    }
    toggleDownloadButton(elements.downloadButton, true);
    renderCouponPreview(elements);
  }

  function renderCouponPreview(elements) {
    const canvas = elements.previewCanvas;
    const context = canvas.getContext('2d');
    const base = getOrCreateCouponBaseCanvas(elements);
    const metadata = getOrCreateCouponMetadata();
    if (!base || !metadata) {
      showInlineToast('유효한 인보이스를 찾을 수 없습니다. 다시 생성해 주세요.');
      return;
    }
    canvas.width = base.width;
    canvas.height = base.height;
    context.drawImage(base, 0, 0);

    context.font = '16px "Noto Sans KR", sans-serif';
    context.fillStyle = '#3d4356';
    const message = elements.messageInput.value || '메시지를 입력해 주세요.';
    wrapText(context, message, 332, 130, 188, 24);

    elements.previewContainer.querySelector('p')?.classList.add('hidden');
    canvas.classList.remove('hidden');
    metadata.message = elements.messageInput.value;
    elements.previewCanvas.dataset.metadata = JSON.stringify(metadata);
  }

  function getOrCreateCouponBaseCanvas(elements) {
    if (state.couponBaseCanvas) {
      return state.couponBaseCanvas;
    }
    if (!state.invoice) {
      return null;
    }
    const width = 560;
    const height = 320;
    const base = document.createElement('canvas');
    base.width = width;
    base.height = height;
    const ctx = base.getContext('2d');

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = '#f4c089';
    ctx.lineWidth = 4;
    ctx.strokeRect(10, 10, width - 20, height - 20);

    const qrCanvas = document.createElement('canvas');
    const metadata = getOrCreateCouponMetadata();
    if (!metadata) {
      return null;
    }
    const qrPayload = metadata.qr_payload || '';
    new QRious({
      element: qrCanvas,
      value: qrPayload,
      size: height - 40,
      background: '#ffffff',
      foreground: '#111827',
      level: 'H',
    });
    const qrOffsetX = 16;
    const qrOffsetY = 20;
    ctx.drawImage(qrCanvas, qrOffsetX, qrOffsetY, height - 40, height - 40);

    ctx.fillStyle = '#fff4dd';
    ctx.fillRect(320, 24, 216, 272);

    ctx.fillStyle = '#b072ff';
    ctx.font = 'bold 16px "DotGothic16", "Noto Sans KR", sans-serif';
    ctx.fillText('SatoShop Coupon', 332, 50);

    ctx.fillStyle = '#1f2533';
    ctx.font = 'bold 26px "Noto Sans KR", sans-serif';
    ctx.fillText(`${state.amount.toLocaleString('en-US')} sats`, 332, 88);

    ctx.strokeStyle = '#f4c089';
    ctx.strokeRect(330, 100, 188, 1);

    state.couponBaseCanvas = base;
    return base;
  }

  function getOrCreateCouponMetadata() {
    if (state.couponMetadata) {
      return state.couponMetadata;
    }
    if (!state.invoice) {
      return null;
    }
    const invoiceValue = state.invoice.startsWith('lightning:')
      ? state.invoice
      : `lightning:${state.invoice}`;
    const couponId = crypto.randomUUID ? crypto.randomUUID() : `coupon-${Date.now()}`;
    const issuedAt = new Date().toISOString();
    state.couponMetadata = {
      type: 'satoshop_coupon',
      coupon_id: couponId,
      amount_sats: state.amount,
      message: '',
      issued_at: issuedAt,
      invoice: invoiceValue,
      qr_payload: invoiceValue,
    };
    return state.couponMetadata;
  }

  function downloadCouponImage(elements) {
    renderCouponPreview(elements);
    const canvas = elements.previewCanvas;
    const link = document.createElement('a');
    const metadata = canvas.dataset.metadata ? JSON.parse(canvas.dataset.metadata) : {};
    link.download = `satoshop-coupon-${metadata.coupon_id || Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    showInlineToast('쿠폰 이미지를 내려받았어요.');
  }

  function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
    const paragraphs = text.split(/\n+/);
    paragraphs.forEach((paragraph, paragraphIndex) => {
      const words = paragraph.split(' ');
      let line = '';
      words.forEach((word, index) => {
        const testLine = `${line}${word} `;
        const metrics = ctx.measureText(testLine);
        if (metrics.width > maxWidth && index > 0) {
          ctx.fillText(line, x, y);
          line = `${word} `;
          y += lineHeight;
        } else {
          line = testLine;
        }
      });
      ctx.fillText(line, x, y);
      if (paragraphIndex < paragraphs.length - 1) {
        y += lineHeight;
      }
    });
  }

  function toggleDownloadButton(button, enabled) {
    if (!button) return;
    button.disabled = !enabled;
    if (enabled) {
      button.classList.remove('disabled');
    } else {
      button.classList.add('disabled');
    }
  }

  function lockCreateButton(button, loading) {
    if (!button) return;
    button.disabled = loading;
    button.classList.toggle('disabled', loading);
    if (loading) {
      button.dataset.originalText = button.innerHTML;
      button.innerHTML = '<span class="animate-pulse">인보이스 생성중...</span>';
    } else if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
      delete button.dataset.originalText;
    }
  }

  function showInlineToast(message) {
    if (!message) return;
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.className = 'fixed bottom-6 left-1/2 -translate-x-1/2 px-4 py-2 rounded-xl text-sm bg-black/80 text-white z-50';
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.classList.add('opacity-0');
      setTimeout(() => toast.remove(), 300);
    }, 1800);
  }

  function formatCountdown(ms) {
    const totalSeconds = Math.max(0, Math.floor(ms / 1000));
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    return `${minutes}:${seconds}`;
  }

  function clearTimers() {
    if (state.countdownTimer) {
      clearInterval(state.countdownTimer);
      state.countdownTimer = null;
    }
    if (state.statusTimer) {
      clearInterval(state.statusTimer);
      state.statusTimer = null;
    }
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function getCsrfToken() {
    if (window.csrfToken) return window.csrfToken;
    const cookie = document.cookie.split(';').map((item) => item.trim()).find((item) => item.startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
  }
})();
