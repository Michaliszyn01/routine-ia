let analyticsPeriod = 7;

document.addEventListener("DOMContentLoaded", () => {
  bindAnalyticsPeriodButtons();
  loadAnalytics().catch((error) => Routine.toast(error.message, "danger"));
});

function bindAnalyticsPeriodButtons() {
  document.querySelectorAll(".analytics-period").forEach((button) => {
    button.addEventListener("click", () => {
      analyticsPeriod = Number(button.dataset.period || 7);
      document.querySelectorAll(".analytics-period").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      loadAnalytics().catch((error) => Routine.toast(error.message, "danger"));
    });
  });
}

async function loadAnalytics() {
  const data = await Routine.requestJson(`/api/routine-analytics?period=${analyticsPeriod}`);
  renderAnalytics(data);
}

function renderAnalytics(data) {
  const summary = data.summary || {};
  Routine.setText("analytics-range", `${formatDateBR(data.start_date)} ate ${formatDateBR(data.end_date)}`);
  Routine.setText("analytics-data-count", `${summary.days_with_any_data || 0}/${data.period_days || analyticsPeriod} dias`);
  Routine.setText("analytics-safety", data.safety_note || "Os dados sao pistas de rotina e bem-estar. O Routine IA nao faz diagnostico medico.");
  Routine.setText("analytics-sleep", summary.average_sleep_hours ? `${Routine.number(summary.average_sleep_hours, 1)}h` : "-");
  Routine.setText("analytics-sleep-days", `${summary.good_sleep_days || 0} dias com sono bom`);
  Routine.setText("analytics-productive", formatMinutes(summary.average_productive_minutes));
  Routine.setText("analytics-risk", formatMinutes(summary.average_risk_minutes));
  Routine.setText("analytics-combined", Routine.number(summary.combined_good_days || 0));
  renderInsights(data.insights || []);
  renderTrends(data.trends || []);
  renderCorrelations(data.correlations || []);
  renderDailyRows(data.daily || []);
}

function renderInsights(insights) {
  const target = document.getElementById("analytics-insights");
  target.innerHTML = insights.length
    ? insights.map((item) => `
      <article class="analytics-insight" data-level="${Routine.escapeHtml(item.level || "info")}">
        <strong>${Routine.escapeHtml(item.title || "Insight")}</strong>
        <p>${Routine.escapeHtml(item.message || "")}</p>
      </article>
    `).join("")
    : `<p class="muted">Sem insights simples ainda.</p>`;
}

function renderTrends(trends) {
  const target = document.getElementById("analytics-trends");
  target.innerHTML = trends.length
    ? trends.map((trend) => {
      const delta = Number(trend.delta || 0);
      const sign = delta > 0 ? "+" : "";
      return `
        <div class="analytics-trend-row" data-direction="${Routine.escapeHtml(trend.direction || "stable")}">
          <span>${Routine.escapeHtml(trend.label || "-")}</span>
          <strong>${sign}${formatTrendValue(delta, trend.unit)}</strong>
          <small>${formatTrendValue(trend.first_half_average, trend.unit)} -> ${formatTrendValue(trend.second_half_average, trend.unit)}</small>
        </div>
      `;
    }).join("")
    : `<p class="muted">Tendencias aparecem com pelo menos quatro dias no periodo.</p>`;
}

function renderCorrelations(correlations) {
  const target = document.getElementById("analytics-correlations");
  target.innerHTML = correlations.map((item) => `
    <article class="analytics-correlation-card">
      <span>${Routine.escapeHtml(item.label || "-")}</span>
      <strong>${formatCorrelation(item.value)}</strong>
      <small>${Routine.escapeHtml(item.strength || "sem sinal")} · ${Routine.escapeHtml(item.direction || "neutra")} · ${item.sample_size || 0} amostras</small>
    </article>
  `).join("") || `<p class="muted">Sem dados suficientes para correlacoes.</p>`;
}

function renderDailyRows(rows) {
  const body = document.getElementById("analytics-daily-body");
  body.innerHTML = rows.length
    ? rows.map((row) => `
      <tr>
        <td>${formatDateBR(row.date)}</td>
        <td>${row.sleep_hours ? `${Routine.number(row.sleep_hours, 1)}h` : "-"}</td>
        <td>${row.trained ? formatMinutes(row.workout_minutes) : "-"}</td>
        <td>${row.steps ? Routine.number(row.steps) : "-"}</td>
        <td>${row.has_pc_data ? formatMinutes(row.productive_minutes) : "-"}</td>
        <td>${row.has_pc_data ? formatMinutes(row.risk_minutes) : "-"}</td>
        <td>${row.has_daily_record ? Routine.number(row.routine_score, 1) : "-"}</td>
        <td>${renderSignals(row)}</td>
      </tr>
    `).join("")
    : `<tr><td colspan="8" class="muted">Nenhum dado combinado encontrado.</td></tr>`;
}

function renderSignals(row) {
  const signals = [];
  if (row.good_sleep) signals.push("sono bom");
  if (row.short_sleep) signals.push("sono curto");
  if (row.trained) signals.push("treino");
  if (row.focus_good) signals.push("foco");
  if (row.risk_high) signals.push("risco alto");
  return signals.length ? signals.map((label) => `<span class="mini-badge">${Routine.escapeHtml(label)}</span>`).join(" ") : "-";
}

function formatMinutes(value) {
  const minutes = Number(value || 0);
  if (!minutes) return "-";
  if (minutes >= 60) return `${Routine.number(minutes / 60, 1)}h`;
  return `${Routine.number(minutes, 0)}min`;
}

function formatDateBR(value) {
  if (!value) return "-";
  const parts = String(value).split("-");
  if (parts.length === 3) return `${parts[2]}/${parts[1]}`;
  return Routine.formatDate(value) || "-";
}

function formatCorrelation(value) {
  const number = Number(value || 0);
  return number ? Routine.number(number, 2) : "0";
}

function formatTrendValue(value, unit) {
  const number = Number(value || 0);
  if (unit === "h") return `${Routine.number(number, 1)}h`;
  if (unit === "min") return `${Routine.number(number, 0)}min`;
  if (unit === "pts") return `${Routine.number(number, 1)} pts`;
  return Routine.number(number, 0);
}

