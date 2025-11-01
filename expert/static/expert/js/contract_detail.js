document.addEventListener('DOMContentLoaded', () => {
    const panel = document.querySelector('.chat-panel');
    const log = document.getElementById('contract-chat-log');
    const form = document.getElementById('contract-chat-form');
    const input = document.getElementById('contract-chat-input');
    const indicator = panel?.querySelector('.connection-indicator');

    if (!panel || !log || !form || !input) {
        return;
    }

    const socketPath = panel.getAttribute('data-websocket');
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socketUrl = `${scheme}://${window.location.host}${socketPath}`;

    let socket = null;

    function setConnectionStatus(status) {
        if (!indicator) {
            return;
        }
        indicator.dataset.status = status;
        if (status === 'connected') {
            indicator.textContent = '연결됨';
        } else if (status === 'connecting') {
            indicator.textContent = '접속 중...';
        } else {
            indicator.textContent = '연결 끊김 - 다시 시도 중';
        }
    }

    function appendMessage(payload) {
        const wrapper = document.createElement('div');
        wrapper.className = 'chat-message';

        const meta = document.createElement('div');
        meta.className = 'chat-meta';
        const sender = document.createElement('span');
        sender.className = 'chat-sender';
        sender.textContent = payload.sender || '시스템';
        meta.appendChild(sender);

        if (payload.sender_role) {
            const role = document.createElement('span');
            role.className = 'chat-role';
            role.textContent = payload.sender_role === 'client' ? '의뢰자' :
                payload.sender_role === 'performer' ? '수행자' : payload.sender_role;
            meta.appendChild(role);
        }

        const time = document.createElement('span');
        time.className = 'chat-time';
        const timestamp = payload.timestamp ? new Date(payload.timestamp) : new Date();
        time.textContent = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        meta.appendChild(time);

        const body = document.createElement('p');
        body.className = 'chat-body';
        body.textContent = payload.message;

        wrapper.appendChild(meta);
        wrapper.appendChild(body);
        log.appendChild(wrapper);
        log.scrollTop = log.scrollHeight;
    }

    function connectSocket() {
        setConnectionStatus('connecting');
        socket = new WebSocket(socketUrl);

        socket.addEventListener('open', () => {
            setConnectionStatus('connected');
        });

        socket.addEventListener('message', (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'chat.system') {
                    data.sender = '시스템';
                }
                appendMessage(data);
            } catch (error) {
                console.error('채팅 메시지 처리 실패', error);
            }
        });

        socket.addEventListener('close', () => {
            setConnectionStatus('disconnected');
            setTimeout(connectSocket, 3000);
        });

        socket.addEventListener('error', () => {
            setConnectionStatus('disconnected');
        });
    }

    connectSocket();

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const message = input.value.trim();
        if (!message || !socket || socket.readyState !== WebSocket.OPEN) {
            return;
        }
        socket.send(JSON.stringify({ message }));
        input.value = '';
    });

    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            form.dispatchEvent(new Event('submit'));
        }
    });
});
