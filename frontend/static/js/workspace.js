(function () {
  let state = null;

  document.addEventListener("DOMContentLoaded", () => {
    bindActions();
    loadWorkspace();
  });

  async function loadWorkspace() {
    try {
      state = await Routine.requestJson(`/api/workspace?date=${Routine.todayISO()}`);
      renderWorkspace(state);
    } catch (error) {
      Routine.toast(error.message, "error");
    }
  }

  function bindActions() {
    document.getElementById("workspace-checkin-open")?.addEventListener("click", () => {
      const checkin = document.getElementById("workspace-checkin");
      checkin.hidden = !checkin.hidden;
    });
    document.querySelectorAll("[data-energy]").forEach((button) => {
      button.addEventListener("click", async () => {
        await Routine.requestJson("/api/day-planner/checkin", {
          method: "POST",
          body: { date: Routine.todayISO(), energy_level: button.dataset.energy },
        });
        document.getElementById("workspace-checkin").hidden = true;
        Routine.toast("Ritmo do dia atualizado.");
        loadWorkspace();
      });
    });
    document.getElementById("workspace-plan-generate")?.addEventListener("click", async (event) => {
      const button = event.currentTarget;
      Routine.setButtonLoading(button, true, "Organizando...");
      try {
        await Routine.requestJson("/api/day-planner/generate", { method: "POST", body: { date: Routine.todayISO() } });
        Routine.toast("Plano do dia criado.");
        await loadWorkspace();
      } finally {
        Routine.setButtonLoading(button, false);
      }
    });
    document.getElementById("workspace-plan-complete")?.addEventListener("click", completePlanBlock);
    document.getElementById("quick-task-form")?.addEventListener("submit", createTask);
    document.getElementById("workspace-tasks")?.addEventListener("click", handleTaskClick);
    document.getElementById("workspace-reviews")?.addEventListener("click", handleReviewClick);
  }

  function renderWorkspace(data) {
    const date = new Date(`${data.date}T12:00:00`);
    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
    setText("workspace-date", new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" }).format(date));
    setText("workspace-greeting", `${greeting}. Vamos ao que importa.`);
    renderNextAction(data.planner || {});
    renderTasks(data.tasks || {});
    renderStudies(data.studies || {}, data.reviews || []);
    renderPulse(data);
    renderHabits(data.habits || {});
  }

  function renderNextAction(planner) {
    const next = planner.next_step;
    const context = planner.context || {};
    const generateButton = document.getElementById("workspace-plan-generate");
    const completeButton = document.getElementById("workspace-plan-complete");
    setText("workspace-plan-mode", modeLabel(context.suggested_mode));
    if (!next) {
      setText("workspace-next-title", "Crie um plano curto para comecar");
      setText("workspace-next-detail", planner.message || "Organize o dia em blocos realistas para sua energia atual.");
      document.getElementById("workspace-microsteps").innerHTML = "";
      generateButton.hidden = false;
      completeButton.hidden = true;
      return;
    }
    setText("workspace-next-title", next.title || "Proximo bloco");
    setText("workspace-next-detail", `${next.duration_minutes || 25} min · ${blockTypeLabel(next.type)}`);
    document.getElementById("workspace-microsteps").innerHTML = (next.microsteps || [])
      .slice(0, 4)
      .map((step) => `<li>${Routine.escapeHtml(step)}</li>`)
      .join("");
    generateButton.hidden = true;
    completeButton.hidden = false;
    completeButton.dataset.blockId = next.id;
    const focusLink = document.getElementById("workspace-focus-action");
    focusLink.href = `/focus?title=${encodeURIComponent(next.title || "Foco")}&minutes=${next.duration_minutes || 25}&block_id=${next.id || ""}`;
  }

  async function completePlanBlock(event) {
    const blockId = Number(event.currentTarget.dataset.blockId || 0);
    if (!blockId) return;
    await Routine.requestJson("/api/day-planner/block/complete", { method: "POST", body: { block_id: blockId } });
    Routine.toast("Bloco concluido.");
    loadWorkspace();
  }

  function renderTasks(tasks) {
    const items = [...(tasks.overdue || []), ...(tasks.today || []), ...(tasks.backlog || [])].slice(0, 9);
    const counts = tasks.counts || {};
    const pending = Number(counts.today || 0) + Number(counts.overdue || 0) + Number(counts.backlog || 0);
    setText("workspace-task-count", `${pending} ${pending === 1 ? "pendente" : "pendentes"}`);
    document.getElementById("workspace-tasks").innerHTML = items.length
      ? items.map(taskTemplate).join("")
      : `<div class="empty-state"><strong>Dia livre por aqui</strong><span>Adicione uma tarefa ou gere o plano do dia.</span></div>`;
  }

  function taskTemplate(task) {
    const overdue = task.due_date && task.due_date < Routine.todayISO();
    const meta = [areaLabel(task.area), `${task.estimated_minutes || 25} min`, task.project_name].filter(Boolean).join(" · ");
    return `<article class="workspace-task ${overdue ? "overdue" : ""}">
      <button class="task-check" data-task-complete="${task.id}" type="button" aria-label="Concluir"></button>
      <div><strong>${Routine.escapeHtml(task.title)}</strong><span>${Routine.escapeHtml(meta)}</span></div>
      ${overdue ? '<span class="task-alert">Atrasada</span>' : `<span class="priority-dot priority-${task.priority || 2}" aria-label="Prioridade"></span>`}
      <button class="task-more" data-task-archive="${task.id}" type="button" aria-label="Arquivar">&times;</button>
    </article>`;
  }

  async function createTask(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Routine.formToObject(form);
    payload.scheduled_for = Routine.todayISO();
    payload.estimated_minutes = 25;
    await Routine.requestJson("/api/tasks", { method: "POST", body: payload });
    form.reset();
    Routine.toast("Tarefa adicionada.");
    loadWorkspace();
  }

  async function handleTaskClick(event) {
    const complete = event.target.closest("[data-task-complete]");
    const archive = event.target.closest("[data-task-archive]");
    if (complete) {
      await Routine.requestJson(`/api/tasks/${complete.dataset.taskComplete}/complete`, { method: "POST", body: { completed: true } });
      Routine.toast("Tarefa concluida.");
      loadWorkspace();
    }
    if (archive) {
      await Routine.requestJson(`/api/tasks/${archive.dataset.taskArchive}`, { method: "DELETE" });
      loadWorkspace();
    }
  }

  function renderStudies(studies, reviews) {
    setText("study-hours", `${Routine.number(studies.total_hours || 0, 1)}h`);
    setText("study-questions", studies.questions_done || 0);
    setText("study-accuracy", `${Routine.number(studies.accuracy || 0, 0)}%`);
    setText("study-reviews", studies.due_reviews || 0);
    document.getElementById("workspace-reviews").innerHTML = reviews.length
      ? `<div class="review-heading">Revisoes para hoje</div>${reviews.slice(0, 3).map((item) => `<article class="review-item"><div><strong>${Routine.escapeHtml(item.subject)} · ${Routine.escapeHtml(item.topic || "Topico")}</strong><span>${Routine.escapeHtml(item.error_type || "revisao")}</span></div><button class="button ghost" data-review-id="${item.study_error_id}" type="button">Revisar</button></article>`).join("")}`
      : `<div class="study-empty">Nenhuma revisao pendente hoje.</div>`;
  }

  async function handleReviewClick(event) {
    const button = event.target.closest("[data-review-id]");
    if (!button) return;
    await Routine.requestJson(`/api/studies/reviews/${button.dataset.reviewId}`, { method: "POST", body: { quality: 4, date: Routine.todayISO() } });
    Routine.toast("Revisao registrada e reagendada.");
    loadWorkspace();
  }

  function renderPulse(data) {
    const daily = data.daily || {};
    const focus = (data.focus || {}).summary || {};
    const load = data.load_balance || {};
    setText("pulse-score", Math.round(Number(daily.daily_score || 0)));
    setText("pulse-sleep", daily.sleep_hours ? `${Routine.number(daily.sleep_hours, 1)}h` : "Sem dado");
    setText("pulse-energy", daily.energy ? `${daily.energy}/5` : "Sem dado");
    setText("pulse-focus", `${Math.round(Number(focus.focused_minutes || focus.total_minutes || 0))} min`);
    setText("pulse-load", load.level ? capitalize(load.level) : "Sem dado");
  }

  function renderHabits(data) {
    const habits = data.habits || [];
    document.getElementById("workspace-habits").innerHTML = habits.length
      ? habits.slice(0, 5).map((habit) => `<div class="workspace-habit"><span class="habit-state ${Number(habit.completed) ? "done" : ""}"></span><div><strong>${Routine.escapeHtml(habit.name)}</strong><span>${Routine.escapeHtml(habit.category || "Rotina")}</span></div></div>`).join("")
      : `<div class="study-empty">Crie habitos para acompanhar aqui.</div>`;
  }

  function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  }

  function modeLabel(value) {
    return ({ light: "Leve", normal: "Normal", strong: "Intenso" })[value] || "Plano";
  }

  function areaLabel(value) {
    return ({ rotina: "Rotina", estudos: "Estudos", saude: "Saude", projetos: "Projetos", pessoal: "Pessoal" })[value] || "Rotina";
  }

  function blockTypeLabel(value) {
    return ({ project: "Projeto", study: "Estudo", health: "Saude", routine: "Rotina", workout: "Treino", review: "Revisao" })[value] || areaLabel(value);
  }

  function capitalize(value) {
    return String(value || "").charAt(0).toUpperCase() + String(value || "").slice(1);
  }
})();
