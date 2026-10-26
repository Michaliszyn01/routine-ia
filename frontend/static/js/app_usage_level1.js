const usageCharts = {};

document.addEventListener("DOMContentLoaded", () => {
  bindUsageActions();
  refreshUsagePage().catch((error) => Routine.toast(error.message, "danger"));
  window.setInterval(refreshUsagePage, 10000);
});

function bindUsageActions() {
  document.getElementById("monitor-start").addEventListener("click", () => monitorAction("/api/monitoring-level1/start"));
  document.getElementById("monitor-pause").addEventListener("click", () => monitorAction("/api/monitoring-level1/pause"));
  document.getElementById("monitor-resume").addEventListener("click", () => monitorAction("/api/monitoring-level1/resume"));
  document.getElementById("monitor-stop").addEventListener("click", () => monitorAction("/api/monitoring-level1/stop"));
  document.getElementById("monitor-tick").addEventListener("click", async () => {
    await Routine.requestJson("/api/monitoring-level1/tick", { method: "POST", body: { interval_seconds: 60 } });
    Routine.toast("Uso registrado.");
    refreshUsagePage();
  });
  document.querySelectorAll("[data-delete-scope]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!Routine.confirmAction("Apagar dados de uso do PC? Esta acao nao remove outros dados do app.")) return;
      await Routine.requestJson("/api/monitoring-level1/delete-data", { method: "POST", body: { scope: button.dataset.deleteScope } });
      Routine.toast("Dados de uso removidos.");
      refreshUsagePage();
    });
  });
}

async function monitorAction(url, body = {}) {
  const result = await Routine.requestJson(url, { method: "POST", body });
  renderStatus(result);
  Routine.toast("Status atualizado.");
}

async function refreshUsagePage() {
  const [status, summary, week] = await Promise.all([
    Routine.requestJson("/api/monitoring-level1/status"),
    Routine.requestJson("/api/monitoring-level1/summary"),
    Routine.requestJson("/api/monitoring-level1/week"),
  ]);
  renderStatus(status);
  renderSummary(summary);
  renderFocusedApp(status.focused_app || null);
  renderOpenApps(status.open_apps || []);
  renderDailyList(summary.by_category || [], summary.by_app || []);
  renderUsageCharts(summary, week);
}

function renderStatus(status) {
  const target = document.getElementById("monitor-status");
  const label = status.status || "off";
  const labels = { active: "ativo", starting: "iniciando", paused: "pausado", error: "erro", off: "desligado", worker_off: "worker iniciando" };
  target.className = `monitor-status status-${label}`;
  target.textContent = labels[label] || label;
  if (status.last_error) target.title = status.last_error;
  const worker = status.worker?.worker || {};
  const workerLabel = status.background_mode
    ? worker.running
      ? `Worker ativo: ${Routine.formatDateTime(worker.heartbeat_at || "") || "agora"}`
      : "Worker em segundo plano aguardando heartbeat"
    : "Modo local da interface";
  Routine.setText("monitor-detail", `Intervalo: ${status.interval_seconds || 60}s. Ultima leitura: ${Routine.formatDateTime(status.last_scan_at || "") || "-"}. ${workerLabel}.`);
  renderFocusedApp(status.focused_app || null);
}

function renderSummary(summary) {
  Routine.setText("usage-total", formatMinutes(summary.total_minutes));
  Routine.setText("usage-apps", `${summary.apps_count || 0} apps`);
  Routine.setText("usage-productive", formatMinutes(summary.productive_minutes));
  Routine.setText("usage-risk", formatMinutes(summary.risk_minutes));
  Routine.setText("usage-score", Routine.number(summary.score || 0, 1));
  Routine.setText("usage-result", summary.result || "Sem dados.");
  Routine.setText("usage-top-category", summary.top_category?.label || "-");
  Routine.setText("usage-top-category-time", formatMinutes(summary.top_category?.minutes || 0));
}

function renderFocusedApp(app) {
  Routine.setText("focused-app", app?.app_name || "-");
  Routine.setText(
    "focused-process",
    app ? `${app.process_name || "processo"} - ${app.label || "Neutro"}` : "aguardando leitura"
  );
}

function renderOpenApps(apps) {
  const target = document.getElementById("open-apps-list");
  target.innerHTML = apps.map((app) => `
    <article class="rule-card">
      <div class="entity-meta"><span>${Routine.escapeHtml(app.process_name || "-")}</span><span>${Number(app.window_count || 1)} janela(s)</span></div>
      <h3>${Routine.escapeHtml(app.app_name || app.process_name || "App")}</h3>
      <p><span class="app-badge">${Routine.escapeHtml(app.label || "Neutro")}</span></p>
      ${app.context ? `<p class="muted">${Routine.escapeHtml(app.context)}</p>` : ""}
    </article>
  `).join("") || `<p class="muted">Nenhum app relevante detectado na ultima leitura.</p>`;
}

function renderDailyList(categories, apps) {
  const target = document.getElementById("usage-daily-list");
  target.innerHTML = categories.map((category) => {
    const children = apps.filter((app) => app.category === category.label);
    const rows = children.map((app) => `<li>${Routine.escapeHtml(app.app_name)}: ${formatMinutes(app.minutes)}</li>`).join("");
    return `<div><h3>${Routine.escapeHtml(category.label)}</h3><ul class="plain-list">${rows}</ul></div>`;
  }).join("") || `<p class="muted">Sem dados registrados hoje.</p>`;
}

function renderUsageCharts(summary, week) {
  drawUsageChart("usage-app-chart", "bar", summary.by_app || []);
  drawUsageChart("usage-category-chart", "bar", summary.by_category || []);
  drawUsageChart("usage-week-chart", "bar", week.by_day || []);
}

function drawUsageChart(id, type, rows) {
  const canvas = document.getElementById(id);
  if (!canvas || !window.Chart) return;
  if (usageCharts[id]) usageCharts[id].destroy();
  const styles = getComputedStyle(document.documentElement);
  const colors = {
    accent: styles.getPropertyValue("--app-accent").trim() || "#38b99b",
    blue: styles.getPropertyValue("--app-blue").trim() || "#73a2f5",
    amber: styles.getPropertyValue("--app-amber").trim() || "#e1a451",
    red: styles.getPropertyValue("--app-red").trim() || "#ed7d76",
    muted: styles.getPropertyValue("--app-muted").trim() || "#9caab1",
    surface: styles.getPropertyValue("--app-surface").trim() || "#182126",
    border: styles.getPropertyValue("--app-border").trim() || "#2e3b42",
  };
  usageCharts[id] = new Chart(canvas, {
    type,
    data: {
      labels: rows.map((row) => row.label),
      datasets: [{
        label: "Minutos",
        data: rows.map((row) => row.minutes),
        backgroundColor: [colors.accent, colors.blue, colors.amber, colors.red, colors.muted],
        borderColor: colors.surface,
        borderWidth: 1,
        borderRadius: type === "bar" ? 7 : 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: colors.muted } } },
      scales: type === "bar" ? {
        x: { ticks: { color: colors.muted }, grid: { color: colors.border } },
        y: { beginAtZero: true, ticks: { color: colors.muted }, grid: { color: colors.border } },
      } : {},
    },
  });
}

function formatMinutes(minutes) {
  const value = Number(minutes || 0);
  if (value >= 60) return `${Routine.number(value / 60, 1)}h`;
  return `${Routine.number(value, 0)}min`;
}
