(function () {
  const app = document.getElementById('paymentWorkflowApp');
  if (!app) {
    return;
  }

  const startButton = document.getElementById('startPaymentButton');
  const workflowPanel = document.getElementById('paymentWorkflowPanel');
  const statusBanner = document.getElementById('paymentStatusText');

  if (statusBanner) {
    statusBanner.setAttribute('role', 'status');
    statusBanner.setAttribute('aria-live', 'polite');
  }

  if (startButton) {
    try {
      startButton.focus({ preventScroll: true });
    } catch (error) {
      startButton.focus();
    }
    startButton.addEventListener('click', () => {
      if (!workflowPanel) {
        return;
      }
      setTimeout(() => {
        workflowPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 300);
    });
  }
})();
