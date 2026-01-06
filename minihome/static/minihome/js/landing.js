document.addEventListener('DOMContentLoaded', () => {
  const modal = document.querySelector('[data-blog-modal]');
  const modalText = modal ? modal.querySelector('[data-modal-text]') : null;
  const modalImages = modal ? modal.querySelector('[data-modal-images]') : null;
  const closeButton = modal ? modal.querySelector('[data-modal-close]') : null;

  if (modal && closeButton) {
    closeButton.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  document.querySelectorAll('[data-blog-card]').forEach((card) => {
    card.addEventListener('click', () => {
      if (!modal || !modalText || !modalImages) {
        return;
      }
      const text = card.dataset.text || '';
      modalText.textContent = text;
      modalImages.innerHTML = '';

      const imageUrls = [
        card.dataset.image0,
        card.dataset.image1,
        card.dataset.image2,
        card.dataset.image3,
      ].filter((url) => url);

      imageUrls.forEach((url) => {
        const img = document.createElement('img');
        img.src = url;
        img.alt = '블로그 이미지';
        img.className = 'w-full h-40 object-cover rounded-xl';
        modalImages.appendChild(img);
      });

      modal.classList.remove('hidden');
    });
  });

  const mapTargets = document.querySelectorAll('[data-map]');
  if (mapTargets.length && window.naver && window.naver.maps) {
    mapTargets.forEach((target) => {
      const lat = parseFloat(target.dataset.lat || '');
      const lng = parseFloat(target.dataset.lng || '');
      if (Number.isNaN(lat) || Number.isNaN(lng)) {
        target.textContent = '좌표 정보가 없습니다.';
        target.classList.add('flex', 'items-center', 'justify-center', 'text-xs', 'text-slate-500');
        return;
      }
      const location = new naver.maps.LatLng(lat, lng);
      const map = new naver.maps.Map(target, {
        center: location,
        zoom: 14,
        zoomControl: false,
      });
      new naver.maps.Marker({
        position: location,
        map: map,
      });
    });
  }
});
