document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("life-goal-form").addEventListener("submit", saveGoal);
  document.getElementById("life-goal-reset").addEventListener("click", resetGoalForm);
  loadGoals();
});
async function loadGoals() {
  const data = await Routine.requestJson("/api/life-goals");
  const summary = data.summary || {};
  document.getElementById("life-goal-summary").innerHTML = `<div><span>Ativos</span><strong>${summary.active_count || 0}</strong></div><div><span>Progresso medio</span><strong>${Routine.number(summary.average_progress || 0, 1)}%</strong></div><div><span>Perto do prazo</span><strong>${summary.due_soon?.length || 0}</strong></div>`;
  document.getElementById("life-goals-list").innerHTML = (data.goals || []).map(goal => `<article class="goal-card-item"><h3>${Routine.escapeHtml(goal.title)}</h3><p>${Routine.escapeHtml(goal.description || "")}</p><div class="progress-track"><span style="width:${Number(goal.progress_percent || 0)}%"></span></div><div class="entity-meta"><span>${Routine.escapeHtml(goal.category)}</span><span>${Routine.escapeHtml(goal.priority)}</span><span>${Routine.escapeHtml(goal.status)}</span><span>${Routine.escapeHtml(goal.linked_area || "sem area")}</span></div><div class="form-actions"><button class="button secondary" data-edit="${goal.id}">Editar</button><button class="button secondary" data-complete="${goal.id}">Concluir</button><button class="button ghost" data-archive="${goal.id}">Arquivar</button></div></article>`).join("") || `<p class="muted">Nenhum objetivo ativo.</p>`;
  document.querySelectorAll("[data-edit]").forEach(btn => btn.addEventListener("click", async () => editGoal(btn.dataset.edit)));
  document.querySelectorAll("[data-complete]").forEach(btn => btn.addEventListener("click", async () => { await Routine.requestJson(`/api/life-goals/${btn.dataset.complete}/complete`, {method:"POST"}); loadGoals(); }));
  document.querySelectorAll("[data-archive]").forEach(btn => btn.addEventListener("click", async () => { await Routine.requestJson(`/api/life-goals/${btn.dataset.archive}/archive`, {method:"POST"}); loadGoals(); }));
}
async function saveGoal(event) {
  event.preventDefault();
  const payload = Routine.formToObject(event.target);
  const goalId = payload.id;
  const url = goalId ? `/api/life-goals/${goalId}` : "/api/life-goals";
  await Routine.requestJson(url, {method:"POST", body: payload});
  resetGoalForm();
  Routine.toast("Objetivo salvo.");
  loadGoals();
}

async function editGoal(goalId) {
  const data = await Routine.requestJson(`/api/life-goals/${goalId}`);
  const goal = data.goal || {};
  const form = document.getElementById("life-goal-form");
  Object.entries(goal).forEach(([key, value]) => {
    const field = form.elements[key];
    if (field) field.value = value ?? "";
  });
  Routine.setText("life-goal-form-title", "Editar objetivo");
  form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetGoalForm() {
  const form = document.getElementById("life-goal-form");
  Routine.clearForm(form);
  form.elements.id.value = "";
  form.elements.priority.value = "media";
  form.elements.status.value = "ativo";
  form.elements.progress_percent.value = 0;
  Routine.setText("life-goal-form-title", "Novo objetivo");
}
