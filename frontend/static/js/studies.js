document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('input[type="date"]').forEach((input) => { input.value = Routine.todayISO(); });
  document.getElementById("study-session-form").addEventListener("submit", submitForm("/api/studies/session", "Sessao registrada."));
  document.getElementById("mock-form").addEventListener("submit", submitForm("/api/studies/mock-exam", "Simulado registrado."));
  document.getElementById("study-error-form").addEventListener("submit", submitForm("/api/studies/errors", "Erro salvo e revisao agendada."));
  document.getElementById("study-review-queue").addEventListener("click", reviewItem);
  loadStudies();
});

function submitForm(url, message) {
  return async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type="submit"]');
    Routine.setButtonLoading(button, true, "Salvando...");
    try {
      await Routine.requestJson(url, { method: "POST", body: Routine.formToObject(form) });
      Routine.toast(message);
      form.reset();
      form.querySelectorAll('input[type="date"]').forEach((input) => { input.value = Routine.todayISO(); });
      await loadStudies();
    } finally {
      Routine.setButtonLoading(button, false);
    }
  };
}

async function loadStudies() {
  const [data, reviewData] = await Promise.all([
    Routine.requestJson("/api/studies"),
    Routine.requestJson(`/api/studies/reviews?date=${Routine.todayISO()}`),
  ]);
  renderSummary(data.summary || {});
  renderSessions(data.sessions || []);
  renderErrors(data.errors || []);
  renderReviews(reviewData.reviews || []);
}

function renderSummary(summary) {
  const entries = [
    ["Horas", Routine.number(summary.total_hours || 0, 1)],
    ["Questoes", summary.questions_done || 0],
    ["Aproveitamento", `${Routine.number(summary.accuracy || 0, 0)}%`],
    ["A revisar", summary.pending_reviews || 0],
  ];
  document.getElementById("study-summary").innerHTML = entries.map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`).join("");
}

function renderSessions(sessions) {
  document.getElementById("study-sessions").innerHTML = sessions.slice(0, 10).map((item) => {
    const accuracy = item.questions_done ? Math.round((Number(item.correct_answers || 0) / Number(item.questions_done)) * 100) : null;
    return `<article class="study-session-row"><div class="study-subject-mark">${Routine.escapeHtml((item.subject || "E").slice(0, 1))}</div><div><strong>${Routine.escapeHtml(item.subject)} · ${Routine.escapeHtml(item.topic || "Sem topico")}</strong><span>${Routine.formatDate(item.date)} · ${item.duration_minutes} min${accuracy === null ? "" : ` · ${accuracy}%`}</span></div><span class="difficulty-level">Nivel ${item.difficulty || 3}</span></article>`;
  }).join("") || `<div class="study-empty">Nenhuma sessao registrada nesta semana.</div>`;
}

function renderErrors(errors) {
  const pending = errors.filter((item) => !Number(item.reviewed));
  document.getElementById("study-errors").innerHTML = pending.slice(0, 5).map((item) => `<article><strong>${Routine.escapeHtml(item.subject)} · ${Routine.escapeHtml(item.topic || "Topico")}</strong><span>${Routine.escapeHtml(item.error_type)} · ${Routine.escapeHtml(item.description || "Sem descricao")}</span></article>`).join("") || `<div class="study-empty">Nenhum ponto pendente.</div>`;
}

function renderReviews(reviews) {
  document.getElementById("review-count").textContent = reviews.length;
  document.getElementById("study-review-queue").innerHTML = reviews.slice(0, 6).map((item) => `<article class="study-review-item"><div><strong>${Routine.escapeHtml(item.subject)} · ${Routine.escapeHtml(item.topic || "Topico")}</strong><span>${Routine.escapeHtml(item.correction || item.description || item.error_type)}</span></div><div class="review-actions"><button data-review="${item.study_error_id}" data-quality="2" type="button">Rever</button><button data-review="${item.study_error_id}" data-quality="4" type="button">Fixei</button></div></article>`).join("") || `<div class="study-empty">Fila de revisao em dia.</div>`;
}

async function reviewItem(event) {
  const button = event.target.closest("[data-review]");
  if (!button) return;
  await Routine.requestJson(`/api/studies/reviews/${button.dataset.review}`, {
    method: "POST",
    body: { quality: Number(button.dataset.quality), date: Routine.todayISO() },
  });
  Routine.toast(button.dataset.quality >= 3 ? "Conteudo reagendado." : "Vamos rever novamente em breve.");
  loadStudies();
}
