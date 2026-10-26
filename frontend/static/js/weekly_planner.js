let plannerItems = [];
let plannerProjects = [];
let plannerGoals = [];

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("planner-week").value = Routine.currentWeekRange().start;
  document.getElementById("planner-week").addEventListener("change", loadPlanner);
  document.getElementById("generate-plan").addEventListener("click", generatePlan);
  document.getElementById("save-plan").addEventListener("click", savePlan);
  bootstrapPlanner().catch((error) => Routine.toast(error.message, "danger"));
});

async function bootstrapPlanner() {
  const [projectsData, goalsData] = await Promise.all([
    Routine.requestJson("/api/projects"),
    Routine.requestJson("/api/life-goals"),
  ]);
  plannerProjects = projectsData.projects || [];
  plannerGoals = goalsData.goals || [];
  await loadPlanner();
}

async function loadPlanner() {
  const week = document.getElementById("planner-week").value;
  const data = await Routine.requestJson(`/api/weekly-planner?week_start=${week}`);
  const source = data.plan ? data : data.suggestion;
  plannerItems = source.items || [];
  renderPlanner(source, Boolean(data.plan));
}
async function generatePlan() {
  const week = document.getElementById("planner-week").value;
  const data = await Routine.requestJson("/api/weekly-planner/generate", {method:"POST", body:{week_start:week}});
  plannerItems = data.plan.items || [];
  renderPlanner(data.plan, false);
}
async function savePlan() {
  collectPlannerEdits();
  const week = document.getElementById("planner-week").value;
  await Routine.requestJson("/api/weekly-planner/save", {method:"POST", body:{week_start:week, generated_by:"rules-v3", title:`Plano semanal ${week}`, items: plannerItems}});
  Routine.toast("Plano salvo.");
  loadPlanner();
}
function renderPlanner(plan, saved) {
  Routine.setText("planner-title", saved ? `${plan.plan.title}` : "Sugestao editavel");
  const context = plan.context || {};
  document.getElementById("planner-context").innerHTML = `<div><span>Energia</span><strong>${Routine.number(context.average_energy || 0,1)}</strong></div><div><span>Sono</span><strong>${Routine.number(context.average_sleep || 0,1)}h</strong></div><div><span>Modo</span><strong>${Routine.escapeHtml(context.mode || "salvo")}</strong></div>`;
  document.getElementById("planner-items").innerHTML = plannerItems.map((item, index) => renderPlannerItem(item, index)).join("");
  document.querySelectorAll("[data-planner-complete]").forEach(input => input.addEventListener("change", async () => {
    const index = Number(input.dataset.index);
    plannerItems[index].completed = input.checked ? 1 : 0;
    if (input.dataset.plannerComplete) {
      await Routine.requestJson("/api/weekly-planner/complete-item", {method:"POST", body:{item_id:input.dataset.plannerComplete, completed:input.checked}});
    }
  }));
}

function renderPlannerItem(item, index) {
  return `
    <article class="planner-item planner-item-expanded">
      <div class="planner-item-head">
        <label><span>Data</span><input type="date" data-planner-field="date" data-index="${index}" value="${Routine.escapeHtml(item.date || "")}"></label>
        <label><span>Categoria</span><select data-planner-field="category" data-index="${index}">${categoryOptions(item.category)}</select></label>
        <label class="planner-check"><span>Concluido</span><input type="checkbox" data-planner-complete="${item.id || ""}" data-index="${index}" ${Number(item.completed || 0) ? "checked" : ""}></label>
      </div>
      <div class="planner-item-main">
        <label><span>Titulo</span><input type="text" data-planner-field="title" data-index="${index}" value="${Routine.escapeHtml(item.title || "")}"></label>
        <label><span>Minutos</span><input type="number" min="0" max="1440" data-planner-field="estimated_minutes" data-index="${index}" value="${Number(item.estimated_minutes || 0)}"></label>
      </div>
      <div class="planner-item-links">
        <label><span>Projeto</span><select data-planner-field="linked_project_id" data-index="${index}">${projectOptions(item.linked_project_id)}</select></label>
        <label><span>Objetivo</span><select data-planner-field="linked_goal_id" data-index="${index}">${goalOptions(item.linked_goal_id)}</select></label>
      </div>
      <label><span>Nota</span><input type="text" data-planner-field="note" data-index="${index}" value="${Routine.escapeHtml(item.note || "")}"></label>
    </article>
  `;
}

function collectPlannerEdits() {
  document.querySelectorAll("[data-planner-field]").forEach((input) => {
    const index = Number(input.dataset.index);
    const field = input.dataset.plannerField;
    if (!plannerItems[index] || !field) return;
    plannerItems[index][field] = field === "estimated_minutes" ? Number(input.value || 0) : input.value;
  });
  document.querySelectorAll("[data-planner-complete]").forEach((input) => {
    const index = Number(input.dataset.index);
    if (plannerItems[index]) plannerItems[index].completed = input.checked ? 1 : 0;
  });
}

function categoryOptions(current) {
  const categories = ["treino", "estudo", "programacao", "leitura", "foco", "projetos", "alimentacao", "saude", "habitos", "revisao", "sistema", "rotina"];
  return optionsWithCurrent(categories, current || "rotina");
}

function projectOptions(current) {
  const currentValue = String(current || "");
  return `<option value="">Sem projeto</option>` + plannerProjects
    .map((project) => `<option value="${project.id}" ${String(project.id) === currentValue ? "selected" : ""}>${Routine.escapeHtml(project.name)}</option>`)
    .join("");
}

function goalOptions(current) {
  const currentValue = String(current || "");
  return `<option value="">Sem objetivo</option>` + plannerGoals
    .map((goal) => `<option value="${goal.id}" ${String(goal.id) === currentValue ? "selected" : ""}>${Routine.escapeHtml(goal.title)}</option>`)
    .join("");
}

function optionsWithCurrent(values, current) {
  const normalized = String(current || "");
  const allValues = values.includes(normalized) || !normalized ? values : [normalized, ...values];
  return allValues
    .map((value) => `<option value="${Routine.escapeHtml(value)}" ${value === normalized ? "selected" : ""}>${Routine.escapeHtml(value)}</option>`)
    .join("");
}
