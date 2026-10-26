document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("habit-form").addEventListener("submit", saveHabit);
  loadHabits();
});
async function loadHabits() {
  const data = await Routine.requestJson("/api/habits");
  const summary = data.summary || {};
  document.getElementById("habit-summary").innerHTML = `<div><span>Ativos</span><strong>${summary.active_count || 0}</strong></div><div><span>Semana</span><strong>${summary.completed_this_week || 0}</strong></div><div><span>Melhor</span><strong>${Routine.escapeHtml(summary.best_habit?.name || "-")}</strong></div>`;
  document.getElementById("habit-list").innerHTML = (data.habits || []).map(habit => `<article class="habit-item"><h3>${Routine.escapeHtml(habit.name)}</h3><p>${Routine.escapeHtml(habit.description || "")}</p><div class="entity-meta"><span>${Routine.escapeHtml(habit.category)}</span><span>${Routine.escapeHtml(habit.frequency)}</span><span>${habit.target_per_week}/semana</span></div><div class="form-actions"><button class="button secondary" data-log="${habit.id}">Marcar hoje</button><button class="button ghost" data-archive="${habit.id}">Arquivar</button></div></article>`).join("") || `<p class="muted">Nenhum habito cadastrado.</p>`;
  document.querySelectorAll("[data-log]").forEach(btn => btn.addEventListener("click", async () => { await Routine.requestJson("/api/habits/log", {method:"POST", body:{habit_id:btn.dataset.log, date:Routine.todayISO(), completed:true}}); Routine.toast("Habito marcado."); loadHabits(); }));
  document.querySelectorAll("[data-archive]").forEach(btn => btn.addEventListener("click", async () => { await Routine.requestJson(`/api/habits/${btn.dataset.archive}/archive`, {method:"POST"}); loadHabits(); }));
}
async function saveHabit(event) {
  event.preventDefault();
  await Routine.requestJson("/api/habits", {method:"POST", body: Routine.formToObject(event.target)});
  Routine.clearForm(event.target);
  Routine.toast("Habito salvo.");
  loadHabits();
}
