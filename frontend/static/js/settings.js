document.addEventListener("DOMContentLoaded", () => {
  loadSettings().catch((error) => Routine.toast(error.message, "danger"));
  loadStartupStatus().catch(() => {});
  document.getElementById("settings-form").addEventListener("submit", saveSettings);
  document.getElementById("reset-settings").addEventListener("click", resetSettings);
  document.getElementById("quit-app").addEventListener("click", quitApp);
});

async function loadSettings() {
  const data = await Routine.requestJson("/api/settings");
  const settings = data.settings || {};
  field("app_name").value = settings.app_name || "Routine IA";
  field("theme").value = settings.theme || "dark";
  field("week_start").value = settings.week_start || "monday";
  field("auto_open_browser").checked = String(settings.auto_open_browser || "true") === "true";
  field("desktop_mode").checked = String(settings.desktop_mode || "true") === "true";
  field("low_friction_mode").checked = String(settings.low_friction_mode || "false") === "true";
  field("today_simplified_view").checked = String(settings.today_simplified_view || "false") === "true";
  field("start_with_windows").checked = String(settings.start_with_windows || "false") === "true";
  field("start_minimized").checked = String(settings.start_minimized || "false") === "true";
  field("run_in_background").checked = String(settings.run_in_background || "true") === "true";
  field("background_worker_enabled").checked = String(settings.background_worker_enabled || "true") === "true";
  field("auto_start_monitoring").checked = String(settings.auto_start_monitoring || "false") === "true";
  field("monitoring_worker_state").value = settings.monitoring_worker_state || "off";
  field("monitoring_interval_seconds").value = String(settings.monitoring_interval_seconds || "60");
  field("health_sync_base_path").value = settings.health_sync_base_path || "G:\\Meu Drive";
  field("health_auto_import_enabled").checked = String(settings.health_auto_import_enabled || "true") === "true";
  field("health_import_interval_hours").value = String(settings.health_import_interval_hours || "4");
  field("ai_evaluation_enabled").checked = String(settings.ai_evaluation_enabled || "true") === "true";
  field("ai_evaluation_model").value = settings.ai_evaluation_model || "gemma3:4b";
  field("ai_evaluation_url").value = settings.ai_evaluation_url || "http://127.0.0.1:11434";
  field("ai_evaluation_timeout_seconds").value = String(settings.ai_evaluation_timeout_seconds || "8");
}

async function saveSettings(event) {
  event.preventDefault();
  try {
    if (field("auto_start_monitoring").checked && field("monitoring_worker_state").value === "off") {
      field("monitoring_worker_state").value = "active";
    }
    await Routine.requestJson("/api/settings", {
      method: "POST",
      body: Routine.formToObject(document.getElementById("settings-form")),
    });
    await Routine.applySavedSettings();
    await loadStartupStatus();
    Routine.toast("Configurações salvas.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

async function resetSettings() {
  if (!Routine.confirmAction("Restaurar configuracoes padrao?")) return;
  try {
    await Routine.requestJson("/api/settings/reset", { method: "POST" });
    await loadSettings();
    await Routine.applySavedSettings();
    await loadStartupStatus();
    Routine.toast("Configuracoes padrao restauradas.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

async function loadStartupStatus() {
  const data = await Routine.requestJson("/api/settings/startup-status");
  const startup = data.startup || {};
  Routine.setText(
    "startup-status",
    startup.exists
      ? `Inicializacao do Windows ativa: ${startup.path}`
      : `Inicializacao do Windows desativada: ${startup.path || "-"}`
  );
}

async function quitApp() {
  if (!Routine.confirmAction("Encerrar o Routine IA de verdade?")) return;
  await Routine.requestJson("/api/app/quit", { method: "POST" });
  Routine.toast("Routine IA esta encerrando.");
}

function field(id) {
  return document.getElementById(id);
}
