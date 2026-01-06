const sectionList = document.querySelector('[data-section-list]');
const form = document.getElementById('minihome-form');
const payloadInput = document.getElementById('sections-payload');
const actionInput = document.getElementById('sections-action');
const initialSectionsNode = document.getElementById('minihome-initial-sections');
const initialSections = initialSectionsNode ? JSON.parse(initialSectionsNode.textContent || '[]') : [];
const initialSectionMap = new Map(
  initialSections
    .filter((section) => section && section.id)
    .map((section) => [section.id, section])
);
const backgroundRadios = document.querySelectorAll('[name="background_preset"]');
const backgroundTarget = document.querySelector('.minihome-canvas');

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
      const scope = zone.querySelector('[data-image-meta]') ? zone : zone.closest('[data-gallery-item],[data-blog-post],[data-section]') || zone.parentElement;
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
};

const removeEmptyHint = (container) => {
  const hint = container.querySelector('[data-empty-hint]');
  if (hint) {
    hint.remove();
  }
};

const addSection = (type) => {
  const sectionId = generateId();
  const replacements = {
    '__SECTION_ID__': sectionId,
    '__ITEM_ID__': generateId(),
    '__POST_ID__': generateId(),
  };
  const section = renderTemplate(`template-${type}`, replacements);
  if (!section) return;
  sectionList.appendChild(section);
  initializeSection(section);
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
      const initial = initialSectionMap.get(id);
      const items = initial?.data?.items && Array.isArray(initial.data.items)
        ? initial.data.items
        : [];
      sections.push({ id, type, data: { items } });
      return;
    }
    if (type === 'mini_blog') {
      const initial = initialSectionMap.get(id);
      const posts = initial?.data?.posts && Array.isArray(initial.data.posts)
        ? initial.data.posts
        : [];
      sections.push({ id, type, data: { posts } });
      return;
    }
    if (type === 'map') {
      sections.push({
        id,
        type,
        data: {
          title: section.querySelector('[data-field="title"]')?.value || '',
          address: section.querySelector('[data-field="address"]')?.value || '',
          lat: section.querySelector('[data-field="lat"]')?.value || '',
          lng: section.querySelector('[data-field="lng"]')?.value || '',
        },
      });
      return;
    }
    if (type === 'store') {
      const initial = initialSectionMap.get(id);
      const stores = initial?.data?.stores && Array.isArray(initial.data.stores)
        ? initial.data.stores
        : [];
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

const updateBackgroundPreview = (value) => {
  if (!backgroundTarget || !value) return;
  const classes = Array.from(backgroundTarget.classList);
  classes.forEach((className) => {
    if (className.startsWith('minihome-bg--')) {
      backgroundTarget.classList.remove(className);
    }
  });
  backgroundTarget.classList.add(`minihome-bg--${value}`);
};

backgroundRadios.forEach((radio) => {
  radio.addEventListener('change', () => updateBackgroundPreview(radio.value));
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
  if (['save', 'preview', 'publish'].includes(action)) {
    event.preventDefault();
    submitWithAction(action, action === 'preview' ? '_blank' : '_self');
    return;
  }

  if (action === 'remove-section') {
    event.preventDefault();
    const section = actionButton.closest('[data-section]');
    if (section) section.remove();
    return;
  }


});
