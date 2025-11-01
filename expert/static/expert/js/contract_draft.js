const previewMap = {
    title: document.getElementById('preview-title'),
    role: document.getElementById('preview-role'),
    period: document.getElementById('preview-period'),
    amount: document.getElementById('preview-amount'),
    payment: document.getElementById('preview-payment'),
    chat: document.getElementById('preview-chat'),
    email: document.getElementById('preview-email'),
};

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
        titleInput.addEventListener('input', (event) => {
            previewMap.title.textContent = event.target.value || '-';
        });
    }

    const roleInputs = document.querySelectorAll('input[name="role"]');
    if (roleInputs.length && previewMap.role) {
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

    const amountInput = document.getElementById('id_amount_sats');
    if (amountInput && previewMap.amount) {
        amountInput.addEventListener('input', (event) => {
            const value = event.target.value;
            previewMap.amount.textContent = value ? `${value} sats` : '-';
        });
    }

    const paymentSelect = document.getElementById('id_payment_type');
    if (paymentSelect && previewMap.payment) {
        paymentSelect.addEventListener('change', (event) => {
            previewMap.payment.textContent = formatPayment(event.target.value);
        });
    }

    const chatSelect = document.getElementById('id_enable_chat');
    if (chatSelect && previewMap.chat) {
        chatSelect.addEventListener('change', (event) => {
            previewMap.chat.textContent = formatChat(event.target.value);
        });
    }

    const emailInput = document.getElementById('id_email_recipient');
    if (emailInput && previewMap.email) {
        emailInput.addEventListener('input', (event) => {
            previewMap.email.textContent = event.target.value || '-';
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    bindFieldUpdates();
});
