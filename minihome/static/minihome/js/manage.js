const sectionList = document.querySelector('[data-section-list]');
const form = document.getElementById('minihome-form');
const payloadInput = document.getElementById('sections-payload');
const actionInput = document.getElementById('sections-action');
const backgroundChoiceInputs = document.querySelectorAll('[data-bg-choice]');
const backgroundTarget = document.querySelector('.minihome-canvas');
const backgroundValueInput = document.getElementById('background-preset');
const backgroundModal = document.querySelector('[data-background-modal]');
const backgroundPreview = document.querySelector('[data-current-bg]');
const backgroundLabelTargets = document.querySelectorAll('[data-current-bg-label]');
const backgroundModalPreview = document.querySelector('[data-modal-current-bg]');
const blogPreviewPlaceholder = '내용을 입력해주세요.';
const publishNotice = document.querySelector('[data-publish-notice]');
const dataPanelContainer = document.querySelector('[data-section-data-panels]');
const dataEmptyHint = document.querySelector('[data-data-empty]');
const dataTitle = document.querySelector('[data-data-title]');
const dataSubtitle = document.querySelector('[data-data-subtitle]');
const sectionTypeLabels = {
  gallery: '갤러리',
  mini_blog: '미니 블로그',
  store: '매장',
};
let activeDataPanelId = null;

const generateId = () => {
  if (window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
};

const renderTemplate = (templateId, replacements) => {
  const template = document.getElementById(templateId);
  if (!template) return null;
  let html = template.innerHTML;
  Object.keys(replacements).forEach((key) => {
    html = html.replaceAll(key, replacements[key]);
  });
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html.trim();
  return wrapper.firstElementChild;
};

const getDataPanel = (sectionId) => {
  if (!dataPanelContainer || !sectionId) return null;
  return dataPanelContainer.querySelector(
    `[data-section-panel][data-section-id="${sectionId}"]`
  );
};

const updateDataHeader = (sectionType) => {
  const label = sectionTypeLabels[sectionType] || '데이터';
  if (dataTitle) {
    dataTitle.textContent = `${label} 데이터`;
  }
  if (dataSubtitle) {
    dataSubtitle.textContent = `${label} 섹션을 편집중입니다.`;
  }
};

const resetDataHeader = () => {
  if (dataTitle) {
    dataTitle.textContent = '데이터 보기';
  }
  if (dataSubtitle) {
    dataSubtitle.textContent = '섹션을 선택하세요.';
  }
};

const resetDataPanel = () => {
  dataPanelContainer?.querySelectorAll('[data-section-panel]').forEach((panel) => {
    panel.classList.add('hidden');
  });
  activeDataPanelId = null;
  if (dataEmptyHint) {
    dataEmptyHint.classList.remove('hidden');
  }
  resetDataHeader();
};

const showDataPanel = (sectionId, sectionType) => {
  if (!dataPanelContainer) return;
  const panel = getDataPanel(sectionId);
  dataPanelContainer.querySelectorAll('[data-section-panel]').forEach((item) => {
    item.classList.add('hidden');
  });
  if (!panel) {
    resetDataPanel();
    return;
  }
  panel.classList.remove('hidden');
  activeDataPanelId = sectionId;
  if (dataEmptyHint) {
    dataEmptyHint.classList.add('hidden');
  }
  updateDataHeader(sectionType || panel.dataset.sectionType);
};

const clearImageMeta = (scope) => {
  scope.querySelectorAll('[data-image-meta]').forEach((input) => {
    input.value = '';
  });
};

const readImageMeta = (scope) => {
  const path = scope.querySelector('[data-image-meta="path"]')?.value?.trim();
  if (!path) return null;
  return {
    path,
    url: scope.querySelector('[data-image-meta="url"]')?.value?.trim() || '',
    width: scope.querySelector('[data-image-meta="width"]')?.value?.trim() || '',
    height: scope.querySelector('[data-image-meta="height"]')?.value?.trim() || '',
  };
};

const setupDropzone = (zone) => {
  if (zone.dataset.bound) return;
  zone.dataset.bound = 'true';
  const input = zone.querySelector('[data-image-input]');
  const preview = zone.querySelector('[data-image-preview]');
  const trigger = zone.querySelector('[data-action="trigger-file"]');
  const clear = zone.querySelector('[data-action="clear-image"]');

  const updatePreview = (file) => {
    if (!file || !preview) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      preview.src = event.target.result;
      preview.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  };

  if (input) {
    input.addEventListener('change', () => {
      updatePreview(input.files[0]);
    });
  }

  if (trigger && input) {
    trigger.addEventListener('click', (event) => {
      event.preventDefault();
      input.click();
    });
  }

  if (clear) {
    clear.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (input) {
        input.value = '';
      }
      if (preview) {
        preview.src = '';
        preview.classList.add('hidden');
      }
      const scope = zone.querySelector('[data-image-meta]')
        ? zone
        : zone.closest('[data-blog-image],[data-gallery-item],[data-store-item],[data-section]')
          || zone.parentElement;
      if (scope) {
        clearImageMeta(scope);
      }
    });
  }

  zone.addEventListener('dragover', (event) => {
    event.preventDefault();
    zone.classList.add('dragover');
  });

  zone.addEventListener('dragleave', () => {
    zone.classList.remove('dragover');
  });

  zone.addEventListener('drop', (event) => {
    event.preventDefault();
    zone.classList.remove('dragover');
    if (!input || !event.dataTransfer.files.length) return;
    const file = event.dataTransfer.files[0];
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    input.files = dataTransfer.files;
    updatePreview(file);
  });
};

const initializeSection = (section) => {
  section.querySelectorAll('[data-dropzone]').forEach(setupDropzone);
  section.querySelectorAll('[data-blog-post]').forEach(bindBlogPreview);
};

const initializePanel = (panel) => {
  panel.querySelectorAll('[data-dropzone]').forEach(setupDropzone);
  panel.querySelectorAll('[data-blog-post]').forEach(bindBlogPreview);
  const galleryContainer = panel.querySelector('[data-gallery-items]');
  if (galleryContainer) {
    refreshGalleryLayout(galleryContainer);
    toggleEmptyHint(galleryContainer, '[data-gallery-item]');
  }
  const blogContainer = panel.querySelector('[data-blog-posts]');
  if (blogContainer) {
    toggleEmptyHint(blogContainer, '[data-blog-post]');
  }
  const storeContainer = panel.querySelector('[data-store-items]');
  if (storeContainer) {
    toggleEmptyHint(storeContainer, '[data-store-item]');
  }
};

const toggleEmptyHint = (container, itemSelector) => {
  if (!container) return;
  const hint = container.querySelector('[data-empty-hint]');
  if (!hint) return;
  const hasItems = container.querySelector(itemSelector);
  hint.classList.toggle('hidden', Boolean(hasItems));
};

const bindBlogPreview = (scope) => {
  const textarea = scope.querySelector('[data-field="text"]');
  const preview = scope.querySelector('[data-preview-text]');
  if (!textarea || !preview) return;
  const update = () => {
    preview.textContent = textarea.value.trim() || blogPreviewPlaceholder;
  };
  textarea.addEventListener('input', update);
  update();
};

const addSection = (type) => {
  const sectionId = generateId();
  const replacements = {
    '__SECTION_ID__': sectionId,
    '__ITEM_ID__': generateId(),
    '__POST_ID__': generateId(),
    '__STORE_ID__': generateId(),
  };
  const section = renderTemplate(`template-${type}`, replacements);
  if (!section) return;
  sectionList.appendChild(section);
  initializeSection(section);
  if (dataPanelContainer && ['gallery', 'mini_blog', 'store'].includes(type)) {
    const panel = renderTemplate(`template-${type}-panel`, replacements);
    if (panel) {
      dataPanelContainer.appendChild(panel);
      initializePanel(panel);
    }
  }
  toggleEmptyHint(section.querySelector('[data-gallery-items]'), '[data-gallery-item]');
  toggleEmptyHint(section.querySelector('[data-blog-posts]'), '[data-blog-post]');
  toggleEmptyHint(section.querySelector('[data-store-items]'), '[data-store-item]');
};

const refreshGalleryLayout = (container) => {
  if (!container) return;
  const rows = Array.from(container.querySelectorAll('[data-gallery-row]'));
  rows.forEach((row, index) => {
    row.classList.remove('sm:flex-row', 'sm:flex-row-reverse');
    row.classList.add(index % 2 === 0 ? 'sm:flex-row' : 'sm:flex-row-reverse');
  });
};

const addGalleryItem = (panel) => {
  const container = panel.querySelector('[data-gallery-items]');
  if (!container) return;
  const count = container.querySelectorAll('[data-gallery-item]').length;
  const replacements = {
    '__SECTION_ID__': panel.dataset.sectionId,
    '__ITEM_ID__': generateId(),
    '__FLEX_CLASS__': count % 2 === 0 ? 'sm:flex-row' : 'sm:flex-row-reverse',
  };
  const item = renderTemplate('template-gallery-item', replacements);
  if (!item) return;
  const itemId = item.dataset.itemId || replacements.__ITEM_ID__;
  item.querySelectorAll('[data-image-input]').forEach((input) => {
    input.name = `gallery__${panel.dataset.sectionId}__${itemId}`;
  });
  container.appendChild(item);
  initializeSection(item);
  refreshGalleryLayout(container);
  toggleEmptyHint(container, '[data-gallery-item]');
};

const addBlogPost = (panel) => {
  const container = panel.querySelector('[data-blog-posts]');
  if (!container) return;
  const replacements = {
    '__SECTION_ID__': panel.dataset.sectionId,
    '__POST_ID__': generateId(),
  };
  const post = renderTemplate('template-blog-post', replacements);
  if (!post) return;
  const postId = post.dataset.postId || replacements.__POST_ID__;
  post.querySelectorAll('[data-image-input]').forEach((input) => {
    const slot = input.closest('[data-blog-image]')?.dataset.imageSlot;
    if (slot !== undefined) {
      input.name = `blog__${panel.dataset.sectionId}__${postId}__${slot}`;
    }
  });
  container.appendChild(post);
  initializeSection(post);
  bindBlogPreview(post);
  toggleEmptyHint(container, '[data-blog-post]');
};

const addStoreItem = (panel) => {
  const container = panel.querySelector('[data-store-items]');
  if (!container) return;
  const replacements = {
    '__SECTION_ID__': panel.dataset.sectionId,
    '__STORE_ID__': generateId(),
  };
  const store = renderTemplate('template-store-item', replacements);
  if (!store) return;
  const storeId = store.dataset.storeId || replacements.__STORE_ID__;
  store.querySelectorAll('[data-image-input]').forEach((input) => {
    input.name = `store__${panel.dataset.sectionId}__${storeId}`;
  });
  container.appendChild(store);
  initializeSection(store);
  toggleEmptyHint(container, '[data-store-item]');
};

const collectSections = () => {
  const sections = [];
  sectionList.querySelectorAll('[data-section]').forEach((section) => {
    const type = section.dataset.sectionType;
    const id = section.dataset.sectionId;
    if (!type || !id) return;
    if (type === 'brand_image') {
      sections.push({
        id,
        type,
        data: {
          image: readImageMeta(section),
        },
      });
      return;
    }
    if (type === 'title') {
      sections.push({
        id,
        type,
        data: {
          title: section.querySelector('[data-field="title"]')?.value || '',
          description: section.querySelector('[data-field="description"]')?.value || '',
        },
      });
      return;
    }
    if (type === 'gallery') {
      const items = [];
      const scope = getDataPanel(id) || section;
      scope.querySelectorAll('[data-gallery-item]').forEach((item) => {
        items.push({
          id: item.dataset.itemId || generateId(),
          description: item.querySelector('[data-field="description"]')?.value || '',
          image: readImageMeta(item),
        });
      });
      sections.push({ id, type, data: { items } });
      return;
    }
    if (type === 'mini_blog') {
      const posts = [];
      const scope = getDataPanel(id) || section;
      scope.querySelectorAll('[data-blog-post]').forEach((post) => {
        const images = [];
        const slots = Array.from(post.querySelectorAll('[data-blog-image]'));
        slots.sort((a, b) => Number(a.dataset.imageSlot) - Number(b.dataset.imageSlot));
        slots.forEach((slot) => {
          images.push(readImageMeta(slot));
        });
        while (images.length < 4) {
          images.push(null);
        }
        posts.push({
          id: post.dataset.postId || generateId(),
          text: post.querySelector('[data-field="text"]')?.value || '',
          images,
        });
      });
      sections.push({ id, type, data: { posts } });
      return;
    }
    if (type === 'store') {
      const stores = [];
      const scope = getDataPanel(id) || section;
      scope.querySelectorAll('[data-store-item]').forEach((store) => {
        stores.push({
          id: store.dataset.storeId || generateId(),
          name: store.querySelector('[data-field="name"]')?.value || '',
          map_url: store.querySelector('[data-field="map_url"]')?.value || '',
          cover_image: readImageMeta(store),
        });
      });
      sections.push({ id, type, data: { stores } });
      return;
    }
    if (type === 'cta') {
      sections.push({
        id,
        type,
        data: {
          profile_image: readImageMeta(section),
          description: section.querySelector('[data-field="description"]')?.value || '',
          email: section.querySelector('[data-field="email"]')?.value || '',
          donation: section.querySelector('[data-field="donation"]')?.value || '',
        },
      });
    }
  });
  return sections;
};

const submitWithAction = (action, target = '_self') => {
  actionInput.value = action;
  form.target = target;
  const payload = collectSections();
  payloadInput.value = JSON.stringify(payload);
  if (typeof form.requestSubmit === 'function') {
    form.requestSubmit();
  } else {
    form.submit();
  }
  form.target = '_self';
};

if (form) {
  form.addEventListener('submit', () => {
    const payload = collectSections();
    payloadInput.value = JSON.stringify(payload);
  });
}

sectionList?.querySelectorAll('[data-section]').forEach(initializeSection);
dataPanelContainer?.querySelectorAll('[data-section-panel]').forEach(initializePanel);
dataPanelContainer?.querySelectorAll('[data-gallery-items]').forEach((container) => {
  refreshGalleryLayout(container);
  toggleEmptyHint(container, '[data-gallery-item]');
});
dataPanelContainer?.querySelectorAll('[data-blog-posts]').forEach((container) => {
  toggleEmptyHint(container, '[data-blog-post]');
});
dataPanelContainer?.querySelectorAll('[data-store-items]').forEach((container) => {
  toggleEmptyHint(container, '[data-store-item]');
});
resetDataPanel();

const updateBackgroundPreview = (element, value) => {
  if (!element || !value) return;
  const classes = Array.from(element.classList);
  classes.forEach((className) => {
    if (className.startsWith('minihome-bg--')) {
      element.classList.remove(className);
    }
  });
  element.classList.add(`minihome-bg--${value}`);
};

const setBackgroundPreset = (value, label) => {
  if (!value) return;
  if (backgroundValueInput) {
    backgroundValueInput.value = value;
  }
  updateBackgroundPreview(backgroundTarget, value);
  updateBackgroundPreview(backgroundPreview, value);
  updateBackgroundPreview(backgroundModalPreview, value);
  if (label) {
    backgroundLabelTargets.forEach((target) => {
      target.textContent = label;
    });
  }
};

const openBackgroundModal = () => {
  if (!backgroundModal) return;
  backgroundModal.classList.remove('hidden');
  if (backgroundValueInput) {
    backgroundChoiceInputs.forEach((input) => {
      input.checked = input.value === backgroundValueInput.value;
    });
  }
};

const closeBackgroundModal = () => {
  if (!backgroundModal) return;
  backgroundModal.classList.add('hidden');
};

backgroundChoiceInputs.forEach((input) => {
  input.addEventListener('change', () => {
    setBackgroundPreset(input.value, input.dataset.label || '');
    closeBackgroundModal();
  });
});

backgroundModal?.addEventListener('click', (event) => {
  if (event.target === backgroundModal) {
    closeBackgroundModal();
  }
});

document.querySelectorAll('[data-modal-close]').forEach((button) => {
  button.addEventListener('click', (event) => {
    event.preventDefault();
    closeBackgroundModal();
  });
});

document.addEventListener('click', (event) => {
  const addButton = event.target.closest('[data-add-section]');
  if (addButton) {
    addSection(addButton.dataset.sectionType);
    return;
  }

  const actionButton = event.target.closest('[data-action]');
  if (!actionButton) return;

  const action = actionButton.dataset.action;
  if (action === 'open-background-modal') {
    event.preventDefault();
    openBackgroundModal();
    return;
  }
  if (action === 'open-data-panel') {
    event.preventDefault();
    const sectionId = actionButton.dataset.sectionId
      || actionButton.closest('[data-section]')?.dataset.sectionId;
    const sectionType = actionButton.dataset.sectionType
      || actionButton.closest('[data-section]')?.dataset.sectionType;
    if (sectionId) {
      showDataPanel(sectionId, sectionType);
    }
    return;
  }
  if (action === 'close-data-panel') {
    event.preventDefault();
    resetDataPanel();
    return;
  }
  if (['save', 'preview', 'publish'].includes(action)) {
    event.preventDefault();
    submitWithAction(action, action === 'preview' ? '_blank' : '_self');
    return;
  }

  if (action === 'remove-section') {
    event.preventDefault();
    const section = actionButton.closest('[data-section]');
    if (section) {
      const sectionId = section.dataset.sectionId;
      section.remove();
      const panel = getDataPanel(sectionId);
      if (panel) {
        panel.remove();
      }
      if (activeDataPanelId === sectionId) {
        resetDataPanel();
      }
    }
    return;
  }

  if (action === 'add-gallery-item') {
    event.preventDefault();
    const panel = actionButton.closest('[data-section-panel]');
    if (panel) addGalleryItem(panel);
    return;
  }

  if (action === 'add-blog-post') {
    event.preventDefault();
    const panel = actionButton.closest('[data-section-panel]');
    if (panel) addBlogPost(panel);
    return;
  }

  if (action === 'add-store-item') {
    event.preventDefault();
    const panel = actionButton.closest('[data-section-panel]');
    if (panel) addStoreItem(panel);
    return;
  }

  if (action === 'remove-gallery-item') {
    event.preventDefault();
    const item = actionButton.closest('[data-gallery-item]');
    const container = item?.closest('[data-gallery-items]');
    if (item) item.remove();
    refreshGalleryLayout(container);
    toggleEmptyHint(container, '[data-gallery-item]');
    return;
  }

  if (action === 'remove-blog-post') {
    event.preventDefault();
    const post = actionButton.closest('[data-blog-post]');
    const container = post?.closest('[data-blog-posts]');
    if (post) post.remove();
    toggleEmptyHint(container, '[data-blog-post]');
    return;
  }

  if (action === 'remove-store-item') {
    event.preventDefault();
    const store = actionButton.closest('[data-store-item]');
    const container = store?.closest('[data-store-items]');
    if (store) store.remove();
    toggleEmptyHint(container, '[data-store-item]');
    return;
  }


});

const showPublishNotice = () => {
  if (!publishNotice) return;
  const params = new URLSearchParams(window.location.search);
  if (params.get('published') !== '1') return;
  publishNotice.classList.remove('hidden');
  window.setTimeout(() => {
    publishNotice.classList.add('hidden');
  }, 5000);
  params.delete('published');
  const nextQuery = params.toString();
  const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}${window.location.hash}`;
  window.history.replaceState({}, '', nextUrl);
};

showPublishNotice();
