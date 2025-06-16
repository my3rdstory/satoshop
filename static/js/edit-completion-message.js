document.addEventListener('DOMContentLoaded', function () {
  const textarea = document.getElementById('completion_message');
  const preview = document.getElementById('messagePreview');

  // 실시간 미리보기 업데이트
  textarea.addEventListener('input', function () {
    const message = this.value.trim();
    if (message) {
      // 줄바꿈을 <br>로 변환하여 미리보기에 표시
      const formattedMessage = message.replace(/\n/g, '<br>');
      preview.innerHTML = formattedMessage;
    } else {
      preview.innerHTML = '<em class="has-text-grey">메시지를 입력하면 여기에 미리보기가 표시됩니다.</em>';
    }
  });
}); 