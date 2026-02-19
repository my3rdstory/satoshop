document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("nostrLoginRoot");
    const startBtn = document.getElementById("startNostrLoginBtn");
    const statusEl = document.getElementById("nostrStatus");
    const connectPanel = document.getElementById("nostrConnectPanel");
    const connectQrImage = document.getElementById("nostrConnectQrImage");
    const connectUriInput = document.getElementById("nostrConnectUri");
    const copyConnectUriBtn = document.getElementById("copyNostrConnectUriBtn");
    const openConnectUriBtn = document.getElementById("openNostrConnectUriBtn");

    if (!root || !startBtn || !statusEl) {
        return;
    }

    const challengeUrl = root.dataset.challengeUrl || "/accounts/nostr-auth-challenge/";
    const verifyUrl = root.dataset.verifyUrl || "/accounts/nostr-auth-verify/";
    const defaultNextUrl = root.dataset.defaultNext || "/accounts/mypage/";
    const nip46Relays = (root.dataset.nip46Relays || "wss://relay.nsec.app,wss://relay.damus.io")
        .split(",")
        .map((relay) => relay.trim())
        .filter(Boolean);

    let activeBunkerSigner = null;
    let activePool = null;
    let currentNostrConnectUri = "";
    let nip46ToolsPromise = null;

    startBtn.addEventListener("click", async () => {
        startBtn.disabled = true;
        hideNostrConnectPanel();

        try {
            if (isNip07Available()) {
                setStatus("pending", "NIP-07 확장 지갑을 확인했습니다. 서명 요청을 준비합니다...");
                await loginWithNip07();
            } else {
                setStatus("pending", "NIP-07 확장이 없어 Nostr Connect로 전환합니다...");
                await loginWithNip46();
            }
        } catch (error) {
            setStatus("error", error.message || "Nostr 로그인 중 오류가 발생했습니다.");
            startBtn.disabled = false;
            cleanupNip46();
        }
    });

    if (copyConnectUriBtn) {
        copyConnectUriBtn.addEventListener("click", async () => {
            if (!currentNostrConnectUri) {
                return;
            }

            try {
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    await navigator.clipboard.writeText(currentNostrConnectUri);
                } else if (connectUriInput) {
                    connectUriInput.select();
                    document.execCommand("copy");
                }
                setStatus("pending", "Nostr Connect URI를 복사했습니다. 지갑 앱에서 열어 승인해 주세요.");
            } catch (error) {
                setStatus("error", "URI 복사에 실패했습니다. 수동으로 복사해 주세요.");
            }
        });
    }

    if (openConnectUriBtn) {
        openConnectUriBtn.addEventListener("click", () => {
            if (!currentNostrConnectUri) {
                return;
            }
            try {
                window.location.assign(currentNostrConnectUri);
            } catch (error) {
                setStatus("error", "지갑 앱을 열지 못했습니다. URI 복사 후 수동으로 열어주세요.");
            }
        });
    }

    async function loginWithNip07() {
        const pubkey = await window.nostr.getPublicKey();
        const challenge = await fetchLoginChallenge(pubkey);
        const loginEvent = buildLoginEvent(challenge);
        setStatus("pending", "Nostr 확장에서 서명을 승인해 주세요...");
        const signedEvent = await window.nostr.signEvent(loginEvent);
        const verified = await verifyLoginSignature({
            challengeId: challenge.challenge_id,
            pubkey,
            event: signedEvent,
        });
        completeLogin(verified);
    }

    async function loginWithNip46() {
        const tools = await loadNip46Tools();
        const relayUrls = nip46Relays.length ? nip46Relays : ["wss://relay.nsec.app"];

        const clientSecretKey = tools.generateSecretKey();
        const clientPublicKey = tools.getPublicKey(clientSecretKey);
        const connectSecret = generateNostrConnectSecret(tools.BunkerSigner);
        const connectUri = tools.createNostrConnectURI({
            clientPubkey: clientPublicKey,
            relays: relayUrls,
            secret: connectSecret,
            name: "SatoShop",
            url: window.location.origin,
            perms: ["sign_event:22242"],
        });

        currentNostrConnectUri = connectUri;
        renderNostrConnectUri(connectUri);
        showNostrConnectPanel();
        setStatus("pending", "지갑 앱에서 Nostr Connect를 승인해 주세요. (QR 스캔 또는 앱 열기)");

        activePool = new tools.SimplePool();
        if (tools.BunkerSigner && typeof tools.BunkerSigner.fromURI === "function") {
            activeBunkerSigner = await withTimeout(
                tools.BunkerSigner.fromURI(
                    clientSecretKey,
                    connectUri,
                    {
                        pool: activePool,
                        autoCloseRelays: false,
                    },
                ),
                180000,
                "Nostr Connect 연결 대기 시간이 만료되었습니다. 다시 시도해 주세요.",
            );
        } else {
            throw new Error("NIP-46 signer 초기화 함수(fromURI)를 찾을 수 없습니다.");
        }

        setStatus("pending", "지갑 연결 완료. 로그인 서명을 요청합니다...");
        const pubkey = await withTimeout(
            activeBunkerSigner.getPublicKey(),
            20000,
            "지갑 공개키를 가져오지 못했습니다. 다시 시도해 주세요.",
        );

        const challenge = await fetchLoginChallenge(pubkey);
        const loginEvent = buildLoginEvent(challenge);
        const signedEvent = await withTimeout(
            activeBunkerSigner.signEvent(loginEvent),
            120000,
            "서명 대기 시간이 만료되었습니다. 지갑 앱에서 다시 승인해 주세요.",
        );

        const verified = await verifyLoginSignature({
            challengeId: challenge.challenge_id,
            pubkey,
            event: signedEvent,
        });
        cleanupNip46();
        completeLogin(verified);
    }

    async function fetchLoginChallenge(pubkey) {
        const url = new URL(challengeUrl, window.location.origin);
        url.searchParams.set("pubkey", pubkey);

        const next = getNextParam();
        if (next) {
            url.searchParams.set("next", next);
        }

        const response = await fetch(url.toString(), {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            throw new Error(payload.error || "Nostr 로그인 챌린지를 생성하지 못했습니다.");
        }
        return payload;
    }

    function buildLoginEvent(challenge) {
        return {
            kind: challenge.kind || 22242,
            created_at: Math.floor(Date.now() / 1000),
            tags: [
                ["challenge", challenge.challenge],
                ["domain", challenge.domain || window.location.host],
            ],
            content: "SatoShop Nostr login",
        };
    }

    async function verifyLoginSignature({ challengeId, pubkey, event }) {
        const response = await fetch(verifyUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                challenge_id: challengeId,
                pubkey,
                event,
            }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            throw new Error(payload.error || "Nostr 로그인 검증에 실패했습니다.");
        }
        return payload;
    }

    function completeLogin(verified) {
        setStatus(
            "success",
            verified.is_new
                ? "새 계정이 생성되어 로그인되었습니다. 이동합니다..."
                : "로그인이 완료되었습니다. 이동합니다...",
        );
        const nextUrl = verified.next_url || getNextParam() || defaultNextUrl;
        setTimeout(() => {
            window.location.href = nextUrl;
        }, 800);
    }

    function isNip07Available() {
        return Boolean(
            window.nostr
            && typeof window.nostr.getPublicKey === "function"
            && typeof window.nostr.signEvent === "function",
        );
    }

    function showNostrConnectPanel() {
        if (connectPanel) {
            connectPanel.classList.remove("hidden");
        }
    }

    function hideNostrConnectPanel() {
        if (connectPanel) {
            connectPanel.classList.add("hidden");
        }
    }

    function renderNostrConnectUri(uri) {
        if (connectUriInput) {
            connectUriInput.value = uri;
        }
        if (connectQrImage && window.QRious) {
            const canvas = document.createElement("canvas");
            const qr = new window.QRious({
                element: canvas,
                value: uri,
                size: 240,
                foreground: "#111827",
                background: "#ffffff",
                level: "M",
            });
            connectQrImage.src = qr.element.toDataURL();
        }
    }

    async function loadNip46Tools() {
        if (!nip46ToolsPromise) {
            nip46ToolsPromise = Promise.all([
                import("https://esm.sh/nostr-tools@2.17.0/pure"),
                import("https://esm.sh/nostr-tools@2.17.0/nip46"),
                import("https://esm.sh/nostr-tools@2.17.0/pool"),
            ]).then(([pureModule, nip46Module, poolModule]) => ({
                generateSecretKey: pureModule.generateSecretKey,
                getPublicKey: pureModule.getPublicKey,
                BunkerSigner: nip46Module.BunkerSigner,
                createNostrConnectURI: nip46Module.createNostrConnectURI,
                SimplePool: poolModule.SimplePool,
            }));
        }
        return nip46ToolsPromise;
    }

    function generateNostrConnectSecret(BunkerSigner) {
        if (BunkerSigner && typeof BunkerSigner.generateSecret === "function") {
            return BunkerSigner.generateSecret();
        }

        // 일부 nostr-tools 버전에는 BunkerSigner.generateSecret이 없어 직접 생성한다.
        const bytes = new Uint8Array(16);
        if (window.crypto && typeof window.crypto.getRandomValues === "function") {
            window.crypto.getRandomValues(bytes);
        } else {
            for (let i = 0; i < bytes.length; i += 1) {
                bytes[i] = Math.floor(Math.random() * 256);
            }
        }
        return Array.from(bytes)
            .map((value) => value.toString(16).padStart(2, "0"))
            .join("");
    }

    async function withTimeout(promise, ms, timeoutMessage) {
        let timer = null;
        return new Promise((resolve, reject) => {
            timer = setTimeout(() => {
                reject(new Error(timeoutMessage));
            }, ms);

            promise
                .then((result) => {
                    clearTimeout(timer);
                    resolve(result);
                })
                .catch((error) => {
                    clearTimeout(timer);
                    reject(error);
                });
        });
    }

    function cleanupNip46() {
        try {
            if (activeBunkerSigner && typeof activeBunkerSigner.close === "function") {
                activeBunkerSigner.close();
            }
        } catch (error) {
            console.warn("Bunker signer close 실패", error);
        }
        try {
            if (activePool && typeof activePool.close === "function") {
                activePool.close(nip46Relays);
            }
        } catch (error) {
            console.warn("NIP-46 relay close 실패", error);
        }
        activeBunkerSigner = null;
        activePool = null;
    }

    function getCookie(name) {
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (let i = 0; i < cookies.length; i += 1) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(`${name}=`)) {
                return decodeURIComponent(cookie.slice(name.length + 1));
            }
        }
        return "";
    }

    function getNextParam() {
        const params = new URLSearchParams(window.location.search);
        return params.get("next");
    }

    function setStatus(status, message) {
        statusEl.className = `nostr-status nostr-status-${status} mt-6`;
        statusEl.innerHTML = `<i class="fas fa-info-circle mr-2"></i>${message}`;
    }
});
