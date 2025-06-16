function confirmStatusChange(checkbox) {
  // 체크박스의 초기 상태를 확인하여 현재 상태 파악
  const form = document.getElementById('toggleForm');
  const originalCheckbox = form.querySelector('input[name="is_active"]');
  const isCurrentlyActive = originalCheckbox.defaultChecked;
  const willBeActive = checkbox.checked;

  let message;
  if (willBeActive && !isCurrentlyActive) {
    message = '상품을 활성화하시겠습니까?\n\n활성화하면 고객들이 이 상품을 구매할 수 있습니다.';
  } else if (!willBeActive && isCurrentlyActive) {
    message = '상품을 비활성화하시겠습니까?\n\n비활성화하면 고객들이 이 상품을 구매할 수 없게 됩니다.\n상품 목록에서는 여전히 보이지만 구매가 불가능합니다.';
  }

  if (confirm(message)) {
    // 확인한 경우 폼 제출
    document.getElementById('toggleForm').submit();
  } else {
    // 취소한 경우 체크박스 상태를 원래대로 되돌림
    checkbox.checked = !checkbox.checked;
  }
}

function confirmDelete() {
  if (confirm('정말로 이 상품을 삭제하시겠습니까?\n\n이 작업은 되돌릴 수 없으며, 다음 데이터가 모두 삭제됩니다:\n- 상품 정보\n- 상품 이미지\n- 상품 옵션\n- 관련 주문 내역\n\n삭제하려면 "확인"을 클릭하세요.')) {
    // 삭제 폼 생성 및 제출
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = window.deleteProductUrl || '/products/delete/';
    
    const csrfToken = document.createElement('input');
    csrfToken.type = 'hidden';
    csrfToken.name = 'csrfmiddlewaretoken';
    csrfToken.value = document.querySelector('[name=csrfmiddlewaretoken]')?.value || window.csrfToken || '';
    
    form.appendChild(csrfToken);
    document.body.appendChild(form);
    form.submit();
  }
} 