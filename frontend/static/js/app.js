(function () {
  const toastEl = document.getElementById("toast");
  let toastTimer = null;

  async function fetchJSON(url, options = {}) {
    const isFormData = options.body instanceof FormData;
    const settings = {
      headers: isFormData ? { ...(options.headers || {}) } : { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    };
    if (settings.body && typeof settings.body !== "string" && !isFormData) {
      settings.body = JSON.stringify(settings.body);
    }

    const response = await fetch(url, settings);
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : {};
    if (!response.ok || data.ok === false) {
      const error = new Error(data.error || "Não foi possível concluir a ação.");
      error.errors = data.errors || {};
      throw error;
    }
    return data;
  }

  function todayISO() {
    const now = new Date();
    const offset = now.getTimezoneOffset();
    return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
  }

  function currentWeekRange() {
    const current = new Date(`${todayISO()}T00:00:00`);
    const day = current.getDay() || 7;
    const start = new Date(current);
    start.setDate(current.getDate() - day + 1);
    const end = new Date(start);
    end.setDate(start.getDate() + 6);
    return { start: toISO(start), end: toISO(end) };
  }

  function toISO(date) {
    const offset = date.getTimezoneOffset();
    return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 10);
  }

  function formatDate(value) {
    if (!value) return "";
    return new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR");
  }

  function formatDateTime(value) {
    if (!value) return "";
    const normalized = String(value).includes("T") ? value : String(value).replace(" ", "T");
    const date = new Date(normalized);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("pt-BR");
  }

  function formatNumber(value, digits = 0) {
    const parsed = Number(value || 0);
    return parsed.toLocaleString("pt-BR", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  }

  function showToast(message, type = "success") {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.dataset.type = type;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), 2600);
  }

  function boolLabel(value) {
    return Number(value) ? "Sim" : "Não";
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function getScoreClass(score) {
    const value = Number(score || 0);
    if (value >= 80) return "badge-success";
    if (value >= 60) return "badge-warning";
    return "badge-danger";
  }

  function formatFileSize(value) {
    const bytes = Number(value || 0);
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${formatNumber(bytes / 1024, 1)} KB`;
    return `${formatNumber(bytes / (1024 * 1024), 1)} MB`;
  }

  function setButtonLoading(button, loading, label) {
    if (!button) return;
    if (loading) {
      button.dataset.originalText = button.textContent;
      button.textContent = label || "Aguarde...";
      button.disabled = true;
      return;
    }
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }

  function clearForm(form) {
    if (!form) return;
    form.reset();
  }

  function confirmAction(message) {
    return window.confirm(message);
  }

  function formToObject(form) {
    const data = {};
    [...form.elements].forEach((element) => {
      if (!element.name) return;
      if (element.type === "checkbox") {
        data[element.name] = element.checked;
      } else {
        data[element.name] = element.value;
      }
    });
    return data;
  }

  async function applySavedSettings() {
    try {
      const data = await fetchJSON("/api/settings");
      const settings = data.settings || {};
      document.documentElement.dataset.theme = settings.theme || "dark";
      const appName = settings.app_name || "Routine IA";
      document.querySelectorAll("[data-app-name]").forEach((element) => {
        element.textContent = appName;
      });
    } catch (error) {
      document.documentElement.dataset.theme = "dark";
    }
  }

  window.Routine = {
    fetchJSON,
    requestJson: fetchJSON,
    todayISO,
    getTodayISO: todayISO,
    currentWeekRange,
    formatDate,
    formatDateTime,
    formatNumber,
    formatFileSize,
    number: formatNumber,
    setText,
    showToast,
    toast: showToast,
    boolLabel,
    escapeHtml,
    getScoreClass,
    setButtonLoading,
    clearForm,
    confirmAction,
    formToObject,
    applySavedSettings,
  };

  applySavedSettings();
})();
