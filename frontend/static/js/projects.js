let projects = [];
let projectsChart = null;

document.addEventListener("DOMContentLoaded", () => {
  field("time-date").value = Routine.todayISO();
  field("project-form").addEventListener("submit", saveProject);
  field("project-reset").addEventListener("click", resetProjectForm);
  field("project-time-form").addEventListener("submit", addManualTime);
  field("time-project").addEventListener("change", () => renderProjectTimeList().catch((error) => Routine.toast(error.message, "danger")));
  field("projects-export").addEventListener("click", () => {
    window.location.href = "/api/projects/export";
  });
  loadProjects().catch((error) => Routine.toast(error.message, "danger"));
});

async function loadProjects() {
  const data = await Routine.requestJson("/api/projects");
  projects = data.projects || [];
  renderSummary(data.summary || {});
  renderProjectList(projects);
  renderProjectSelects(projects);
  renderProjectTimeList();
}

function renderSummary(summary) {
  Routine.setText("project-active-count", summary.active_projects || 0);
  Routine.setText("project-week-hours", `${Routine.number(summary.total_hours, 1)}h`);
  Routine.setText("project-below-goal", (summary.below_goal || []).length);
  drawProjectsChart(summary.hours_by_project || {});
}

function renderProjectList(items) {
  const target = field("projects-list");
  if (!items.length) {
    target.innerHTML = '<div class="empty-state">Nenhum projeto ativo.</div>';
    return;
  }
  target.innerHTML = items
    .map(
      (project) => `
        <article class="project-card" style="--project-color:${project.color}">
          <div>
            <span class="pill">${Routine.escapeHtml(project.category)}</span>
            <h3>${Routine.escapeHtml(project.name)}</h3>
            <p>${Routine.escapeHtml(project.description || "")}</p>
          </div>
          <div class="project-meta">
            <strong>${Routine.number(project.week_hours || 0, 1)}h</strong>
            <small>meta ${Routine.number(project.weekly_hours_goal || 0, 1)}h · ${Routine.escapeHtml(project.status)}</small>
          </div>
          <div class="form-actions">
            <button class="button secondary edit-project" data-id="${project.id}" type="button">Editar</button>
            <button class="button ghost archive-project" data-id="${project.id}" type="button">Arquivar</button>
          </div>
        </article>
      `
    )
    .join("");
  target.querySelectorAll(".edit-project").forEach((button) => {
    button.addEventListener("click", () => editProject(Number(button.dataset.id)));
  });
  target.querySelectorAll(".archive-project").forEach((button) => {
    button.addEventListener("click", () => archiveProject(Number(button.dataset.id)));
  });
}

function renderProjectSelects(items) {
  const options = items.map((project) => `<option value="${project.id}">${Routine.escapeHtml(project.name)}</option>`).join("");
  field("time-project").innerHTML = options || '<option value="">Crie um projeto</option>';
}

async function renderProjectTimeList() {
  const projectId = field("time-project").value;
  const target = field("project-time-list");
  if (!projectId) {
    target.innerHTML = '<div class="empty-state">Selecione um projeto.</div>';
    return;
  }
  const data = await Routine.requestJson(`/api/projects/${projectId}/time`);
  const entries = data.entries || [];
  if (!entries.length) {
    target.innerHTML = '<div class="empty-state">Sem tempo lancado para este projeto.</div>';
    return;
  }
  target.innerHTML = entries.slice(0, 10).map((entry) => `
    <article class="session-card">
      <strong>${Routine.formatDate(entry.date)}</strong>
      <span>${Routine.number(entry.minutes / 60, 1)}h · ${Routine.escapeHtml(entry.source)}</span>
      <small>${Routine.escapeHtml(entry.note || "")}</small>
    </article>
  `).join("");
}

async function saveProject(event) {
  event.preventDefault();
  const id = field("project-id").value;
  const url = id ? `/api/projects/${id}` : "/api/projects";
  try {
    await Routine.requestJson(url, { method: "POST", body: collectProjectPayload() });
    resetProjectForm();
    await loadProjects();
    Routine.toast("Projeto salvo.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

function collectProjectPayload() {
  return {
    name: value("project-name"),
    description: value("project-description"),
    category: value("project-category"),
    status: value("project-status"),
    color: value("project-color"),
    weekly_hours_goal: value("project-weekly-goal"),
    active: field("project-active").checked,
  };
}

function editProject(id) {
  const project = projects.find((item) => Number(item.id) === id);
  if (!project) return;
  field("project-id").value = project.id;
  setValue("project-name", project.name);
  setValue("project-description", project.description);
  setValue("project-category", project.category);
  setValue("project-status", project.status);
  setValue("project-color", project.color || "#38b99b");
  setValue("project-weekly-goal", project.weekly_hours_goal || 0);
  field("project-active").checked = Boolean(Number(project.active));
  Routine.setText("project-form-title", "Editar projeto");
  Routine.setText("project-editing", "Edicao");
}

async function archiveProject(id) {
  if (!Routine.confirmAction("Arquivar este projeto?")) return;
  try {
    await Routine.requestJson(`/api/projects/${id}/archive`, { method: "POST" });
    await loadProjects();
    Routine.toast("Projeto arquivado.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

async function addManualTime(event) {
  event.preventDefault();
  const projectId = field("time-project").value;
  if (!projectId) return;
  try {
    await Routine.requestJson(`/api/projects/${projectId}/time`, {
      method: "POST",
      body: {
        date: value("time-date"),
        minutes: value("time-minutes"),
        source: "manual",
        note: value("time-note"),
      },
    });
    await loadProjects();
    await renderProjectTimeList();
    Routine.toast("Tempo adicionado.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

function resetProjectForm() {
  field("project-form").reset();
  field("project-id").value = "";
  field("project-color").value = "#38b99b";
  field("project-active").checked = true;
  Routine.setText("project-form-title", "Novo projeto");
  Routine.setText("project-editing", "Criacao");
}

function drawProjectsChart(hoursByProject) {
  const canvas = field("projects-chart");
  if (!canvas || !window.Chart) return;
  if (projectsChart) projectsChart.destroy();
  projectsChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: Object.keys(hoursByProject),
      datasets: [{ label: "Horas", data: Object.values(hoursByProject), backgroundColor: "#38b99b" }],
    },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } },
  });
}

function field(id) {
  return document.getElementById(id);
}

function value(id) {
  return field(id).value;
}

function setValue(id, value) {
  field(id).value = value ?? "";
}

