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
  const paramsContainer = document.createElement("div");
  paramsContainer.className = "grid grid-cols-1 md:grid-cols-2 gap-3";

  let selectedEndpoint = null;
  let paramValues = {};

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
      renderParams();
      fetchEndpoint();
    });
    renderParams();
  }

  function renderParams() {
    if (!paramsContainer || !selectedEndpoint) return;
    paramsContainer.innerHTML = "";
    paramValues = {};
    const target = document.getElementById("param-slot");
    if (!target) return;
    if (!selectedEndpoint.params || selectedEndpoint.params.length === 0) {
      target.innerHTML = "";
      return;
    }
    selectedEndpoint.params.forEach((p) => {
      const wrap = document.createElement("div");
      wrap.className = "flex flex-col gap-1";
      const label = document.createElement("label");
      label.className = "text-sm text-gray-600 dark:text-gray-300";
      label.textContent = p.label || p.name;
      const input = document.createElement("input");
      input.type = "text";
      input.className = "input-control";
      input.value = p.default || "";
      input.placeholder = p.placeholder || "";
      input.addEventListener("input", () => {
        paramValues[p.name] = input.value.trim();
      });
      paramValues[p.name] = input.value.trim();
      wrap.appendChild(label);
      wrap.appendChild(input);
      paramsContainer.appendChild(wrap);
    });
    target.innerHTML = "";
    target.appendChild(paramsContainer);
  }

  function buildUrl(ep) {
    try {
      const base = baseUrlInput.value || "/api/v1/";
      let path = ep.path;
      if (ep.params && ep.params.length > 0) {
        ep.params.forEach((p) => {
          const val = encodeURIComponent(paramValues[p.name] || "");
          path = path.replace(`{${p.name}}`, val);
        });
      }
      return new URL(path, base).toString();
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

  renderEndpointSelect();
  fetchEndpoint();
})();
