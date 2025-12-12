(() => {
  const endpointsDataEl = document.getElementById("api-endpoints-data");
  if (!endpointsDataEl) return;

  const endpoints = JSON.parse(endpointsDataEl.textContent);
  const listEl = document.getElementById("api-endpoint-list");
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

  function renderEndpointList() {
    listEl.innerHTML = "";
    endpoints.forEach((ep, idx) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "endpoint-item";
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", "false");
      item.innerHTML = `
        <div class="method-badge">${ep.method}</div>
        <div class="text-left">
          <p class="text-sm font-semibold text-gray-900 dark:text-white">${ep.name}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400">${ep.path}</p>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">${ep.description}</p>
        </div>
      `;
      item.addEventListener("click", () => {
        document.querySelectorAll(".endpoint-item").forEach((el) => {
          el.classList.remove("active");
          el.setAttribute("aria-selected", "false");
        });
        item.classList.add("active");
        item.setAttribute("aria-selected", "true");
        selectedEndpoint = ep;
        selectedLabelEl.textContent = `${ep.method} ${ep.path}`;
        fetchEndpoint();
      });
      if (idx === 0) {
        item.classList.add("active");
        item.setAttribute("aria-selected", "true");
        selectedEndpoint = ep;
        selectedLabelEl.textContent = `${ep.method} ${ep.path}`;
      }
      listEl.appendChild(item);
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

  renderEndpointList();
  fetchEndpoint();
})();
