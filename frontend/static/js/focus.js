let timer = {
  remaining: 25 * 60,
  duration: 25,
  running: false,
  interval: null,
  startedAt: null,
};
let focusRecommendation = null;

document.addEventListener("DOMContentLoaded", () => {
  bindFocusControls();
  loadFocusData().catch((error) => Routine.toast(error.message, "danger"));
  updateTimerDisplay();
});

function bindFocusControls() {
  document.querySelectorAll(".preset").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".preset").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      field("focus-duration").value = button.dataset.duration;
      field("focus-break").value = button.dataset.break;
      resetTimer();
    });
  });
  field("focus-duration").addEventListener("change", resetTimer);
  field("focus-start").addEventListener("click", startTimer);
  field("focus-pause").addEventListener("click", pauseTimer);
  field("focus-complete").addEventListener("click", completeTimer);
  field("focus-cancel").addEventListener("click", resetTimer);
  field("focus-apply-recommend").addEventListener("click", applyFocusRecommendation);
  field("focus-export").addEventListener("click", () => {
    window.location.href = "/api/focus/export";
  });
}

async function loadFocusData() {
  const [data, recommendation] = await Promise.all([
    Routine.requestJson("/api/focus/sessions"),
    Routine.requestJson("/api/focus/recommend"),
  ]);
  focusRecommendation = recommendation;
  renderProjectOptions(data.projects || []);
  applyFocusParams();
  renderFocusRecommendation(recommendation);
  renderSessions(data.sessions || []);
}

function renderProjectOptions(projects) {
  const select = field("focus-project");
  select.innerHTML = '<option value="">Sem projeto</option>' + projects
    .map((project) => `<option value="${project.id}">${Routine.escapeHtml(project.name)}</option>`)
    .join("");
}

function applyFocusParams() {
  const params = new URLSearchParams(window.location.search);
  if (params.has("duration")) field("focus-duration").value = params.get("duration");
  if (params.has("break")) field("focus-break").value = params.get("break");
  if (params.has("category")) field("focus-category").value = params.get("category");
  if (params.has("project_id")) field("focus-project").value = params.get("project_id");
  if (params.has("note")) field("focus-note").value = params.get("note");
  document.querySelectorAll(".preset").forEach((button) => {
    button.classList.toggle("active", button.dataset.duration === field("focus-duration").value);
  });
  resetTimer();
}

function renderSessions(sessions) {
  const target = field("focus-sessions");
  if (!sessions.length) {
    target.innerHTML = '<div class="empty-state">Nenhuma sessao registrada.</div>';
    return;
  }
  target.innerHTML = sessions
    .map(
      (session) => `
        <article class="session-card">
          <strong>${Routine.escapeHtml(session.category)}</strong>
          <span>${Routine.formatDate(session.date)} · ${session.duration_minutes}min</span>
          <small>${Routine.escapeHtml(session.project_name || "Sem projeto")}</small>
        </article>
      `
    )
    .join("");
}

function renderFocusRecommendation(recommendation) {
  if (!recommendation) return;
  const minutes = recommendation.recommended_minutes || recommendation.minutes || 10;
  Routine.setText("focus-recommend-label", `${recommendation.label || "Bloco leve"} · ${minutes}min`);
  Routine.setText("focus-recommend-reason", recommendation.reason || "Um bloco curto ajuda a comecar.");
}

function applyFocusRecommendation() {
  if (!focusRecommendation) return;
  field("focus-duration").value = focusRecommendation.recommended_minutes || focusRecommendation.minutes || 10;
  field("focus-break").value = focusRecommendation.break_minutes || 3;
  if (focusRecommendation.category) field("focus-category").value = focusRecommendation.category;
  resetTimer();
  Routine.toast("Recomendacao aplicada.");
}

function startTimer() {
  if (timer.running) return;
  timer.duration = Number(field("focus-duration").value || 25);
  if (!timer.startedAt) {
    timer.remaining = timer.duration * 60;
    timer.startedAt = new Date().toISOString();
  }
  timer.running = true;
  Routine.setText("focus-state", "Rodando");
  timer.interval = setInterval(() => {
    timer.remaining -= 1;
    updateTimerDisplay();
    if (timer.remaining <= 0) {
      completeTimer();
    }
  }, 1000);
}

function pauseTimer() {
  timer.running = false;
  clearInterval(timer.interval);
  Routine.setText("focus-state", "Pausado");
}

async function completeTimer() {
  pauseTimer();
  try {
    await Routine.requestJson("/api/focus/save", {
      method: "POST",
      body: collectFocusPayload(),
    });
    Routine.toast("Sessao de foco salva.");
    resetTimer();
    await loadFocusData();
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

function resetTimer() {
  pauseTimer();
  timer.duration = Number(field("focus-duration").value || 25);
  timer.remaining = timer.duration * 60;
  timer.startedAt = null;
  Routine.setText("focus-state", "Pronto");
  updateTimerDisplay();
}

function collectFocusPayload() {
  return {
    date: Routine.todayISO(),
    project_id: field("focus-project").value,
    category: field("focus-category").value,
    duration_minutes: field("focus-duration").value,
    break_minutes: field("focus-break").value,
    started_at: timer.startedAt,
    ended_at: new Date().toISOString(),
    note: field("focus-note").value,
    apply_to_daily: field("focus-apply-daily").checked,
  };
}

function updateTimerDisplay() {
  const minutes = Math.floor(Math.max(timer.remaining, 0) / 60);
  const seconds = Math.max(timer.remaining, 0) % 60;
  field("timer-display").textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function field(id) {
  return document.getElementById(id);
}

let focusModeState = {
  session: null,
  timerInterval: null,
  pollInterval: null,
};

function bindFocusControls() {
  document.querySelectorAll(".preset").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".preset").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      field("focus-duration").value = button.dataset.duration;
      updateTimerDisplay(Number(button.dataset.duration || 25) * 60);
    });
  });
  field("focus-start").addEventListener("click", startQuickFocus);
  field("focus-pause").addEventListener("click", () => focusActionV5("/api/focus/pause"));
  field("focus-resume").addEventListener("click", () => focusActionV5("/api/focus/resume"));
  field("focus-complete").addEventListener("click", () => focusActionV5("/api/focus/complete", finalSummaryV5));
  field("focus-abandon").addEventListener("click", abandonFocusV5);
  field("focus-export").addEventListener("click", () => {
    window.location.href = "/api/focus/export";
  });
}

async function loadFocusData() {
  const params = new URLSearchParams(window.location.search);
  const [current, history] = await Promise.all([
    params.has("session_id") ? Routine.requestJson(`/api/focus/session/${params.get("session_id")}`) : Routine.requestJson("/api/focus/current"),
    Routine.requestJson("/api/focus/history?days=7"),
  ]);
  const session = current.session || null;
  if (session && ["active", "paused"].includes(session.status)) {
    applySessionV5(session);
  } else if (session) {
    finalSummaryV5(session);
  } else {
    renderIdleStateV5();
  }
  renderSessions(history.sessions || []);
}

async function startQuickFocus() {
  try {
    const result = await Routine.requestJson("/api/focus/start", {
      method: "POST",
      body: {
        title: field("focus-quick-title").value,
        focus_type: field("focus-type").value,
        planned_minutes: field("focus-duration").value,
      },
    });
    applySessionV5(result.session);
    Routine.toast("Foco rapido iniciado.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

async function focusActionV5(endpoint, afterRender) {
  if (!focusModeState.session?.id) {
    Routine.toast("Nenhuma sessao ativa.", "warning");
    return;
  }
  try {
    const result = await Routine.requestJson(endpoint, {
      method: "POST",
      body: { session_id: focusModeState.session.id },
    });
    applySessionV5(result.session);
    if (afterRender) afterRender(result.session);
    await refreshHistoryV5();
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

async function abandonFocusV5() {
  if (!focusModeState.session?.id) {
    Routine.toast("Nenhuma sessao ativa.", "warning");
    return;
  }
  const blockStatus = window.confirm("Manter o bloco como pendente para voltar depois?") ? "pending" : "skipped";
  try {
    const result = await Routine.requestJson("/api/focus/abandon", {
      method: "POST",
      body: { session_id: focusModeState.session.id, block_status: blockStatus },
    });
    applySessionV5(result.session);
    finalSummaryV5(result.session);
    await refreshHistoryV5();
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

function applySessionV5(session) {
  focusModeState.session = session;
  Routine.setText("focus-title", `${session.title || "Foco"} - ${typeLabelV5(session.focus_type)} - ${session.planned_minutes}min`);
  Routine.setText("focus-next-step", session.note || "Escolher o menor proximo passo.");
  Routine.setText("focus-state", statusLabelV5(session.status));
  renderExpectedAppsV5(session.expected_apps || []);
  renderFocusCountersV5(session);
  updateActionStateV5(session.status);
  startLocalTimerV5(session);
  startPollingV5();
}

function renderIdleStateV5() {
  focusModeState.session = null;
  Routine.setText("focus-state", "Pronto");
  Routine.setText("focus-title", "Escolha um bloco ou comece um foco rapido.");
  Routine.setText("focus-current-app", "-");
  Routine.setText("focus-match-status", "-");
  renderExpectedAppsV5([]);
  updateTimerDisplay(Number(field("focus-duration").value || 25) * 60);
  updateActionStateV5("idle");
}

function startLocalTimerV5(session) {
  clearInterval(focusModeState.timerInterval);
  const planned = Number(session.planned_minutes || 25) * 60;
  const started = new Date(String(session.started_at || "").replace(" ", "T"));
  focusModeState.timerInterval = setInterval(() => {
    if (!focusModeState.session || focusModeState.session.status !== "active") return;
    const elapsed = Number.isNaN(started.getTime()) ? Number(session.actual_seconds || 0) : Math.floor((Date.now() - started.getTime()) / 1000);
    updateTimerDisplay(Math.max(planned - elapsed, 0));
  }, 1000);
}

function startPollingV5() {
  clearInterval(focusModeState.pollInterval);
  if (!focusModeState.session || !["active", "paused"].includes(focusModeState.session.status)) return;
  focusModeState.pollInterval = setInterval(refreshCurrentV5, 5000);
  refreshCurrentV5().catch(() => {});
}

async function refreshCurrentV5() {
  const data = await Routine.requestJson("/api/focus/current");
  if (!data.active) return;
  focusModeState.session = data.session;
  renderFocusCountersV5(data.session);
  Routine.setText("focus-current-app", data.focused_app?.app_name || "-");
  Routine.setText("focus-match-status", matchLabelV5(data.match?.match_status));
  const alert = field("focus-soft-alert");
  if (data.alert) {
    alert.hidden = false;
    alert.textContent = data.alert.message;
  } else {
    alert.hidden = true;
  }
}

function renderFocusCountersV5(session) {
  Routine.setText("focus-focused-time", `${Routine.number((session.focused_seconds || 0) / 60, 0)}min`);
  Routine.setText("focus-distracted-time", `${Routine.number((session.distracted_seconds || 0) / 60, 0)}min`);
}

function renderExpectedAppsV5(apps) {
  const target = field("focus-expected-apps");
  target.innerHTML = apps.length ? apps.map((app) => `<span class="tag">${Routine.escapeHtml(app)}</span>`).join("") : `<p class="muted">Qualquer app neutro pode servir neste bloco.</p>`;
}

function finalSummaryV5(session) {
  clearInterval(focusModeState.pollInterval);
  clearInterval(focusModeState.timerInterval);
  const statusText = session.status === "completed" ? "Sessao concluida" : "Sessao encerrada";
  field("focus-final-summary").innerHTML = `
    <article class="session-card">
      <strong>${statusText}</strong>
      <span>${Routine.escapeHtml(session.title || "Foco")}</span>
      <small>Planejado: ${session.planned_minutes || 0}min</small>
      <small>Tempo real: ${Routine.number((session.actual_seconds || 0) / 60, 0)}min</small>
      <small>Foco estimado: ${Routine.number((session.focused_seconds || 0) / 60, 0)}min</small>
      <small>Fora do bloco: ${Routine.number((session.distracted_seconds || 0) / 60, 0)}min</small>
      <p class="muted">${session.status === "completed" ? "Bom trabalho. Voce concluiu o essencial desse bloco." : "Voce ainda pode voltar depois. O objetivo e ajustar sem recomecar do zero."}</p>
    </article>
  `;
  updateActionStateV5(session.status);
}

async function refreshHistoryV5() {
  const history = await Routine.requestJson("/api/focus/history?days=7");
  renderSessions(history.sessions || []);
}

function renderSessions(sessions) {
  const target = field("focus-sessions");
  if (!sessions.length) {
    target.innerHTML = '<div class="empty-state">Nenhuma sessao registrada.</div>';
    return;
  }
  target.innerHTML = sessions.slice(0, 8).map((session) => `
    <article class="session-card">
      <strong>${Routine.escapeHtml(session.title || typeLabelV5(session.focus_type))}</strong>
      <span>${Routine.formatDate(session.date)} - ${session.planned_minutes || session.duration_minutes}min - ${statusLabelV5(session.status)}</span>
      <small>Foco ${Routine.number((session.focused_seconds || 0) / 60, 0)}min - fora ${Routine.number((session.distracted_seconds || 0) / 60, 0)}min</small>
    </article>
  `).join("");
}

function updateActionStateV5(status) {
  field("focus-pause").disabled = status !== "active";
  field("focus-resume").disabled = status !== "paused";
  field("focus-complete").disabled = !["active", "paused"].includes(status);
  field("focus-abandon").disabled = !["active", "paused"].includes(status);
  field("focus-start").disabled = ["active", "paused"].includes(status);
}

function updateTimerDisplay(secondsValue) {
  const fallback = Number(field("focus-duration")?.value || 25) * 60;
  const seconds = Math.max(0, Math.floor(secondsValue ?? fallback));
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  field("timer-display").textContent = `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

function typeLabelV5(value) {
  return {
    study: "Estudo",
    project: "Projeto",
    workout: "Treino",
    organization: "Organizacao",
    reading: "Leitura",
    rest: "Descanso",
    generic: "Generico",
  }[value] || "Generico";
}

function statusLabelV5(value) {
  return {
    active: "Rodando",
    paused: "Pausado",
    completed: "Concluido",
    abandoned: "Abandonado",
    pending: "Pendente",
  }[value] || "Pronto";
}

function matchLabelV5(value) {
  return { match: "Combina", warning: "Atencao leve", mismatch: "Fora do bloco" }[value] || "-";
}
