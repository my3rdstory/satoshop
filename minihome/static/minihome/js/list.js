document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.minihome-card').forEach((card) => {
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        card.click();
      }
    });
  });
});
