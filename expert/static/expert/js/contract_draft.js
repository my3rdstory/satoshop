const previewMap = {
    title: document.getElementById('preview-title'),
    role: document.getElementById('preview-role'),
    period: document.getElementById('preview-period'),
    amount: document.getElementById('preview-amount'),
    payment: document.getElementById('preview-payment'),
    email: document.getElementById('preview-email'),
    performerLightning: document.getElementById('preview-performer-lightning'),
    oneTimeDate: document.getElementById('preview-one-time-date'),
    oneTimeCondition: document.getElementById('preview-one-time-condition'),
};

let amountInput;
let paymentInputs = [];
let submitButton;
let milestoneSection;
let milestoneList;
let addMilestoneButton;
let milestoneRemaining;
let milestoneError;
let milestonesInitialized = false;
let milestoneOverflow = false;
let milestoneRowCount = 0;
let agreementCheckboxes = [];
let oneTimeSection;
let oneTimeDueInput;
let oneTimeConditionInput;
let previewOneTimePanel;
let modalOneTimePanel;
let modalOneTimeDate;
let modalOneTimeCondition;
let performerLightningInput;
let previewModalButton;
let previewModal;
let previewModalCloseButtons = [];
let modalTemplateMarkdown;
let templatePayload = null;
let workLogEditor = null;
let previewMilestonePanel;
let previewMilestoneList;
let modalMilestonePanel;
let modalMilestoneList;
let previewWorklogNode;
let modalWorklogNode;
let previewAttachmentPanel;
let previewAttachmentList;
let modalAttachmentPanel;
let modalAttachmentList;
let modalPerformerLightning;
let attachmentUploader;
let attachmentDropzone;
let attachmentInput;
let attachmentTrigger;
let attachmentStatusNode;
let attachmentListNode;
let attachmentManifestInput;
let attachmentUploadUrl = '';
let attachmentEntries = [];
let roleContactFieldset;
let roleLightningCard;
let roleEmailHelpTexts = [];
const WORKLOG_MAX_LENGTH = 10000;
const worklogLengthFormatter = new Intl.NumberFormat('ko-KR');
let worklogCounterNode = null;
let worklogNoteNode = null;
let suppressWorklogEditorChange = false;

const attachmentConfig = {
    maxItems: 3,
    maxSize: 5 * 1024 * 1024,
};

function formatSats(value) {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return '-';
    }
    return new Intl.NumberFormat('ko-KR').format(value);
}

function formatRole(value) {
    if (value === 'client') return '의뢰자';
    if (value === 'performer') return '수행자';
    return '-';
}

function clampWorklogValue(value) {
    if (typeof value !== 'string') {
        return '';
    }
    if (value.length <= WORKLOG_MAX_LENGTH) {
        return value;
    }
    return value.slice(0, WORKLOG_MAX_LENGTH);
}

function updateWorklogCounterDisplay(length, truncated = false) {
    if (!worklogCounterNode) {
        worklogCounterNode = document.querySelector('[data-worklog-remaining]');
    }
    if (!worklogCounterNode) {
        return;
    }
    if (!worklogNoteNode) {
        worklogNoteNode = document.querySelector('[data-worklog-note]');
    }
    const remaining = Math.max(WORKLOG_MAX_LENGTH - length, 0);
    worklogCounterNode.textContent = worklogLengthFormatter.format(remaining);
    const wrapper = worklogCounterNode.closest('[data-worklog-counter-wrapper]');
    if (wrapper) {
        wrapper.dataset.remaining = String(remaining);
        wrapper.dataset.truncated = truncated ? 'true' : 'false';
    }
    if (worklogNoteNode) {
        if (truncated) {
            worklogNoteNode.hidden = false;
        } else {
            worklogNoteNode.hidden = true;
        }
    }
}

function formatPayment(value) {
    if (value === 'one_time') return '일괄 지급';
    if (value === 'milestone') return '분할 지급';
    return '-';
}

function formatBytes(bytes) {
    if (!Number.isFinite(bytes)) {
        return '-';
    }
    if (bytes === 0) {
        return '0 B';
    }
    const units = ['B', 'KB', 'MB', 'GB'];
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    const value = bytes / 1024 ** index;
    return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDateLabel(value) {
    if (!value) {
        return '미정';
    }
    return value;
}

function collectMilestoneDetails() {
    if (!milestoneList) {
        return [];
    }
    const items = Array.from(milestoneList.querySelectorAll('.milestone-item'));
    return items
        .map((item) => {
            const amountInput = item.querySelector('.milestone-amount-input');
            const dateInput = item.querySelector('.milestone-date-input');
            const conditionInput = item.querySelector('.milestone-condition-input');
            const amountValue = amountInput ? parseInt(amountInput.value, 10) : Number.NaN;
            return {
                amount: Number.isFinite(amountValue) && amountValue > 0 ? amountValue : 0,
                dueDate: dateInput ? dateInput.value : '',
                condition: conditionInput ? conditionInput.value.trim() : '',
            };
        })
        .filter((detail) => detail.amount > 0 || detail.dueDate || detail.condition);
}

function buildMilestonePreviewItem(detail, index) {
    const li = document.createElement('li');
    li.className = 'milestone-preview-item';
    const conditionText = detail.condition || '지급 조건 미입력';
    li.innerHTML = `
        <div class="milestone-preview-row">
            <span class="milestone-preview-order">분할 ${index + 1}</span>
            <div class="milestone-preview-meta">
                <span>금액: ${formatSats(detail.amount || 0)} sats</span>
                <span>지급일: ${formatDateLabel(detail.dueDate)}</span>
            </div>
        </div>
        <p class="milestone-preview-condition">조건: ${conditionText}</p>
    `;
    return li;
}

function renderMilestoneLists(details) {
    const paymentValue = getCheckedValue(paymentInputs);
    const resolvedDetails = Array.isArray(details) ? details : [];
    const hasDetails = paymentValue === 'milestone' && resolvedDetails.length > 0;

    if (previewMilestonePanel) {
        previewMilestonePanel.hidden = !hasDetails;
    }
    if (modalMilestonePanel) {
        modalMilestonePanel.hidden = !hasDetails;
    }

    [previewMilestoneList, modalMilestoneList].forEach((listNode) => {
        if (listNode) {
            listNode.innerHTML = '';
        }
    });

    if (!hasDetails) {
        return;
    }

    resolvedDetails.forEach((detail, index) => {
        if (previewMilestoneList) {
            previewMilestoneList.appendChild(buildMilestonePreviewItem(detail, index));
        }
        if (modalMilestoneList) {
            modalMilestoneList.appendChild(buildMilestonePreviewItem(detail, index));
        }
    });
}

function updateOneTimePreview() {
    const paymentValue = getCheckedValue(paymentInputs);
    const show = paymentValue === 'one_time';
    if (previewOneTimePanel) {
        previewOneTimePanel.hidden = !show;
    }
    if (modalOneTimePanel) {
        modalOneTimePanel.hidden = !show;
    }
    const dueValue = oneTimeDueInput && oneTimeDueInput.value ? oneTimeDueInput.value : '';
    const conditionValue = oneTimeConditionInput && oneTimeConditionInput.value ? oneTimeConditionInput.value.trim() : '';
    const dueText = dueValue || '미정';
    const conditionText = conditionValue || '지급 조건 미입력';
    if (previewMap.oneTimeDate) {
        previewMap.oneTimeDate.textContent = dueText;
    }
    if (previewMap.oneTimeCondition) {
        previewMap.oneTimeCondition.textContent = conditionText;
    }
    if (modalOneTimeDate) {
        modalOneTimeDate.textContent = dueText;
    }
    if (modalOneTimeCondition) {
        modalOneTimeCondition.textContent = conditionText;
    }
}

function updateLightningPreview() {
    const performerValue = performerLightningInput && performerLightningInput.value ? performerLightningInput.value.trim() : '';
    if (previewMap.performerLightning) {
        previewMap.performerLightning.textContent = performerValue || '-';
    }
    if (modalPerformerLightning) {
        modalPerformerLightning.textContent = performerValue || '-';
    }
}

function toggleRoleContactFields(roleValue) {
    if (!roleContactFieldset) {
        return;
    }
    const hasRole = Boolean(roleValue);
    const isPerformer = roleValue === 'performer';
    roleContactFieldset.hidden = !hasRole;
    if (roleLightningCard) {
        roleLightningCard.hidden = !isPerformer;
        const lightningInputs = Array.from(roleLightningCard.querySelectorAll('input, select, textarea'));
        lightningInputs.forEach((input) => {
            input.disabled = !isPerformer;
        });
    }
    if (performerLightningInput) {
        performerLightningInput.required = isPerformer;
    }
    roleEmailHelpTexts.forEach((node) => {
        node.hidden = node.getAttribute('data-role-email-help') !== roleValue;
    });
}

function renderAttachmentPreviewLists(entries = attachmentEntries) {
    const listData = Array.isArray(entries) ? entries : [];
    const hasItems = listData.length > 0;
    if (previewAttachmentPanel) {
        previewAttachmentPanel.hidden = !hasItems;
    }
    if (modalAttachmentPanel) {
        modalAttachmentPanel.hidden = !hasItems;
    }
    [previewAttachmentList, modalAttachmentList].forEach((listNode) => {
        if (listNode) {
            listNode.innerHTML = '';
        }
    });
    if (!hasItems) {
        return;
    }
    listData.forEach((item, index) => {
        const name = item && item.name ? item.name : `첨부 ${index + 1}`;
        const sizeLabel = item && Number.isFinite(item.size) ? formatBytes(item.size) : '—';
        const listItem = document.createElement('li');
        listItem.className = 'attachment-preview-item';
        listItem.innerHTML = `
            <span class="attachment-preview-name">${name}</span>
            <span class="attachment-preview-size">${sizeLabel}</span>
        `;
        if (previewAttachmentList) {
            previewAttachmentList.appendChild(listItem.cloneNode(true));
        }
        if (modalAttachmentList) {
            modalAttachmentList.appendChild(listItem.cloneNode(true));
        }
    });
}

function updateWorkLogPreview(markdownText) {
    const content = (markdownText || '').trim();
    const targets = [
        { node: previewWorklogNode, placeholder: '작성된 메모가 없습니다.' },
        { node: modalWorklogNode, placeholder: '작성된 메모가 없습니다.' },
    ];

    targets.forEach(({ node, placeholder }) => {
        if (!node) {
            return;
        }
        if (!content) {
            node.dataset.empty = 'true';
            node.innerHTML = `<p class="preview-placeholder">${placeholder}</p>`;
            return;
        }
        node.dataset.empty = 'false';
        node.textContent = content;
        if (window.MarkdownRenderer && typeof window.MarkdownRenderer.render === 'function') {
            window.MarkdownRenderer.render(node);
        } else {
            node.innerHTML = content.replace(/\n/g, '<br>');
        }
    });
}

function getCsrfToken() {
    const tokenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return tokenInput ? tokenInput.value : '';
}

function isPdfFile(file) {
    if (!file) {
        return false;
    }
    const mime = (file.type || '').toLowerCase();
    if (mime === 'application/pdf' || mime === 'application/x-pdf') {
        return true;
    }
    return file.name.toLowerCase().endsWith('.pdf');
}

function getCheckedValue(inputs) {
    if (!inputs || !inputs.length) {
        return null;
    }
    const found = inputs.find((input) => input.checked);
    return found ? found.value : null;
}

function getMilestoneAmountInputs() {
    if (!milestoneList) {
        return [];
    }
    return Array.from(milestoneList.querySelectorAll('.milestone-amount-input'));
}

function getMilestoneRowCount() {
    if (!milestoneList) {
        return 0;
    }
    return milestoneList.querySelectorAll('.milestone-item').length;
}

function allAgreementsAccepted() {
    if (!agreementCheckboxes.length) {
        return true;
    }
    return agreementCheckboxes.every((checkbox) => checkbox.checked);
}

function setSubmitButtonState(forceDisable = false) {
    if (!submitButton) {
        return;
    }
    const agreementsReady = allAgreementsAccepted();
    submitButton.disabled = forceDisable || !agreementsReady;
}

function updateMilestoneLabels() {
    if (!milestoneList) {
        return;
    }
    const labels = milestoneList.querySelectorAll('.milestone-item .milestone-order');
    labels.forEach((node, index) => {
        node.textContent = `분할 ${index + 1}`;
    });
}

function updateMilestonePreview(totalAmount, remaining, details = null) {
    if (!previewMap.payment || !paymentInputs.length) {
        return;
    }
    const paymentValue = getCheckedValue(paymentInputs);
    if (paymentValue !== 'milestone') {
        previewMap.payment.textContent = formatPayment(paymentValue);
        renderMilestoneLists([]);
        return;
    }
    const resolvedDetails = Array.isArray(details) ? details : collectMilestoneDetails();
    const milestoneCount = resolvedDetails.length || getMilestoneRowCount();
    if (!Number.isFinite(totalAmount) || totalAmount <= 0) {
        previewMap.payment.textContent = '분할 지급 (총액 입력 대기)';
        renderMilestoneLists(resolvedDetails);
        return;
    }
    const remainingText = formatSats(Math.max(remaining, 0));
    previewMap.payment.textContent = `분할 지급 (${milestoneCount}회, 남은 ${remainingText} sats)`;
    renderMilestoneLists(resolvedDetails);
}

function updateMilestoneTotals() {
    if (!milestoneSection) {
        return;
    }

    const inputs = getMilestoneAmountInputs();
    const totalAmount = parseInt(amountInput ? amountInput.value : '', 10);
    const hasTotal = Number.isFinite(totalAmount) && totalAmount > 0;
    const allMilestoneInputs = milestoneList ? Array.from(milestoneList.querySelectorAll('.milestone-input')) : [];

    if (!hasTotal) {
        allMilestoneInputs.forEach((input) => {
            input.disabled = true;
        });
        if (addMilestoneButton) {
            addMilestoneButton.disabled = true;
        }
        if (milestoneRemaining) {
            milestoneRemaining.textContent = '총 계약 금액을 입력하면 분할 금액을 구성할 수 있어요.';
        }
        if (milestoneError) {
            milestoneError.hidden = true;
        }
        milestoneOverflow = false;
        setSubmitButtonState();
        updateMilestonePreview(Number.NaN, Number.NaN, []);
        return;
    }

    allMilestoneInputs.forEach((input) => {
        input.disabled = false;
    });
    if (addMilestoneButton) {
        addMilestoneButton.disabled = false;
    }

    let allocated = 0;
    inputs.forEach((input) => {
        let value = parseInt(input.value, 10);
        if (!Number.isFinite(value) || value < 0) {
            value = 0;
        }
        const allowance = Math.max(totalAmount - allocated, 0);
        if (value > allowance) {
            value = allowance;
            input.value = value ? value : '';
        }
        allocated += value;
    });

    const remaining = Math.max(totalAmount - allocated, 0);

    if (milestoneRemaining) {
        milestoneRemaining.textContent = `남은 금액: ${formatSats(remaining)} sats`;
    }
    if (milestoneError) {
        if (milestoneOverflow) {
            milestoneError.hidden = false;
        } else {
            milestoneError.hidden = true;
        }
    }
    milestoneOverflow = false;
    setSubmitButtonState();

    if (addMilestoneButton) {
        addMilestoneButton.disabled = remaining === 0;
    }

    const details = collectMilestoneDetails();
    updateMilestonePreview(totalAmount, remaining, details);
}

function onMilestoneInput(event) {
    if (!amountInput) {
        return;
    }
    const totalAmount = parseInt(amountInput.value, 10);
    const hasTotal = Number.isFinite(totalAmount) && totalAmount > 0;
    if (!hasTotal) {
        event.target.value = '';
        updateMilestoneTotals();
        return;
    }
    const inputs = getMilestoneAmountInputs();
    const otherSum = inputs.reduce((acc, input) => {
        if (input === event.target) {
            return acc;
        }
        const value = parseInt(input.value, 10);
        return acc + (Number.isFinite(value) ? value : 0);
    }, 0);
    const allowance = Math.max(totalAmount - otherSum, 0);
    let currentValue = parseInt(event.target.value, 10);
    if (!Number.isFinite(currentValue) || currentValue < 0) {
        currentValue = 0;
    }
    milestoneOverflow = false;
    if (currentValue > allowance) {
        currentValue = allowance;
        event.target.value = currentValue ? currentValue : '';
        milestoneOverflow = true;
        if (milestoneError) {
            milestoneError.textContent = '총 계약 금액을 초과할 수 없습니다. 입력값을 남은 금액으로 조정했습니다.';
        }
    }
    updateMilestoneTotals();
}

function onMilestoneDetailChange() {
    renderMilestoneLists(collectMilestoneDetails());
}

function addMilestoneRow(defaults = {}) {
    if (!milestoneList) {
        return;
    }
    milestoneRowCount += 1;
    const rowId = milestoneRowCount;
    const normalizedDefaults = defaults || {};
    const item = document.createElement('div');
    item.className = 'milestone-item';

    const label = document.createElement('span');
    label.className = 'milestone-order';
    item.appendChild(label);

    const fields = document.createElement('div');
    fields.className = 'milestone-fields';

    const amountField = document.createElement('div');
    amountField.className = 'milestone-field';
    const amountLabel = document.createElement('label');
    const amountId = `milestone-amount-${rowId}`;
    amountLabel.className = 'milestone-field-label';
    amountLabel.setAttribute('for', amountId);
    amountLabel.textContent = '금액 (sats)';
    amountField.appendChild(amountLabel);
    const amountInput = document.createElement('input');
    amountInput.type = 'number';
    amountInput.inputMode = 'numeric';
    amountInput.min = '0';
    amountInput.className = 'input milestone-input milestone-amount-input';
    amountInput.name = 'milestone_amounts[]';
    amountInput.id = amountId;
    amountInput.placeholder = '예: 50000';
    if (normalizedDefaults.amount || normalizedDefaults.amount_sats) {
        amountInput.value = normalizedDefaults.amount || normalizedDefaults.amount_sats;
    }
    amountInput.addEventListener('input', onMilestoneInput);
    amountField.appendChild(amountInput);
    fields.appendChild(amountField);

    const dateField = document.createElement('div');
    dateField.className = 'milestone-field';
    const dateLabel = document.createElement('label');
    const dateId = `milestone-date-${rowId}`;
    dateLabel.className = 'milestone-field-label';
    dateLabel.setAttribute('for', dateId);
    dateLabel.textContent = '지급 예정일';
    dateField.appendChild(dateLabel);
    const dateInput = document.createElement('input');
    dateInput.type = 'date';
    dateInput.className = 'input milestone-input milestone-date-input';
    dateInput.name = 'milestone_due_dates[]';
    dateInput.id = dateId;
    if (normalizedDefaults.due_date) {
        dateInput.value = normalizedDefaults.due_date;
    }
    dateInput.addEventListener('change', onMilestoneDetailChange);
    dateInput.addEventListener('input', onMilestoneDetailChange);
    dateField.appendChild(dateInput);
    fields.appendChild(dateField);

    const conditionField = document.createElement('div');
    conditionField.className = 'milestone-field milestone-field--condition';
    const conditionLabel = document.createElement('label');
    const conditionId = `milestone-condition-${rowId}`;
    conditionLabel.className = 'milestone-field-label';
    conditionLabel.setAttribute('for', conditionId);
    conditionLabel.textContent = '지급 조건';
    conditionField.appendChild(conditionLabel);
    const conditionInput = document.createElement('input');
    conditionInput.type = 'text';
    conditionInput.className = 'input milestone-input milestone-condition-input';
    conditionInput.name = 'milestone_conditions[]';
    conditionInput.id = conditionId;
    conditionInput.placeholder = '예: 디자인 시안 승인 후 3일 이내';
    if (normalizedDefaults.condition) {
        conditionInput.value = normalizedDefaults.condition;
    }
    conditionInput.addEventListener('input', onMilestoneDetailChange);
    conditionField.appendChild(conditionInput);
    fields.appendChild(conditionField);

    item.appendChild(fields);
    const actionBar = document.createElement('div');
    actionBar.className = 'milestone-actions';
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'milestone-remove-button';
    removeButton.setAttribute('aria-label', '분할 단계 삭제');
    removeButton.innerHTML = '🗑';
    removeButton.addEventListener('click', () => {
        if (!milestoneList || !item.parentNode) {
            return;
        }
        milestoneList.removeChild(item);
        updateMilestoneLabels();
        updateMilestoneTotals();
        renderMilestoneLists(collectMilestoneDetails());
    });
    actionBar.appendChild(removeButton);
    item.appendChild(actionBar);
    milestoneList.appendChild(item);
    updateMilestoneLabels();
    updateMilestoneTotals();
}

function ensureInitialMilestones() {
    if (!milestoneList || milestonesInitialized) {
        updateMilestoneTotals();
        return;
    }
    for (let index = 0; index < 2; index += 1) {
        addMilestoneRow();
    }
    milestonesInitialized = true;
}

function togglePaymentSections(value) {
    const showMilestone = value === 'milestone';
    if (milestoneSection) {
        if (showMilestone) {
            milestoneSection.hidden = false;
            ensureInitialMilestones();
            updateMilestoneTotals();
        } else {
            milestoneSection.hidden = true;
            if (milestoneError) {
                milestoneError.hidden = true;
            }
            if (addMilestoneButton) {
                addMilestoneButton.disabled = false;
            }
            renderMilestoneLists([]);
            updateMilestonePreview(Number.NaN, Number.NaN, []);
        }
    }
    const showOneTime = value === 'one_time';
    if (oneTimeSection) {
        oneTimeSection.hidden = !showOneTime;
    }
    updateOneTimePreview();
}

function updatePeriod() {
    const startInput = document.getElementById('id_start_date');
    const endInput = document.getElementById('id_end_date');
    if (!startInput || !endInput || !previewMap.period) {
        return;
    }
    const start = startInput.value;
    const end = endInput.value;
    if (start && end) {
        previewMap.period.textContent = `${start} ~ ${end}`;
    } else if (start) {
        previewMap.period.textContent = `${start} ~ (종료일 미정)`;
    } else if (end) {
        previewMap.period.textContent = `(시작일 미정) ~ ${end}`;
    } else {
        previewMap.period.textContent = '-';
    }
}

function bindFieldUpdates() {
    const titleInput = document.getElementById('id_title');
    if (titleInput && previewMap.title) {
        previewMap.title.textContent = titleInput.value || '-';
        titleInput.addEventListener('input', (event) => {
            previewMap.title.textContent = event.target.value || '-';
        });
    }

    performerLightningInput = document.getElementById('id_performer_lightning_address');
    const roleInputs = document.querySelectorAll('input[name="role"]');
    roleContactFieldset = document.getElementById('role-contact-fieldset');
    roleLightningCard = document.getElementById('performer-lightning-card');
    roleEmailHelpTexts = roleContactFieldset
        ? Array.from(roleContactFieldset.querySelectorAll('[data-role-email-help]'))
        : [];
    if (roleInputs.length) {
        const checkedRole = document.querySelector('input[name="role"]:checked');
        const initialRole = checkedRole ? checkedRole.value : '';
        if (previewMap.role) {
            previewMap.role.textContent = formatRole(initialRole);
        }
        toggleRoleContactFields(initialRole);
        roleInputs.forEach((radio) => {
            radio.addEventListener('change', (event) => {
                const { value } = event.target;
                if (previewMap.role) {
                    previewMap.role.textContent = formatRole(value);
                }
                toggleRoleContactFields(value);
            });
        });
    }

    ['start_date', 'end_date'].forEach((field) => {
        const input = document.getElementById(`id_${field}`);
        if (input) {
            input.addEventListener('change', updatePeriod);
        }
    });
    updatePeriod();
    if (performerLightningInput) {
        updateLightningPreview();
        performerLightningInput.addEventListener('input', updateLightningPreview);
    }

    oneTimeDueInput = document.getElementById('id_one_time_due_date');
    oneTimeConditionInput = document.getElementById('id_one_time_condition');
    if (oneTimeDueInput) {
        oneTimeDueInput.addEventListener('change', updateOneTimePreview);
    }
    if (oneTimeConditionInput) {
        oneTimeConditionInput.addEventListener('input', updateOneTimePreview);
    }
    updateOneTimePreview();

    amountInput = document.getElementById('id_amount_sats');
    if (amountInput && previewMap.amount) {
        if (amountInput.value) {
            const numeric = parseInt(amountInput.value, 10);
            previewMap.amount.textContent = Number.isFinite(numeric)
                ? `${formatSats(numeric)} sats`
                : `${amountInput.value} sats`;
        } else {
            previewMap.amount.textContent = '-';
        }
        amountInput.addEventListener('input', (event) => {
            const value = event.target.value;
            if (value) {
                const numeric = parseInt(value, 10);
                previewMap.amount.textContent = Number.isFinite(numeric)
                    ? `${formatSats(numeric)} sats`
                    : `${value} sats`;
            } else {
                previewMap.amount.textContent = '-';
            }
            updateMilestoneTotals();
        });
    }

    paymentInputs = Array.from(document.querySelectorAll('input[name="payment_type"]'));
    if (paymentInputs.length && previewMap.payment) {
        const currentPayment = getCheckedValue(paymentInputs);
        previewMap.payment.textContent = formatPayment(currentPayment);
        togglePaymentSections(currentPayment || 'one_time');
        paymentInputs.forEach((input) => {
            input.addEventListener('change', (event) => {
                const { value } = event.target;
                previewMap.payment.textContent = formatPayment(value);
                togglePaymentSections(value);
                if (value === 'milestone') {
                    updateMilestoneTotals();
                } else {
                    setSubmitButtonState();
                }
            });
        });
    }

    const emailInput = document.getElementById('id_email_recipient');
    if (emailInput && previewMap.email) {
        previewMap.email.textContent = emailInput.value || '-';
        emailInput.addEventListener('input', (event) => {
            previewMap.email.textContent = event.target.value || '-';
        });
    }

    if (!submitButton) {
        const formElement = document.querySelector('form');
        submitButton = formElement ? formElement.querySelector('button[type="submit"]') : null;
    }

    agreementCheckboxes = Array.from(document.querySelectorAll('.agreement-field input[type="checkbox"]'));
    agreementCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener('change', () => {
            setSubmitButtonState();
        });
    });
    setSubmitButtonState();

    if (addMilestoneButton) {
        addMilestoneButton.addEventListener('click', () => {
            addMilestoneRow('');
        });
    }

    updateMilestoneTotals();
}

function hydrateTemplatePayload() {
    const templateNode = document.getElementById('active-contract-template');
    if (!templateNode) {
        templatePayload = null;
        return;
    }
    try {
        templatePayload = JSON.parse(templateNode.textContent);
    } catch (error) {
        templatePayload = null;
    }
}

function syncModalPreviewValues() {
    if (!previewModal) {
        return;
    }
    const modalMapping = {
        title: document.getElementById('modal-preview-title'),
        role: document.getElementById('modal-preview-role'),
        period: document.getElementById('modal-preview-period'),
        amount: document.getElementById('modal-preview-amount'),
        payment: document.getElementById('modal-preview-payment'),
        email: document.getElementById('modal-preview-email'),
        clientLightning: document.getElementById('modal-preview-client-lightning'),
        performerLightning: document.getElementById('modal-preview-performer-lightning'),
    };
    Object.entries(modalMapping).forEach(([key, target]) => {
        if (target && previewMap[key]) {
            target.textContent = previewMap[key].textContent;
        }
    });
}

function renderTemplateMarkdown(payload) {
    if (!modalTemplateMarkdown) {
        return;
    }
    const htmlContent = payload && typeof payload.content_html === 'string' ? payload.content_html.trim() : '';
    if (htmlContent) {
        modalTemplateMarkdown.innerHTML = htmlContent;
        return;
    }
    const markdownContent = payload && typeof payload.content === 'string' ? payload.content.trim() : '';
    const fallback = markdownContent || '계약서 본문이 비어 있습니다.';
    modalTemplateMarkdown.textContent = fallback;
    if (window.MarkdownRenderer && typeof window.MarkdownRenderer.render === 'function') {
        window.MarkdownRenderer.render(modalTemplateMarkdown);
    }
}

function openContractPreview() {
    if (!previewModal || !templatePayload) {
        return;
    }
    syncModalPreviewValues();
    renderTemplateMarkdown(templatePayload);
    previewModal.classList.add('is-active');
    previewModal.setAttribute('aria-hidden', 'false');
    document.documentElement.classList.add('is-clipped');
}

function closeContractPreview() {
    if (!previewModal) {
        return;
    }
    previewModal.classList.remove('is-active');
    previewModal.setAttribute('aria-hidden', 'true');
    document.documentElement.classList.remove('is-clipped');
}

function handleDocumentKeydown(event) {
    if (event.key === 'Escape' && previewModal && previewModal.classList.contains('is-active')) {
        closeContractPreview();
    }
}

function initWorkLogEditor() {
    const textarea = document.getElementById('id_work_log_markdown');
    if (!textarea) {
        return;
    }
    const syncPreview = (value) => {
        updateWorkLogPreview(value);
    };

    const applyValue = (rawValue) => {
        const source = rawValue || '';
        const normalized = clampWorklogValue(source);
        const truncated = normalized.length < source.length;
        if (textarea.value !== normalized) {
            textarea.value = normalized;
        }
        syncPreview(normalized);
        updateWorklogCounterDisplay(normalized.length, truncated);
        return { value: normalized, truncated };
    };

    const { value: initialValue } = applyValue(textarea.value || '');

    if (typeof EasyMDE === 'undefined') {
        textarea.addEventListener('input', (event) => {
            const currentValue = event.target.value || '';
            const normalized = clampWorklogValue(currentValue);
            const truncated = normalized.length < currentValue.length;
            if (normalized !== currentValue) {
                const caretPosition = Math.min(normalized.length, event.target.selectionStart || normalized.length);
                event.target.value = normalized;
                requestAnimationFrame(() => {
                    try {
                        event.target.setSelectionRange(caretPosition, caretPosition);
                    } catch (error) {
                        // selection range might fail in some browsers; ignore silently
                    }
                });
            }
            syncPreview(normalized);
            updateWorklogCounterDisplay(normalized.length, truncated);
        });
        return;
    }

    workLogEditor = new EasyMDE({
        element: textarea,
        autofocus: false,
        maxLength: 10000,
        spellChecker: false,
        status: false,
        placeholder: textarea.getAttribute('placeholder') || '최대 10,000자까지 작성할 수 있습니다.',
        toolbar: ['bold', 'italic', 'heading', '|', 'quote', 'unordered-list', 'ordered-list', '|', 'link', 'preview'],
    });
    if (workLogEditor.value() !== initialValue) {
        workLogEditor.value(initialValue);
    }
    workLogEditor.codemirror.on('change', () => {
        if (suppressWorklogEditorChange) {
            return;
        }
        let currentValue = workLogEditor.value() || '';
        const normalized = clampWorklogValue(currentValue);
        const truncated = normalized.length < currentValue.length;
        if (normalized !== currentValue) {
            suppressWorklogEditorChange = true;
            workLogEditor.value(normalized);
            suppressWorklogEditorChange = false;
            currentValue = normalized;
        }
        textarea.value = currentValue;
        syncPreview(currentValue);
        updateWorklogCounterDisplay(currentValue.length, truncated);
    });
}

function initAttachmentUploader() {
    attachmentUploader = document.getElementById('contract-attachment-uploader');
    if (!attachmentUploader) {
        return;
    }
    attachmentDropzone = document.getElementById('contract-attachment-dropzone');
    attachmentInput = document.getElementById('contract-attachment-input');
    attachmentTrigger = document.getElementById('contract-attachment-trigger');
    attachmentStatusNode = document.getElementById('contract-attachment-status');
    attachmentListNode = document.getElementById('contract-attachment-list');
    attachmentManifestInput = document.getElementById('id_attachment_manifest');
    attachmentUploadUrl = attachmentUploader.dataset.uploadUrl || '';

    const maxItemsAttr = parseInt(attachmentUploader.dataset.maxItems, 10);
    const maxSizeAttr = parseInt(attachmentUploader.dataset.maxSize, 10);
    if (Number.isFinite(maxItemsAttr) && maxItemsAttr > 0) {
        attachmentConfig.maxItems = maxItemsAttr;
    }
    if (Number.isFinite(maxSizeAttr) && maxSizeAttr > 0) {
        attachmentConfig.maxSize = maxSizeAttr;
    }

    if (attachmentManifestInput && attachmentManifestInput.value) {
        try {
            const parsed = JSON.parse(attachmentManifestInput.value);
            if (Array.isArray(parsed)) {
                attachmentEntries = parsed;
            }
        } catch (error) {
            attachmentEntries = [];
        }
    }

    renderAttachmentList();
    syncAttachmentManifest();
    renderAttachmentPreviewLists();
    toggleAttachmentAvailability();

    if (attachmentTrigger && attachmentInput) {
        attachmentTrigger.addEventListener('click', () => attachmentInput.click());
        attachmentInput.addEventListener('change', (event) => {
            if (event.target.files) {
                const files = Array.from(event.target.files);
                event.target.value = '';
                handleAttachmentFiles(files);
            }
        });
    }

    if (attachmentDropzone) {
        attachmentDropzone.addEventListener('dragover', (event) => {
            event.preventDefault();
            if (!attachmentDropzone.classList.contains('is-disabled')) {
                attachmentDropzone.classList.add('drag-over');
            }
        });
        attachmentDropzone.addEventListener('dragleave', (event) => {
            event.preventDefault();
            if (event.target === attachmentDropzone) {
                attachmentDropzone.classList.remove('drag-over');
            }
        });
        attachmentDropzone.addEventListener('drop', (event) => {
            event.preventDefault();
            attachmentDropzone.classList.remove('drag-over');
            if (attachmentDropzone.classList.contains('is-disabled')) {
                return;
            }
            const files = Array.from(event.dataTransfer.files || []);
            handleAttachmentFiles(files);
        });
        attachmentDropzone.addEventListener('click', (event) => {
            if (event.target === attachmentDropzone && attachmentInput && !attachmentDropzone.classList.contains('is-disabled')) {
                attachmentInput.click();
            }
        });
    }
}

function handleAttachmentFiles(files) {
    if (!files || !files.length) {
        return;
    }
    const availableSlots = attachmentConfig.maxItems - attachmentEntries.length;
    if (availableSlots <= 0) {
        setAttachmentStatus('더 이상 파일을 업로드할 수 없습니다.', 'error');
        return;
    }
    const limitedFiles = files.slice(0, availableSlots);
    limitedFiles.forEach((file) => {
        const validationMessage = validateAttachment(file);
        if (validationMessage) {
            setAttachmentStatus(validationMessage, 'error');
        } else {
            uploadAttachment(file);
        }
    });
}

function validateAttachment(file) {
    if (!isPdfFile(file)) {
        return 'PDF 형식의 파일만 업로드할 수 있습니다.';
    }
    if (file.size > attachmentConfig.maxSize) {
        return `파일 크기가 너무 큽니다. ${formatBytes(attachmentConfig.maxSize)} 이하로 제한됩니다.`;
    }
    return '';
}

async function uploadAttachment(file) {
    if (!attachmentUploadUrl) {
        setAttachmentStatus('업로드 엔드포인트가 설정되지 않았습니다.', 'error');
        return;
    }
    toggleAttachmentAvailability(true);
    setAttachmentStatus(`"${file.name}" 업로드 중입니다...`);
    const formData = new FormData();
    formData.append('attachment', file);
    const csrfToken = getCsrfToken();
    if (csrfToken) {
        formData.append('csrfmiddlewaretoken', csrfToken);
    }
    try {
        const response = await fetch(attachmentUploadUrl, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const result = await response.json();
        if (!response.ok || !result.success) {
            const errorMessage = result && result.error ? result.error : '업로드에 실패했습니다.';
            throw new Error(errorMessage);
        }
        attachmentEntries.push(result.attachment);
        renderAttachmentList();
        syncAttachmentManifest();
        renderAttachmentPreviewLists();
        setAttachmentStatus(`"${file.name}" 업로드가 완료되었습니다.`, 'success');
    } catch (error) {
        setAttachmentStatus(error.message || '파일 업로드 중 오류가 발생했습니다.', 'error');
    } finally {
        toggleAttachmentAvailability();
    }
}

function renderAttachmentList() {
    if (!attachmentListNode) {
        return;
    }
    attachmentListNode.innerHTML = '';
    if (!attachmentEntries.length) {
        return;
    }
    attachmentEntries.forEach((item, index) => {
        const listItem = document.createElement('li');
        listItem.className = 'attachment-item';
        listItem.innerHTML = `
            <div class="attachment-meta">
                <span class="attachment-name">${item.name || '첨부 파일'}</span>
                <span class="attachment-size">${formatBytes(item.size)}</span>
                ${item.url ? `<a href="${item.url}" class="attachment-link" target="_blank" rel="noopener noreferrer">파일 열기</a>` : ''}
            </div>
            <button type="button" class="attachment-remove" data-attachment-index="${index}">
                제거
            </button>
        `;
        attachmentListNode.appendChild(listItem);
    });
    attachmentListNode.querySelectorAll('.attachment-remove').forEach((button) => {
        button.addEventListener('click', () => {
            const index = parseInt(button.getAttribute('data-attachment-index'), 10);
            removeAttachment(index);
        });
    });
}

function removeAttachment(index) {
    if (Number.isNaN(index) || index < 0 || index >= attachmentEntries.length) {
        return;
    }
    attachmentEntries.splice(index, 1);
    renderAttachmentList();
    syncAttachmentManifest();
    toggleAttachmentAvailability();
    renderAttachmentPreviewLists();
    setAttachmentStatus('첨부 파일이 삭제되었습니다.', 'success');
}

function syncAttachmentManifest() {
    if (!attachmentManifestInput) {
        return;
    }
    attachmentManifestInput.value = JSON.stringify(attachmentEntries);
}

function setAttachmentStatus(message, variant = 'info') {
    if (!attachmentStatusNode) {
        return;
    }
    attachmentStatusNode.textContent = message || '';
    attachmentStatusNode.classList.remove('is-error', 'is-success');
    if (variant === 'error') {
        attachmentStatusNode.classList.add('is-error');
    } else if (variant === 'success') {
        attachmentStatusNode.classList.add('is-success');
    }
}

function toggleAttachmentAvailability(forceBusy = false) {
    if (!attachmentDropzone || !attachmentTrigger) {
        return;
    }
    const isFull = attachmentEntries.length >= attachmentConfig.maxItems;
    const isBusy = Boolean(forceBusy);
    const shouldDisable = isFull || isBusy;
    attachmentDropzone.classList.toggle('is-disabled', shouldDisable);
    attachmentTrigger.disabled = shouldDisable;
}

document.addEventListener('DOMContentLoaded', () => {
    milestoneSection = document.getElementById('milestone-section');
    milestoneList = document.getElementById('milestone-list');
    addMilestoneButton = document.getElementById('add-milestone');
    milestoneRemaining = document.getElementById('milestone-remaining');
    milestoneError = document.getElementById('milestone-error');
    oneTimeSection = document.getElementById('one-time-section');
    previewOneTimePanel = document.getElementById('preview-one-time-panel');
    modalOneTimePanel = document.getElementById('modal-preview-one-time');
    modalOneTimeDate = document.getElementById('modal-preview-one-time-date');
    modalOneTimeCondition = document.getElementById('modal-preview-one-time-condition');
    previewMilestonePanel = document.getElementById('preview-milestone-panel');
    previewMilestoneList = document.getElementById('preview-milestone-list');
    modalMilestonePanel = document.getElementById('modal-preview-milestones');
    modalMilestoneList = document.getElementById('modal-preview-milestone-list');
    previewWorklogNode = document.getElementById('preview-worklog');
    modalWorklogNode = document.getElementById('modal-preview-worklog');
    previewAttachmentPanel = document.getElementById('preview-attachments');
    previewAttachmentList = document.getElementById('preview-attachment-list');
    modalAttachmentPanel = document.getElementById('modal-preview-attachments');
    modalAttachmentList = document.getElementById('modal-preview-attachment-list');
    modalPerformerLightning = document.getElementById('modal-preview-performer-lightning');

    bindFieldUpdates();
    const initialPayment = getCheckedValue(paymentInputs);
    togglePaymentSections(initialPayment);
    hydrateTemplatePayload();
    previewModalButton = document.getElementById('contract-preview-trigger');
    previewModal = document.getElementById('contract-preview-modal');
    modalTemplateMarkdown = document.getElementById('modal-template-markdown');
    previewModalCloseButtons = Array.from(document.querySelectorAll('[data-close-contract-modal]'));

    if (previewModalButton && previewModal && templatePayload) {
        previewModalButton.addEventListener('click', openContractPreview);
        previewModalCloseButtons.forEach((button) => {
            button.addEventListener('click', closeContractPreview);
        });
        document.addEventListener('keydown', handleDocumentKeydown);
    }
    initWorkLogEditor();
    initAttachmentUploader();
});
