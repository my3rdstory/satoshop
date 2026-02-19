document.addEventListener("DOMContentLoaded", () => {
    const NIP46_PENDING_STORAGE_KEY = "satoshop:nostr:nip46:pending";
    const NIP46_PENDING_MAX_AGE_MS = 4 * 60 * 1000;

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
    const statusUrl = root.dataset.statusUrl || "/accounts/check-nostr-auth/";
    const pendingCreateUrl = root.dataset.pendingCreateUrl || "/accounts/nostr-auth-pending/create/";
    const pendingFetchUrl = root.dataset.pendingFetchUrl || "/accounts/nostr-auth-pending/fetch/";
    const pendingClearUrl = root.dataset.pendingClearUrl || "/accounts/nostr-auth-pending/clear/";
    const defaultNextUrl = root.dataset.defaultNext || "/accounts/mypage/";
    const nip46Relays = (root.dataset.nip46Relays || "wss://relay.nsec.app,wss://relay.damus.io")
        .split(",")
        .map((relay) => relay.trim())
        .filter(Boolean);

    let activeBunkerSigner = null;
    let activePool = null;
    let currentNostrConnectUri = "";
    let nip46ToolsPromise = null;
    let activeNip46Task = null;
    let statusPollingTimer = null;
    let activeChallengeId = "";
    let hasCompletedLogin = false;

    restorePendingNip46Session();

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") {
            resumePendingNip46Session();
        }
    });
    window.addEventListener("pageshow", () => {
        resumePendingNip46Session();
    });

    startBtn.addEventListener("click", async () => {
        startBtn.disabled = true;
        hideNostrConnectPanel();

        try {
            if (isNip07Available()) {
                setStatus("pending", "NIP-07 확장 지갑을 확인했습니다. 서명 요청을 준비합니다...");
                try {
                    await loginWithNip07();
                    return;
                } catch (nip07Error) {
                    console.warn("NIP-07 로그인 실패, NIP-46로 폴백합니다.", nip07Error);
                    setStatus("pending", "NIP-07 로그인에 실패해 Nostr Connect로 전환합니다...");
                    await beginNip46Login();
                    return;
                }
            } else {
                setStatus("pending", "NIP-07 확장이 없어 Nostr Connect로 전환합니다...");
                await beginNip46Login();
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
        activeChallengeId = challenge.challenge_id;
        startStatusPolling(activeChallengeId);
        const loginEvent = buildLoginEvent(challenge);
        setStatus("pending", "Nostr 확장에서 서명을 승인해 주세요...");
        const signedEvent = await window.nostr.signEvent(loginEvent);
        await verifyLoginSignature({
            challengeId: challenge.challenge_id,
            pubkey,
            event: signedEvent,
        });
        await finalizeLoginFromStatusOrFallback(challenge.challenge_id);
    }

    async function beginNip46Login({ usePending = false } = {}) {
        const tools = await loadNip46Tools();
        const relayUrls = nip46Relays.length ? nip46Relays : ["wss://relay.nsec.app"];
        let clientSecretKey = null;
        let connectUri = "";

        const pendingSession = usePending ? getPendingNip46Session() : null;
        if (pendingSession) {
            clientSecretKey = secretKeyFromHex(pendingSession.clientSecretKeyHex);
            connectUri = pendingSession.connectUri;
        } else {
            clientSecretKey = tools.generateSecretKey();
            const clientPublicKey = tools.getPublicKey(clientSecretKey);
            const connectSecret = generateNostrConnectSecret(tools.BunkerSigner);
            const baseConnectUri = tools.createNostrConnectURI({
                pubkey: clientPublicKey,
                clientPubkey: clientPublicKey,
                relays: relayUrls,
                relayUrls: relayUrls,
                secret: connectSecret,
                name: "SatoShop",
                url: window.location.origin,
                perms: ["sign_event:22242", "sign_event", "get_public_key"],
                permissions: ["sign_event:22242", "sign_event", "get_public_key"],
            });
            const challenge = await fetchLoginChallenge("");
            activeChallengeId = challenge.challenge_id;
            startStatusPolling(activeChallengeId);

            const pendingPayload = {
                clientSecretKeyHex: secretKeyToHex(clientSecretKey),
                connectUri: baseConnectUri,
                challenge,
                createdAt: Date.now(),
            };
            const resumeToken = await createPendingSessionOnServer(pendingPayload);
            connectUri = appendNostrConnectCallback(baseConnectUri, buildNostrConnectCallbackUrl(resumeToken));
            pendingPayload.connectUri = connectUri;
            pendingPayload.resumeToken = resumeToken;
            savePendingNip46Session(pendingPayload);
        }

        const challenge = pendingSession?.challenge || getPendingNip46Session()?.challenge;
        if (!challenge || !challenge.challenge_id) {
            throw new Error("Nostr 로그인 챌린지를 복구하지 못했습니다. 다시 시도해 주세요.");
        }
        activeChallengeId = challenge.challenge_id;
        startStatusPolling(activeChallengeId);
        if (pendingSession && !pendingSession.resumeToken) {
            const resumeToken = getResumeTokenFromUrl();
            if (resumeToken) {
                savePendingNip46Session({
                    ...pendingSession,
                    resumeToken,
                });
            }
        }

        currentNostrConnectUri = connectUri;
        renderNostrConnectUri(connectUri);
        showNostrConnectPanel();
        setStatus("pending", "지갑 앱에서 Nostr Connect를 승인해 주세요. (QR 스캔 또는 앱 열기)");

        await runNip46Handshake({
            tools,
            clientSecretKey,
            connectUri,
            relayUrls,
            challenge,
        });
    }

    async function runNip46Handshake({ tools, clientSecretKey, connectUri, relayUrls, challenge }) {
        if (activeNip46Task) {
            return activeNip46Task;
        }

        activeNip46Task = (async () => {
            activePool = new tools.SimplePool();
            if (!(tools.BunkerSigner && typeof tools.BunkerSigner.fromURI === "function")) {
                throw new Error("NIP-46 signer 초기화 함수(fromURI)를 찾을 수 없습니다.");
            }
            activeBunkerSigner = await withTimeout(
                createBunkerSignerFromURI({
                    BunkerSigner: tools.BunkerSigner,
                    pool: activePool,
                    clientSecretKey,
                    connectUri,
                }),
                300000,
                "Nostr Connect 연결 대기 시간이 만료되었습니다. 다시 시도해 주세요.",
            );

            if (activeBunkerSigner && typeof activeBunkerSigner.waitForAuth === "function") {
                await withTimeout(
                    activeBunkerSigner.waitForAuth(),
                    300000,
                    "지갑 승인 대기 시간이 만료되었습니다. 다시 시도해 주세요.",
                );
            }

            setStatus("pending", "지갑 연결 완료. 로그인 서명을 요청합니다...");
            const loginEvent = buildLoginEvent(challenge);
            const signedEvent = await withTimeout(
                activeBunkerSigner.signEvent(loginEvent),
                120000,
                "서명 대기 시간이 만료되었습니다. 지갑 앱에서 다시 승인해 주세요.",
            );

            const signedPubkey = (signedEvent && typeof signedEvent.pubkey === "string") ? signedEvent.pubkey : "";
            await verifyLoginSignature({
                challengeId: challenge.challenge_id,
                pubkey: signedPubkey,
                event: signedEvent,
            });
            await finalizeLoginFromStatusOrFallback(challenge.challenge_id);
            clearPendingNip46Session();
            cleanupNip46(relayUrls);
        })();

        try {
            await activeNip46Task;
        } finally {
            activeNip46Task = null;
        }
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

    async function checkNostrLoginStatus(challengeId) {
        if (!challengeId) {
            return {
                authenticated: false,
                pending: true,
            };
        }

        const url = new URL(statusUrl, window.location.origin);
        url.searchParams.set("challenge_id", challengeId);
        const response = await fetch(url.toString(), {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || payload.detail || "Nostr 로그인 상태 확인에 실패했습니다.");
        }
        return payload;
    }

    async function finalizeLoginFromStatusOrFallback(challengeId) {
        try {
            const status = await checkNostrLoginStatus(challengeId);
            if (status.authenticated) {
                completeLogin(status);
                return;
            }
        } catch (error) {
            console.warn("Nostr 상태 확인 실패, 기본 리다이렉트로 진행합니다.", error);
        }

        completeLogin({
            is_new: false,
            next_url: getNextParam() || defaultNextUrl,
        });
    }

    function completeLogin(verified) {
        if (hasCompletedLogin) {
            return;
        }
        hasCompletedLogin = true;
        stopStatusPolling();
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

    function startStatusPolling(challengeId) {
        if (!challengeId) {
            return;
        }
        stopStatusPolling();
        statusPollingTimer = setInterval(async () => {
            if (hasCompletedLogin) {
                stopStatusPolling();
                return;
            }
            try {
                const status = await checkNostrLoginStatus(challengeId);
                if (status.authenticated) {
                    completeLogin(status);
                }
            } catch (error) {
                console.warn("Nostr 상태 폴링 실패", error);
            }
        }, 2000);
    }

    function stopStatusPolling() {
        if (!statusPollingTimer) {
            return;
        }
        clearInterval(statusPollingTimer);
        statusPollingTimer = null;
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

    async function createBunkerSignerFromURI({ BunkerSigner, pool, clientSecretKey, connectUri }) {
        const errors = [];
        const attempts = [
            () => BunkerSigner.fromURI(
                clientSecretKey,
                connectUri,
                {
                    pool,
                    autoCloseRelays: false,
                },
            ),
            () => BunkerSigner.fromURI(
                pool,
                clientSecretKey,
                connectUri,
                {
                    autoCloseRelays: false,
                },
            ),
        ];

        for (const attempt of attempts) {
            try {
                const signer = await Promise.resolve(attempt());
                if (signer && typeof signer.getPublicKey === "function") {
                    return signer;
                }
            } catch (error) {
                errors.push(error);
            }
        }

        const reason = errors.length
            ? (errors[errors.length - 1]?.message || "알 수 없는 초기화 오류")
            : "fromURI 반환값이 유효하지 않습니다.";
        throw new Error(`Nostr Connect signer 초기화에 실패했습니다: ${reason}`);
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

    async function withTimeout(valueOrPromise, ms, timeoutMessage) {
        let timer = null;
        const promise = Promise.resolve(valueOrPromise);
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

    function cleanupNip46(relayUrls = nip46Relays) {
        stopStatusPolling();
        try {
            if (activeBunkerSigner && typeof activeBunkerSigner.close === "function") {
                activeBunkerSigner.close();
            }
        } catch (error) {
            console.warn("Bunker signer close 실패", error);
        }
        try {
            if (activePool && typeof activePool.close === "function") {
                activePool.close(relayUrls);
            }
        } catch (error) {
            console.warn("NIP-46 relay close 실패", error);
        }
        activeBunkerSigner = null;
        activePool = null;
    }

    function restorePendingNip46Session() {
        const pending = getPendingNip46Session();
        if (pending) {
            currentNostrConnectUri = pending.connectUri;
            activeChallengeId = pending.challenge?.challenge_id || "";
            renderNostrConnectUri(pending.connectUri);
            showNostrConnectPanel();
            if (activeChallengeId) {
                startStatusPolling(activeChallengeId);
            }
            setStatus("pending", "이전 Nostr Connect 연결을 복구 중입니다. 잠시만 기다려 주세요.");
            resumePendingNip46Session();
            return;
        }

        const resumeToken = getResumeTokenFromUrl();
        if (!resumeToken) {
            clearNostrConnectReturnMarker();
            return;
        }

        setStatus("pending", "복귀 토큰으로 로그인 세션을 복구 중입니다...");
        fetchPendingSessionFromServer(resumeToken)
            .then((serverPending) => {
                if (!serverPending) {
                    setStatus("error", "복귀 세션이 만료되었습니다. 다시 로그인해 주세요.");
                    clearNostrConnectReturnMarker();
                    return;
                }
                const connectUriWithCallback = appendNostrConnectCallback(
                    serverPending.connectUri,
                    buildNostrConnectCallbackUrl(resumeToken),
                );
                savePendingNip46Session({
                    ...serverPending,
                    connectUri: connectUriWithCallback,
                    resumeToken,
                });
                restorePendingNip46Session();
            })
            .catch((error) => {
                setStatus("error", error.message || "복귀 세션 복구에 실패했습니다. 다시 시도해 주세요.");
                clearNostrConnectReturnMarker();
            });
    }

    function resumePendingNip46Session() {
        const pending = getPendingNip46Session();
        if (!pending || activeNip46Task) {
            return;
        }
        setStatus("pending", "Nostr Connect 재연결을 시도합니다...");

        beginNip46Login({ usePending: true }).catch((error) => {
            setStatus("error", error.message || "Nostr Connect 재연결에 실패했습니다. 다시 시도해 주세요.");
            startBtn.disabled = false;
            cleanupNip46();
            if ((error.message || "").includes("챌린지")) {
                clearPendingNip46Session();
            }
        });
    }

    function savePendingNip46Session(payload) {
        const storage = getPersistentStorage();
        if (!storage) {
            return;
        }
        try {
            storage.setItem(NIP46_PENDING_STORAGE_KEY, JSON.stringify(payload));
        } catch (error) {
            console.warn("NIP-46 pending 세션 저장 실패", error);
        }
    }

    function getPendingNip46Session() {
        const storage = getPersistentStorage();
        if (!storage) {
            return null;
        }
        try {
            const raw = storage.getItem(NIP46_PENDING_STORAGE_KEY);
            if (!raw) {
                return null;
            }
            const parsed = JSON.parse(raw);
            if (!parsed || !parsed.clientSecretKeyHex || !parsed.connectUri || !parsed.createdAt || !parsed.challenge) {
                clearPendingNip46Session();
                return null;
            }
            if ((Date.now() - Number(parsed.createdAt)) > NIP46_PENDING_MAX_AGE_MS) {
                clearPendingNip46Session();
                return null;
            }
            return parsed;
        } catch (error) {
            clearPendingNip46Session();
            return null;
        }
    }

    function clearPendingNip46Session() {
        const pending = getPendingNip46Session();
        const resumeToken = pending?.resumeToken || getResumeTokenFromUrl();
        if (resumeToken) {
            clearPendingSessionOnServer(resumeToken);
        }
        try {
            if (window.localStorage) {
                window.localStorage.removeItem(NIP46_PENDING_STORAGE_KEY);
            }
            if (window.sessionStorage) {
                window.sessionStorage.removeItem(NIP46_PENDING_STORAGE_KEY);
            }
        } catch (error) {
            console.warn("NIP-46 pending 세션 삭제 실패", error);
        }
        clearNostrConnectReturnMarker();
    }

    function buildNostrConnectCallbackUrl(resumeToken) {
        const url = new URL(window.location.href);
        url.searchParams.set("nostr_connect_return", "1");
        if (resumeToken) {
            url.searchParams.set("nostr_connect_resume", resumeToken);
        }
        return url.toString();
    }

    function appendNostrConnectCallback(connectUri, callbackUrl) {
        if (!connectUri || !callbackUrl || connectUri.includes("callback=")) {
            return connectUri;
        }
        const encodedCallback = encodeURIComponent(callbackUrl);
        return connectUri.includes("?")
            ? `${connectUri}&callback=${encodedCallback}`
            : `${connectUri}?callback=${encodedCallback}`;
    }

    async function createPendingSessionOnServer(pendingPayload) {
        const resumeToken = generateResumeToken();
        const response = await fetch(pendingCreateUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                token: resumeToken,
                pending: pendingPayload,
            }),
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            throw new Error(payload.error || "Nostr 복귀 세션 저장에 실패했습니다.");
        }
        return payload.token || resumeToken;
    }

    async function fetchPendingSessionFromServer(token) {
        const url = new URL(pendingFetchUrl, window.location.origin);
        url.searchParams.set("token", token);
        const response = await fetch(url.toString(), {
            method: "GET",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        });
        const payload = await response.json();
        if (!response.ok || !payload.success) {
            return null;
        }
        return payload.pending || null;
    }

    async function clearPendingSessionOnServer(token) {
        try {
            await fetch(pendingClearUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({ token }),
            });
        } catch (error) {
            console.warn("Nostr pending 세션 서버 정리 실패", error);
        }
    }

    function generateResumeToken() {
        const bytes = new Uint8Array(24);
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

    function isNostrConnectReturnIntent() {
        const params = new URLSearchParams(window.location.search);
        return params.get("nostr_connect_return") === "1";
    }

    function getResumeTokenFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const token = params.get("nostr_connect_resume");
        return token ? token.trim() : "";
    }

    function getPersistentStorage() {
        try {
            if (window.localStorage) {
                return window.localStorage;
            }
        } catch (error) {
            console.warn("localStorage 접근 실패", error);
        }
        try {
            if (window.sessionStorage) {
                return window.sessionStorage;
            }
        } catch (error) {
            console.warn("sessionStorage 접근 실패", error);
        }
        return null;
    }

    function clearNostrConnectReturnMarker() {
        const params = new URLSearchParams(window.location.search);
        if (!params.has("nostr_connect_return") && !params.has("nostr_connect_resume")) {
            return;
        }
        params.delete("nostr_connect_return");
        params.delete("nostr_connect_resume");
        const nextQuery = params.toString();
        const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}${window.location.hash || ""}`;
        window.history.replaceState({}, "", nextUrl);
    }

    function secretKeyToHex(secretKey) {
        if (typeof secretKey === "string") {
            return secretKey.startsWith("0x") ? secretKey.slice(2) : secretKey;
        }
        const bytes = secretKey instanceof Uint8Array ? secretKey : new Uint8Array(secretKey);
        return Array.from(bytes)
            .map((value) => value.toString(16).padStart(2, "0"))
            .join("");
    }

    function secretKeyFromHex(hexValue) {
        const normalized = (hexValue || "").replace(/^0x/, "");
        if (normalized.length % 2 !== 0) {
            throw new Error("Nostr Connect secret key 형식이 올바르지 않습니다.");
        }
        const bytes = new Uint8Array(normalized.length / 2);
        for (let i = 0; i < bytes.length; i += 1) {
            bytes[i] = parseInt(normalized.substr(i * 2, 2), 16);
        }
        return bytes;
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
