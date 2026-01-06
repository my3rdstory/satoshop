document.addEventListener('DOMContentLoaded', () => {
  const modal = document.querySelector('[data-blog-modal]');
  const modalText = modal ? modal.querySelector('[data-modal-text]') : null;
  const modalImages = modal ? modal.querySelector('[data-modal-images]') : null;
  const closeButton = modal ? modal.querySelector('[data-modal-close]') : null;
  const postsPerPage = 4;

  if (modal && closeButton) {
    closeButton.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  const getImageUrl = (card, key) => {
    return card.dataset[key] || card.getAttribute(`data-${key}`) || '';
  };

  const bindBlogCards = (container) => {
    container.querySelectorAll('[data-blog-card]').forEach((card) => {
    card.addEventListener('click', () => {
      if (!modal || !modalText || !modalImages) {
        return;
      }
      const text = card.dataset.text || '';
      modalText.textContent = text;
      modalImages.innerHTML = '';

      const imageUrls = [
        getImageUrl(card, 'image0'),
        getImageUrl(card, 'image1'),
        getImageUrl(card, 'image2'),
        getImageUrl(card, 'image3'),
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
  };

  const initPagination = (section) => {
    const list = section.querySelector('[data-blog-list]');
    const pagination = section.querySelector('[data-blog-pagination]');
    if (!list || !pagination) return;

    const cards = Array.from(list.querySelectorAll('[data-blog-card]'));
    if (cards.length <= postsPerPage) {
      pagination.classList.add('hidden');
      return;
    }

    const totalPages = Math.ceil(cards.length / postsPerPage);
    const indicator = pagination.querySelector('[data-page-indicator]');
    const prevBtn = pagination.querySelector('[data-page-prev]');
    const nextBtn = pagination.querySelector('[data-page-next]');
    let currentPage = 1;

    const renderPage = (page) => {
      currentPage = page;
      const start = (page - 1) * postsPerPage;
      const end = start + postsPerPage;
      cards.forEach((card, index) => {
        card.classList.toggle('hidden', index < start || index >= end);
      });
      if (indicator) {
        indicator.textContent = `${currentPage} / ${totalPages}`;
      }
      if (prevBtn) {
        prevBtn.disabled = currentPage === 1;
      }
      if (nextBtn) {
        nextBtn.disabled = currentPage === totalPages;
      }
    };

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
          renderPage(currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (currentPage < totalPages) {
          renderPage(currentPage + 1);
        }
      });
    }

    pagination.classList.remove('hidden');
    renderPage(1);
  };

  document.querySelectorAll('[data-blog-list]').forEach((list) => {
    const section = list.closest('section');
    bindBlogCards(section || list);
    if (section) {
      initPagination(section);
    }
  });

  const mapTargets = document.querySelectorAll('[data-map]');
  if (mapTargets.length && window.naver && window.naver.maps) {
    mapTargets.forEach((target) => {
      const lat = parseFloat(target.dataset.lat || '');
      const lng = parseFloat(target.dataset.lng || '');
      if (Number.isNaN(lat) || Number.isNaN(lng)) {
        target.textContent = '좌표 정보가 없습니다.';
        target.classList.add('flex', 'items-center', 'justify-center', 'text-xs', 'text-slate-300');
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
