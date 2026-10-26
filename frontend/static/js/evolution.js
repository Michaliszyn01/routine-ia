document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("evolution-period").addEventListener("change", loadEvolution);
  loadEvolution();
});
async function loadEvolution() {
  const period = document.getElementById("evolution-period").value;
  const data = await Routine.requestJson(`/api/evolution?period=${period}`);
  Routine.setText("evolution-title", `${data.label} - ${Routine.formatDate(data.start)} a ${Routine.formatDate(data.end)}`);
  const s = data.summary || {};
  document.getElementById("evolution-summary").innerHTML = `<div><span>Score medio</span><strong>${Routine.number(s.average_score || 0,1)}</strong></div><div><span>Estudos</span><strong>${Routine.number(s.study_hours || 0,1)}h</strong></div><div><span>Programacao</span><strong>${Routine.number(s.programming_hours || 0,1)}h</strong></div><div><span>Treinos</span><strong>${s.workouts || 0}</strong></div><div><span>Sono</span><strong>${Routine.number(s.average_sleep || 0,1)}h</strong></div><div><span>Foco</span><strong>${s.focus_sessions || 0}</strong></div>`;
  Routine.setText("evolution-resume", data.month_resume || "");
  document.getElementById("evolution-hours").innerHTML = Object.entries(data.charts?.hours_by_category || {}).map(([name, value]) => `<article class="evolution-item"><strong>${Routine.escapeHtml(name)}</strong><span>${Routine.number(value,1)}h</span></article>`).join("");
  const projects = Object.entries(data.charts?.projects || {}).map(([name, value]) => `<article class="evolution-item"><strong>${Routine.escapeHtml(name)}</strong><span>${Routine.number(value,1)}h</span></article>`).join("");
  const subjects = Object.entries(data.charts?.studies_by_subject || {}).map(([name, value]) => `<article class="evolution-item"><strong>${Routine.escapeHtml(name)}</strong><span>${Routine.number(value,1)}h</span></article>`).join("");
  document.getElementById("evolution-details").innerHTML = projects + subjects || `<p class="muted">Sem detalhes neste periodo.</p>`;
}
