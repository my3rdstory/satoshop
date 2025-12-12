(() => {
  const endpointsDataEl = document.getElementById("api-endpoints-data");
  if (!endpointsDataEl) return;

  const endpoints = JSON.parse(endpointsDataEl.textContent);
  const selectEl = document.getElementById("endpoint-select");
  const responseBodyEl = document.getElementById("response-body");
  const responseStatusEl = document.getElementById("response-status");
  const selectedLabelEl = document.getElementById("selected-endpoint-label");
  const apiKeyInput = document.getElementById("api-key");
  const baseUrlInput = document.getElementById("api-base-url");
  const refreshBtn = document.getElementById("refresh-response");
  const copyCurlBtn = document.getElementById("copy-curl");
  const toggleKeyBtn = document.getElementById("toggle-key-visibility");
  const rapidocEl = document.getElementById("rapidoc");

  let selectedEndpoint = null;

  function renderEndpointSelect() {
    if (!selectEl) return;
    selectEl.innerHTML = "";
    endpoints.forEach((ep, idx) => {
      const opt = document.createElement("option");
      opt.value = idx.toString();
      opt.textContent = `${ep.method} ${ep.path} — ${ep.name}`;
      selectEl.appendChild(opt);
    });
    selectedEndpoint = endpoints[0];
    selectedLabelEl.textContent = `${selectedEndpoint.method} ${selectedEndpoint.path}`;
    selectEl.addEventListener("change", (e) => {
      const idx = Number(e.target.value);
      selectedEndpoint = endpoints[idx];
      selectedLabelEl.textContent = `${selectedEndpoint.method} ${selectedEndpoint.path}`;
      fetchEndpoint();
    });
  }

  function buildUrl(ep) {
    try {
      const base = baseUrlInput.value || "/api/v1/";
      return new URL(ep.path, base).toString();
    } catch (e) {
      return ep.path;
    }
  }

  function setLoading() {
    responseStatusEl.textContent = "로딩 중...";
    responseBodyEl.textContent = "";
    refreshBtn.disabled = true;
    copyCurlBtn.disabled = true;
  }

  function showResult(status, body) {
    responseStatusEl.textContent = status;
    responseBodyEl.textContent = typeof body === "string" ? body : JSON.stringify(body, null, 2);
    refreshBtn.disabled = false;
    copyCurlBtn.disabled = false;
  }

  async function fetchEndpoint() {
    if (!selectedEndpoint) return;
    setLoading();
    const url = buildUrl(selectedEndpoint);
    const headers = {};
    const apiKey = apiKeyInput.value.trim();
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    try {
      const res = await fetch(url, { headers });
      const text = await res.text();
      let data = text;
      try {
        data = JSON.parse(text);
      } catch (_) {
        // keep text
      }
      showResult(`${res.status} ${res.statusText}`, data);
    } catch (err) {
      showResult("네트워크 오류", err.message || String(err));
    }
  }

  function updateCurl() {
    if (!selectedEndpoint) return "";
    const url = buildUrl(selectedEndpoint);
    const apiKey = apiKeyInput.value.trim();
    const parts = [
      "curl",
      "-X", selectedEndpoint.method,
    ];
    if (apiKey) {
      parts.push("-H", `"Authorization: Bearer ${apiKey}"`);
    }
    parts.push(`"${url}"`);
    return parts.join(" ");
  }

  refreshBtn?.addEventListener("click", fetchEndpoint);

  copyCurlBtn?.addEventListener("click", async () => {
    const cmd = updateCurl();
    try {
      await navigator.clipboard.writeText(cmd);
      copyCurlBtn.textContent = "복사됨";
      setTimeout(() => (copyCurlBtn.textContent = "curl 복사"), 1500);
    } catch (_) {
      copyCurlBtn.textContent = "복사 실패";
      setTimeout(() => (copyCurlBtn.textContent = "curl 복사"), 1500);
    }
  });

  apiKeyInput?.addEventListener("input", () => {
    copyCurlBtn.disabled = !apiKeyInput.value.trim();
  });

  toggleKeyBtn?.addEventListener("click", () => {
    if (!apiKeyInput) return;
    apiKeyInput.type = apiKeyInput.type === "password" ? "text" : "password";
    toggleKeyBtn.textContent = apiKeyInput.type === "password" ? "표시" : "숨김";
  });

  // Sync RapiDoc theme with current mode
  const html = document.documentElement;
  if (rapidocEl) {
    const applyTheme = () => {
      const isDark = html.classList.contains("dark");
      rapidocEl.setAttribute("theme", isDark ? "dark" : "light");
    };
    applyTheme();
    const observer = new MutationObserver(applyTheme);
    observer.observe(html, { attributes: true, attributeFilter: ["class"] });
  }

  renderEndpointSelect();
  fetchEndpoint();
})();
