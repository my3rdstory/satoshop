document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("nostrLoginRoot");
    const startBtn = document.getElementById("startNostrLoginBtn");
    const statusEl = document.getElementById("nostrStatus");

    if (!root || !startBtn || !statusEl) {
        return;
    }

    const challengeUrl = root.dataset.challengeUrl || "/accounts/nostr-auth-challenge/";
    const verifyUrl = root.dataset.verifyUrl || "/accounts/nostr-auth-verify/";
    const defaultNextUrl = root.dataset.defaultNext || "/accounts/mypage/";

    startBtn.addEventListener("click", async () => {
        startBtn.disabled = true;
        setStatus("pending", "Nostr 확장 지갑 연결을 확인 중입니다...");

        try {
            if (!window.nostr || typeof window.nostr.getPublicKey !== "function" || typeof window.nostr.signEvent !== "function") {
                throw new Error("NIP-07 지원 Nostr 확장을 찾을 수 없습니다. 확장을 설치하거나 활성화해 주세요.");
            }

            const pubkey = await window.nostr.getPublicKey();
            setStatus("pending", "로그인 챌린지를 생성하고 있습니다...");
            const challenge = await fetchLoginChallenge(pubkey);

            const loginEvent = {
                kind: challenge.kind || 22242,
                created_at: Math.floor(Date.now() / 1000),
                tags: [
                    ["challenge", challenge.challenge],
                    ["domain", challenge.domain || window.location.host],
                ],
                content: "SatoShop Nostr login",
            };

            setStatus("pending", "Nostr 확장에서 서명을 승인해 주세요...");
            const signedEvent = await window.nostr.signEvent(loginEvent);

            setStatus("pending", "서명을 검증하고 로그인 중입니다...");
            const verified = await verifyLoginSignature({
                challengeId: challenge.challenge_id,
                pubkey,
                event: signedEvent,
            });

            setStatus("success", verified.is_new ? "새 계정이 생성되어 로그인되었습니다. 이동합니다..." : "로그인이 완료되었습니다. 이동합니다...");
            const nextUrl = verified.next_url || getNextParam() || defaultNextUrl;
            setTimeout(() => {
                window.location.href = nextUrl;
            }, 800);
        } catch (error) {
            setStatus("error", error.message || "Nostr 로그인 중 오류가 발생했습니다.");
            startBtn.disabled = false;
        }
    });

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
