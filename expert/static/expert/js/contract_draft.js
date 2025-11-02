const previewMap = {
    title: document.getElementById('preview-title'),
    role: document.getElementById('preview-role'),
    period: document.getElementById('preview-period'),
    amount: document.getElementById('preview-amount'),
    payment: document.getElementById('preview-payment'),
    chat: document.getElementById('preview-chat'),
    email: document.getElementById('preview-email'),
};

let amountInput;
let paymentInputs = [];
let chatInput = null;
let submitButton;
let milestoneSection;
let milestoneList;
let addMilestoneButton;
let milestoneRemaining;
let milestoneError;
let milestonesInitialized = false;
let milestoneOverflow = false;

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

function formatPayment(value) {
    if (value === 'one_time') return '일괄 지급';
    if (value === 'milestone') return '분할 지급';
    return '-';
}

function formatChat(value) {
    if (value === 'on') return '채팅 활성화';
    if (value === 'off') return '채팅 비활성화';
    return '-';
}

function getCheckedValue(inputs) {
    if (!inputs || !inputs.length) {
        return null;
    }
    const found = inputs.find((input) => input.checked);
    return found ? found.value : null;
}

function getMilestoneInputs() {
    if (!milestoneList) {
        return [];
    }
    return Array.from(milestoneList.querySelectorAll('.milestone-input'));
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

function updateMilestonePreview(totalAmount, remaining) {
    if (!previewMap.payment || !paymentInputs.length) {
        return;
    }
    const paymentValue = getCheckedValue(paymentInputs);
    if (paymentValue !== 'milestone') {
        previewMap.payment.textContent = formatPayment(paymentValue);
        return;
    }
    const milestoneCount = getMilestoneInputs().length;
    if (!Number.isFinite(totalAmount) || totalAmount <= 0) {
        previewMap.payment.textContent = '분할 지급 (총액 입력 대기)';
        return;
    }
    const remainingText = formatSats(Math.max(remaining, 0));
    previewMap.payment.textContent = `분할 지급 (${milestoneCount}회, 남은 ${remainingText} sats)`;
}

function updateMilestoneTotals() {
    if (!milestoneSection) {
        return;
    }

    const inputs = getMilestoneInputs();
    const totalAmount = parseInt(amountInput ? amountInput.value : '', 10);
    const hasTotal = Number.isFinite(totalAmount) && totalAmount > 0;

    if (!hasTotal) {
        inputs.forEach((input) => {
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
        if (submitButton) {
            submitButton.disabled = false;
        }
        updateMilestonePreview(Number.NaN, Number.NaN);
        return;
    }

    inputs.forEach((input) => {
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
    if (submitButton) {
        submitButton.disabled = false;
    }

    if (addMilestoneButton) {
        addMilestoneButton.disabled = remaining === 0;
    }

    updateMilestonePreview(totalAmount, remaining);
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
    const inputs = getMilestoneInputs();
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

function addMilestoneRow(defaultValue = '') {
    if (!milestoneList) {
        return;
    }
    const item = document.createElement('div');
    item.className = 'milestone-item';

    const label = document.createElement('span');
    label.className = 'milestone-order';
    item.appendChild(label);

    const input = document.createElement('input');
    input.type = 'number';
    input.inputMode = 'numeric';
    input.min = '0';
    input.className = 'input milestone-input';
    input.name = 'milestones[]';
    input.placeholder = '예: 50000';
    if (defaultValue !== undefined && defaultValue !== null && defaultValue !== '') {
        input.value = defaultValue;
    }
    input.addEventListener('input', onMilestoneInput);
    item.appendChild(input);

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
        addMilestoneRow('');
    }
    milestonesInitialized = true;
}

function toggleMilestoneSection(show) {
    if (!milestoneSection) {
        return;
    }
    if (show) {
        milestoneSection.hidden = false;
        ensureInitialMilestones();
        updateMilestoneTotals();
        return;
    }
    milestoneSection.hidden = true;
    if (milestoneError) {
        milestoneError.hidden = true;
    }
    if (addMilestoneButton) {
        addMilestoneButton.disabled = false;
    }
    if (submitButton) {
        submitButton.disabled = false;
    }
    updateMilestonePreview(Number.NaN, Number.NaN);
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

    const roleInputs = document.querySelectorAll('input[name="role"]');
    if (roleInputs.length && previewMap.role) {
        const checkedRole = document.querySelector('input[name="role"]:checked');
        if (checkedRole) {
            previewMap.role.textContent = formatRole(checkedRole.value);
        }
        roleInputs.forEach((radio) => {
            radio.addEventListener('change', (event) => {
                previewMap.role.textContent = formatRole(event.target.value);
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
        paymentInputs.forEach((input) => {
            input.addEventListener('change', (event) => {
                const { value } = event.target;
                previewMap.payment.textContent = formatPayment(value);
                toggleMilestoneSection(value === 'milestone');
                updateMilestoneTotals();
            });
        });
    }

    chatInput = document.querySelector('input[name="enable_chat"]');
    if (chatInput && previewMap.chat) {
        previewMap.chat.textContent = formatChat(chatInput.value);
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

    if (addMilestoneButton) {
        addMilestoneButton.addEventListener('click', () => {
            addMilestoneRow('');
        });
    }

    updateMilestoneTotals();
}

document.addEventListener('DOMContentLoaded', () => {
    milestoneSection = document.getElementById('milestone-section');
    milestoneList = document.getElementById('milestone-list');
    addMilestoneButton = document.getElementById('add-milestone');
   milestoneRemaining = document.getElementById('milestone-remaining');
   milestoneError = document.getElementById('milestone-error');

    bindFieldUpdates();
    const initialPayment = getCheckedValue(paymentInputs);
    toggleMilestoneSection(initialPayment === 'milestone');
});
