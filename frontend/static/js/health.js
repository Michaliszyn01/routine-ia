document.addEventListener("DOMContentLoaded", () => {
  bindHealthViewMode();
  document.getElementById("date").value = Routine.todayISO();
  document.getElementById("health-form").addEventListener("submit", saveHealthData);
  document.getElementById("clear-health-form").addEventListener("click", clearHealthForm);
  document.getElementById("health-import-now").addEventListener("click", runHealthSyncImport);
  document.getElementById("save-health-sync-settings").addEventListener("click", saveHealthSyncSettings);
  document.getElementById("open-health-sync-folder").addEventListener("click", openHealthSyncFolder);
  document.getElementById("toggle-health-auto-import").addEventListener("click", toggleHealthAutoImport);
  document.getElementById("export-health-csv").addEventListener("click", () => {
    window.location.href = "/api/health/export";
  });
  document.getElementById("health-csv-file").addEventListener("change", importHealthCsv);
  loadHealthImportStatus().catch((error) => Routine.toast(error.message, "danger"));
  loadHealthData().catch((error) => Routine.toast(error.message));
});

function bindHealthViewMode() {
  const simple = document.getElementById("health-simple-view");
  const advanced = document.getElementById("health-advanced-view");
  if (!simple || !advanced) return;
  simple.addEventListener("click", () => setHealthViewMode("simple"));
  advanced.addEventListener("click", () => setHealthViewMode("advanced"));
  setHealthViewMode("simple");
}

function setHealthViewMode(mode) {
  const advancedMode = mode === "advanced";
  document.querySelectorAll(".health-advanced-area").forEach((element) => {
    element.classList.toggle("hidden", !advancedMode);
  });
  const simple = document.getElementById("health-simple-view");
  const advanced = document.getElementById("health-advanced-view");
  if (simple && advanced) {
    simple.classList.toggle("active", !advancedMode);
    advanced.classList.toggle("active", advancedMode);
    simple.classList.toggle("ghost", advancedMode);
    simple.classList.toggle("secondary", !advancedMode);
    advanced.classList.toggle("ghost", !advancedMode);
    advanced.classList.toggle("secondary", advancedMode);
  }
}

async function saveHealthData(event) {
  event.preventDefault();
  try {
    await Routine.requestJson("/api/health", {
      method: "POST",
      body: collectHealthPayload(),
    });
    await loadHealthData();
    Routine.toast("Health data salvo.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

async function loadHealthData() {
  const data = await Routine.requestJson("/api/health");
  renderHealthRows(data.records);
}

async function loadHealthImportStatus() {
  const data = await Routine.requestJson("/api/health/status");
  renderHealthImportStatus(data);
}

async function saveHealthSyncSettings() {
  try {
    const settings = collectHealthSyncSettings();
    await Routine.requestJson("/api/health/settings", {
      method: "POST",
      body: settings,
    });
    await loadHealthImportStatus();
    setFeedback("Configuracao de importacao salva.");
    Routine.toast("Integracao Health Sync salva.");
  } catch (error) {
    setFeedback(error.message, "danger");
    Routine.toast(error.message, "danger");
  }
}

async function runHealthSyncImport() {
  const button = document.getElementById("health-import-now");
  Routine.setButtonLoading(button, true, "Importando...");
  try {
    const result = await Routine.requestJson("/api/health/import-now", {
      method: "POST",
      body: collectHealthSyncSettings(),
    });
    await loadHealthImportStatus();
    await loadHealthData();
    setFeedback(result.message || "Importacao concluida com sucesso.");
    Routine.toast(result.message || "Importacao concluida.");
  } catch (error) {
    await loadHealthImportStatus().catch(() => {});
    setFeedback(error.message, "danger");
    Routine.toast(error.message, "danger");
  } finally {
    Routine.setButtonLoading(button, false);
  }
}

async function openHealthSyncFolder() {
  try {
    const result = await Routine.requestJson("/api/health/open-folder", {
      method: "POST",
      body: { health_sync_base_path: value("health_sync_base_path") },
    });
    if (result.opened) {
      Routine.toast("Pasta aberta no Explorer.");
    } else {
      setFeedback(`Caminho para copiar: ${result.path || "-"}`);
      Routine.toast("Nao consegui abrir automaticamente. O caminho foi exibido.");
    }
  } catch (error) {
    setFeedback(error.message, "danger");
    Routine.toast(error.message, "danger");
  }
}

async function toggleHealthAutoImport() {
  const checkbox = document.getElementById("health_auto_import_enabled");
  checkbox.checked = !checkbox.checked;
  await saveHealthSyncSettings();
}

function collectHealthSyncSettings() {
  return {
    health_sync_base_path: value("health_sync_base_path"),
    health_auto_import_enabled: document.getElementById("health_auto_import_enabled").checked,
    health_import_interval_hours: value("health_import_interval_hours"),
  };
}

function renderHealthImportStatus(data) {
  const settings = data.settings || {};
  const scan = data.scan || {};
  const dashboard = data.dashboard || {};
  const lastImport = data.last_import || {};
  const scheduler = data.scheduler || {};
  const worker = data.worker?.worker || {};
  const importStats = data.import_stats || {};
  const operation = data.operation || {};
  const autoEnabled = String(settings.health_auto_import_enabled || "true") === "true";
  document.getElementById("health_sync_base_path").value = settings.health_sync_base_path || "G:\\Meu Drive";
  document.getElementById("health_auto_import_enabled").checked = autoEnabled;
  document.getElementById("health_import_interval_hours").value = String(settings.health_import_interval_hours || "4");

  Routine.setText("health-sync-path", scan.base_path || settings.health_sync_base_path || "-");
  Routine.setText("health-sync-folder-status", scan.exists ? "Pasta encontrada" : "Pasta nao encontrada");
  Routine.setText("health-sync-last-import", lastImport.imported_at ? Routine.formatDateTime(lastImport.imported_at) : "-");
  Routine.setText("health-sync-next-import", autoEnabled ? formatDateTimeOrDash(data.next_import_at || scheduler.next_run_at) : "-");
  Routine.setText("health-sync-auto-status", autoEnabled ? "Ativada" : "Desativada");
  Routine.setText("health-sync-worker-status", formatWorkerStatus(worker, autoEnabled));
  Routine.setText("health-sync-imported-files", formatNumber(importStats.total || 0));
  Routine.setText("health-sync-ignored-files", formatNumber(scan.ignored_count || 0));
  Routine.setText("health-sync-last-error", operation.last_error || lastImport.error_message || (scan.errors || [])[0] || "-");

  const status = document.getElementById("health-sync-status");
  if (operation.level) {
    status.textContent = operation.level === "ok" ? "OK" : operation.level === "error" ? "Erro" : "Atencao";
    status.dataset.status = operation.level === "error" ? "error" : "ok";
  } else if (scan.exists) {
    status.textContent = lastImport.status === "error" ? "Erro" : "OK";
    status.dataset.status = lastImport.status === "error" ? "error" : "ok";
  } else {
    status.textContent = "Pasta nao encontrada";
    status.dataset.status = "error";
  }
  renderHealthOperation(operation);
  renderHealthSyncMessage(scan);
  renderHealthCards(dashboard);
  renderHealthWeek(dashboard.daily || []);
  renderHealthInsights(dashboard.insights || []);
  renderHealthLogs(dashboard.logs || []);
}

function renderHealthOperation(operation) {
  const card = document.getElementById("health-operation-card");
  if (!card) return;
  const level = operation.level || "ok";
  card.dataset.level = level;
  Routine.setText("health-operation-title", operation.title || "Health Importer pronto");
  Routine.setText("health-operation-message", operation.message || "Importacao local pronta.");
  Routine.setText("health-operation-action", operation.action || "");
}

function formatWorkerStatus(worker, autoEnabled) {
  if (!autoEnabled) return "Nao necessario";
  if (worker?.running) return `Ativo desde ${formatDateTimeOrDash(worker.heartbeat_at)}`;
  if (worker?.reason === "status_missing") return "Aguardando inicializacao";
  return "Sem heartbeat recente";
}

function renderHealthSyncMessage(scan) {
  const target = document.getElementById("health-sync-message");
  const errors = scan.errors || [];
  if (!scan.exists) {
    target.textContent = "Nao encontrei a pasta configurada. Verifique se o Google Drive esta aberto e sincronizado.";
    target.classList.remove("hidden");
    return;
  }
  if (!errors.length) {
    target.classList.add("hidden");
    target.textContent = "";
    return;
  }
  target.textContent = errors[0];
  target.classList.remove("hidden");
}

function renderHealthCards(dashboard) {
  const today = dashboard.today || {};
  const sleep = today.sleep || {};
  const steps = today.steps_summary || { total_steps: today.steps || 0, has_data: Boolean(today.steps) };
  const workout = dashboard.last_activity || today.workout || {};
  const heart = today.heart_rate || {};

  Routine.setText("health-today-sleep", sleep.has_data ? `${formatSecondsToHoursMinutes(sleep.total_sleep_seconds)} dormidas` : "-");
  Routine.setText(
    "health-today-sleep-detail",
    sleep.has_data
      ? `Leve: ${formatSecondsToHoursMinutes(sleep.light_sleep_seconds)} | Profundo: ${formatSecondsToHoursMinutes(sleep.deep_sleep_seconds)} | REM: ${formatSecondsToHoursMinutes(sleep.rem_sleep_seconds)} | Acordado: ${formatSecondsToHoursMinutes(sleep.awake_seconds)}`
      : "Ainda nao ha dados de sono importados."
  );

  Routine.setText("health-today-steps", steps.has_data ? `${formatNumber(steps.total_steps)} passos` : "-");
  Routine.setText("health-today-steps-detail", steps.has_data ? formatStepComparison(steps.difference_from_yesterday) : "Ainda nao ha dados de passos importados.");

  Routine.setText("health-last-workout", workout.has_data ? (workout.label || "Treino") : "-");
  Routine.setText("health-last-workout-detail", workout.has_data ? formatWorkoutDetail(workout) : "Ainda nao ha treino importado.");

  Routine.setText("health-today-hr", heart.has_data ? `FC media: ${formatBpm(heart.avg_bpm)}` : "-");
  Routine.setText(
    "health-today-hr-detail",
    heart.has_data
      ? `Min: ${formatBpm(heart.min_bpm)} | Max: ${formatBpm(heart.max_bpm)} | Amostras: ${formatNumber(heart.samples_count)}`
      : "Ainda nao ha dados de frequencia cardiaca."
  );
}

function renderHealthWeek(records) {
  const body = document.getElementById("health-sync-week-body");
  if (!records.length) {
    body.innerHTML = '<tr><td colspan="5" class="muted">Ainda nao ha dados importados. Clique em "Importar agora" para buscar dados do Health Sync.</td></tr>';
    return;
  }
  body.innerHTML = records
    .map((record) => {
      const sleep = record.sleep || {};
      const steps = record.steps_summary || { total_steps: record.steps || 0, has_data: Boolean(record.steps) };
      const workout = record.workout || {};
      const heart = record.heart_rate || {};
      return `
        <tr>
          <td>${formatDateBR(record.date)}</td>
          <td>${sleep.has_data ? formatSecondsToHoursMinutes(sleep.total_sleep_seconds) : "-"}</td>
          <td>${steps.has_data ? formatNumber(steps.total_steps) : "-"}</td>
          <td>${workout.has_data ? formatWorkoutSummary(workout) : "-"}</td>
          <td>${heart.has_data ? formatBpm(heart.avg_bpm) : "-"}</td>
        </tr>
      `;
    })
    .join("");
}

function renderHealthInsights(insights) {
  const target = document.getElementById("health-sync-insights");
  target.innerHTML = insights.length
    ? insights.map((item) => `<li>${Routine.escapeHtml(item)}</li>`).join("")
    : '<li>Nenhum insight simples ainda.</li>';
}

function renderHealthLogs(logs) {
  const body = document.getElementById("health-sync-log-body");
  if (!logs.length) {
    body.innerHTML = '<tr><td colspan="5" class="muted">Nenhum arquivo importado ainda.</td></tr>';
    return;
  }
  body.innerHTML = logs
    .map(
      (item) => `
        <tr>
          <td>${Routine.escapeHtml(item.file_name)}</td>
          <td>${Routine.escapeHtml(item.data_type)}</td>
          <td>${Routine.escapeHtml(item.status)}</td>
          <td>${Routine.number(item.rows_imported || 0)}</td>
          <td>${Routine.formatDateTime(item.imported_at)}</td>
        </tr>
      `
    )
    .join("");
}

function formatSecondsToHoursMinutes(seconds) {
  const totalMinutes = Math.round(Number(seconds || 0) / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (!hours && !minutes) return "0min";
  if (!hours) return `${minutes}min`;
  return `${hours}h${String(minutes).padStart(2, "0")}`;
}

function formatNumber(value, digits = 0) {
  return Routine.number(Number(value || 0), digits);
}

function formatDateBR(value) {
  if (!value) return "-";
  const parts = String(value).split("-");
  if (parts.length === 3) return `${parts[2]}/${parts[1]}`;
  return Routine.formatDate(value) || "-";
}

function formatDateTimeOrDash(value) {
  return value ? Routine.formatDateTime(value) : "-";
}

function formatBpm(value) {
  const number = Number(value || 0);
  return number ? `${formatNumber(number)} bpm` : "-";
}

function formatDistanceKm(value) {
  const distance = Number(value || 0);
  return distance ? `${formatNumber(distance, 2)} km` : "";
}

function formatStepComparison(value) {
  if (value === null || value === undefined) return "Sem comparacao com ontem.";
  const number = Number(value || 0);
  if (number > 0) return `+${formatNumber(number)} em relacao a ontem`;
  if (number < 0) return `${formatNumber(number)} em relacao a ontem`;
  return "Mesmo total de ontem.";
}

function formatWorkoutSummary(workout) {
  const label = workout.label || "Treino";
  const minutes = Math.round(Number(workout.active_seconds || workout.elapsed_seconds || 0) / 60);
  return `${Routine.escapeHtml(label)} ${minutes ? `${formatNumber(minutes)}min` : ""}`.trim();
}

function formatWorkoutDetail(workout) {
  const dateText = formatRelativeWorkoutDate(workout.date, workout.start_time);
  const minutes = Math.round(Number(workout.active_seconds || workout.elapsed_seconds || 0) / 60);
  const distance = formatDistanceKm(workout.distance_km);
  return [dateText, minutes ? `${formatNumber(minutes)} min` : "", distance].filter(Boolean).join(" | ");
}

function formatRelativeWorkoutDate(dateValue, timeValue) {
  if (!dateValue) return "";
  const today = Routine.todayISO();
  const yesterday = offsetISO(-1);
  const time = timeValue ? ` as ${String(timeValue).slice(0, 5)}` : "";
  if (dateValue === today) return `Hoje${time}`;
  if (dateValue === yesterday) return `Ontem${time}`;
  return `${Routine.formatDate(dateValue)}${time}`;
}

function offsetISO(days) {
  const current = new Date(`${Routine.todayISO()}T00:00:00`);
  current.setDate(current.getDate() + days);
  const offset = current.getTimezoneOffset();
  return new Date(current.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function setFeedback(message, type = "info") {
  const target = document.getElementById("health-import-feedback");
  if (!target) return;
  target.textContent = message || "";
  target.dataset.type = type;
}

function formatDuration(seconds) {
  return formatSecondsToHoursMinutes(seconds);
}

function collectHealthPayload() {
  return {
    date: value("date"),
    source: value("source"),
    sleep_hours_auto: value("sleep_hours_auto"),
    steps_auto: value("steps_auto"),
    workout_minutes_auto: value("workout_minutes_auto"),
    average_heart_rate: value("average_heart_rate"),
    resting_heart_rate: value("resting_heart_rate"),
    stress_average: value("stress_average"),
    weight_kg: value("weight_kg"),
    observation: value("observation"),
  };
}

function renderHealthRows(records) {
  const body = document.getElementById("health-body");
  if (!records.length) {
    body.innerHTML = '<tr><td colspan="9" class="muted">Nenhum dado de saúde registrado.</td></tr>';
    return;
  }

  body.innerHTML = records
    .map(
      (record) => `
        <tr>
          <td>${Routine.formatDate(record.date)}</td>
          <td>${Routine.escapeHtml(record.source)}</td>
          <td>${Routine.number(record.sleep_hours_auto, 1)}h</td>
          <td>${Routine.number(record.steps_auto)}</td>
          <td>${Routine.number(record.workout_minutes_auto)} min</td>
          <td>${Routine.number(record.average_heart_rate)}</td>
          <td>${Routine.number(record.resting_heart_rate)}</td>
          <td>${Routine.number(record.stress_average, 1)}</td>
          <td>${Routine.number(record.weight_kg, 1)} kg</td>
        </tr>
      `
    )
    .join("");
}

function value(id) {
  return document.getElementById(id).value;
}

async function importHealthCsv(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);
  try {
    const result = await Routine.requestJson("/api/health/import", {
      method: "POST",
      body: formData,
    });
    await loadHealthData();
    Routine.toast(result.message || "CSV importado.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  } finally {
    event.target.value = "";
  }
}

function clearHealthForm() {
  document.getElementById("health-form").reset();
  document.getElementById("date").value = Routine.todayISO();
}
