document.addEventListener('DOMContentLoaded', () => {
  const selectAll = document.getElementById('select-all');
  const checkboxes = Array.from(document.querySelectorAll('.history-checkbox'));
  const deleteButton = document.getElementById('delete-button');
  const form = deleteButton ? deleteButton.closest('form') : null;

  const updateButtonState = () => {
    const checkedCount = checkboxes.filter((box) => box.checked).length;
    if (deleteButton) {
      deleteButton.disabled = checkedCount === 0;
    }
    if (selectAll) {
      selectAll.checked = checkedCount > 0 && checkedCount === checkboxes.length;
      selectAll.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
    }
  };

  if (selectAll) {
    selectAll.addEventListener('change', () => {
      checkboxes.forEach((box) => {
        box.checked = selectAll.checked;
      });
      updateButtonState();
    });
  }

  checkboxes.forEach((box) => {
    box.addEventListener('change', updateButtonState);
  });

  if (form && deleteButton) {
    form.addEventListener('submit', (event) => {
      const selected = checkboxes.filter((box) => box.checked).length;
      if (selected === 0) {
        event.preventDefault();
        return;
      }

      const warningMessage = [
        `선택한 ${selected}건의 구입 이력을 삭제합니다.`,
        '삭제 후에는 어떤 형태로도 복구할 수 없습니다.',
        '정말로 삭제하시겠습니까?'
      ].join('\n');

      if (!window.confirm(warningMessage)) {
        event.preventDefault();
      }
    });
  }

  updateButtonState();
});
