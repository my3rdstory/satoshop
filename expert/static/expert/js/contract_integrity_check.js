(function () {
  const form = document.querySelector('[data-integrity-form]');
  if (!form) return;

  const fileInput = form.querySelector('input[type="file"]');
  const fileNameTarget = form.querySelector('[data-file-name]');
  if (fileInput && fileNameTarget) {
    fileInput.addEventListener('change', () => {
      const file = fileInput.files && fileInput.files[0];
      fileNameTarget.textContent = file ? file.name : '선택된 파일이 없습니다';
    });
  }

  const select = form.querySelector('select[name="document_slug"]');
  const summary = document.querySelector('[data-integrity-summary]');
  const summaryFields = summary
    ? {
        title: summary.querySelector('[data-summary-title]'),
        status: summary.querySelector('[data-summary-status]'),
        created: summary.querySelector('[data-summary-created]'),
        hash: summary.querySelector('[data-summary-hash]'),
        link: summary.querySelector('[data-summary-link]'),
      }
    : null;
  const documents = Array.isArray(window.integrityDocuments) ? window.integrityDocuments : [];
  const documentsMap = new Map(documents.map((doc) => [doc.slug, doc]));

  function renderSummary(slug) {
    if (!summary || !summaryFields) return;
    const doc = documentsMap.get(slug);
    if (!doc) {
      summary.hidden = true;
      return;
    }
    summary.hidden = false;
    if (summaryFields.title) summaryFields.title.textContent = doc.title || '-';
    if (summaryFields.status) summaryFields.status.textContent = doc.status || '-';
    if (summaryFields.created) summaryFields.created.textContent = doc.created_at || '-';
    if (summaryFields.hash) summaryFields.hash.textContent = doc.final_pdf_hash || '(없음)';
    if (summaryFields.link) {
      if (doc.final_pdf_url) {
        let linkEl = summaryFields.link.querySelector('a');
        if (!linkEl) {
          linkEl = document.createElement('a');
          linkEl.target = '_blank';
          linkEl.rel = 'noopener';
          summaryFields.link.innerHTML = '';
          summaryFields.link.appendChild(linkEl);
        }
        linkEl.href = doc.final_pdf_url;
        linkEl.textContent = '다운로드';
      } else {
        summaryFields.link.textContent = '-';
      }
    }
  }

  if (select) {
    const initialSlug = window.integritySelectedSlug || select.value || '';
    if (initialSlug) {
      select.value = initialSlug;
      renderSummary(initialSlug);
    } else {
      summary && (summary.hidden = true);
    }
    select.addEventListener('change', (event) => {
      renderSummary(event.target.value);
    });
  }
})();
