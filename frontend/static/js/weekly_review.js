let currentReview = null;

document.addEventListener("DOMContentLoaded", () => {
  renderReviewShell();
  bindReviewMvp();
  loadReview("/api/weekly-review/current").catch((error) => Routine.toast(error.message, "danger"));
});

function renderReviewShell() {
  const content = document.querySelector(".content");
  if (!content) return;
  content.innerHTML = `
    <section class="page-intro mvp-intro">
      <h1>Revisão</h1>
      <p>O objetivo é achar o padrão que está repetindo e escolher a próxima regra.</p>
    </section>

    <section class="panel mvp-review-hero">
      <div class="panel-heading">
        <div>
          <h2 id="review-period-title">Revisão semanal</h2>
          <p id="review-message" class="muted">Carregando dados...</p>
        </div>
        <div class="form-actions">
          <button class="button secondary" id="review-current-period" type="button">Semana atual</button>
          <button class="button ghost" id="review-previous-period" type="button">Semana anterior</button>
          <button class="button ghost" id="review-last7-period" type="button">Últimos 7 dias</button>
        </div>
      </div>
      <div id="review-action-summary" class="mvp-review-grid"></div>
    </section>

    <section class="mvp-layout review-mvp-layout">
      <article class="panel mvp-alert-panel">
        <div class="panel-heading"><h2>Principal alerta</h2></div>
        <p id="review-main-alert">Ainda sem dados suficientes.</p>
      </article>
      <article class="panel mvp-alert-panel">
        <div class="panel-heading"><h2>Próxima regra da semana</h2></div>
        <p id="review-next-rule">Registrar o mínimo por alguns dias.</p>
      </article>
    </section>

    <details class="panel mvp-secondary-links">
      <summary>Reflexão salva e telas antigas</summary>
      <form id="weekly-review-form" class="mvp-reflection-form">
        <input name="week_start" id="review-week-hidden" type="hidden">
        <label><span>O que funcionou?</span><textarea name="what_worked" rows="2"></textarea></label>
        <label><span>O que atrapalhou?</span><textarea name="what_failed" rows="2"></textarea></label>
        <label><span>Ajuste da próxima semana</span><textarea name="next_week_adjustment" rows="2"></textarea></label>
        <button class="button primary" type="submit">Salvar reflexão</button>
      </form>
      <div id="review-current" class="mvp-saved-review"></div>
    </details>
  `;
}

function bindReviewMvp() {
  field("review-current-period").addEventListener("click", () => loadReview("/api/weekly-review/current"));
  field("review-previous-period").addEventListener("click", () => loadReview("/api/weekly-review/previous"));
  field("review-last7-period").addEventListener("click", loadLast7);
  field("weekly-review-form").addEventListener("submit", saveReview);
}

async function loadLast7() {
  const end = Routine.todayISO();
  const startDate = new Date(`${end}T00:00:00`);
  startDate.setDate(startDate.getDate() - 6);
  await loadReview(`/api/weekly-review/range?start=${startDate.toISOString().slice(0, 10)}&end=${end}`);
}

async function loadReview(url) {
  const data = await Routine.requestJson(url);
  renderReview(data);
}

function renderReview(data) {
  currentReview = data;
  const period = data.period || {};
  const summary = data.action_summary || {};
  Routine.setText(
    "review-period-title",
    `${period.label || "Período"} - ${Routine.formatDate(data.week_start)} a ${Routine.formatDate(data.week_end)}`
  );
  Routine.setText("review-message", data.message || "Resumo simples da semana.");
  field("review-week-hidden").value = data.week_start || "";
  field("review-action-summary").innerHTML = `
    ${metric("Dias com ENEM feito", summary.enem_days || 0)}
    ${metric("Dias com 3 chaves", summary.three_key_days || 0)}
    ${metric("Jogo antes do estudo", summary.game_before_study_days || 0)}
    ${metric("Jogo médio", `${Routine.number(summary.average_game_hours || 0, 1)}h`)}
    ${metric("Sem refeição decente", summary.days_without_decent_meal || 0)}
  `;
  Routine.setText("review-main-alert", summary.main_alert || "Ainda sem dados suficientes.");
  Routine.setText("review-next-rule", summary.next_week_rule || "Registrar o mínimo por alguns dias.");
  renderSavedReview(data.review);
}

function renderSavedReview(review) {
  document.querySelectorAll("#weekly-review-form [name]").forEach((input) => {
    if (input.type !== "hidden") input.value = "";
  });
  if (review) {
    Object.entries(review).forEach(([key, value]) => {
      const input = document.querySelector(`#weekly-review-form [name="${key}"]`);
      if (input) input.value = value || "";
    });
  }
  field("review-current").innerHTML = review
    ? `<p><strong>Ajuste salvo:</strong> ${Routine.escapeHtml(review.next_week_adjustment || "")}</p>`
    : `<p class="muted">Nenhuma reflexão salva para este período.</p>`;
}

async function saveReview(event) {
  event.preventDefault();
  await Routine.requestJson("/api/weekly-review", {
    method: "POST",
    body: Routine.formToObject(event.target),
  });
  Routine.toast("Revisão salva.");
  if (currentReview) await loadReview(`/api/weekly-review?week_start=${encodeURIComponent(currentReview.week_start)}`);
}

function metric(label, value) {
  return `<article><span>${Routine.escapeHtml(label)}</span><strong>${Routine.escapeHtml(value)}</strong></article>`;
}

function field(id) {
  return document.getElementById(id);
}
