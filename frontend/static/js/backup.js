document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("create-backup").addEventListener("click", createBackup);
  document.getElementById("open-data-dir").addEventListener("click", openDataDir);
  document.getElementById("export-history").addEventListener("click", () => {
    window.location.href = "/api/history/export";
  });
  document.getElementById("export-health").addEventListener("click", () => {
    window.location.href = "/api/health/export";
  });
  document.getElementById("export-nutrition").addEventListener("click", () => {
    window.location.href = "/api/nutrition/export";
  });
  document.getElementById("export-focus").addEventListener("click", () => {
    window.location.href = "/api/focus/export";
  });
  document.getElementById("export-projects").addEventListener("click", () => {
    window.location.href = "/api/projects/export";
  });
  document.getElementById("export-project-time").addEventListener("click", () => {
    window.location.href = "/api/projects/time/export";
  });
  document.getElementById("export-weekly-pdf").addEventListener("click", () => {
    window.location.href = `/api/reports/weekly/pdf?week_start=${Routine.currentWeekRange().start}`;
  });
  document.getElementById("refresh-backups").addEventListener("click", loadBackups);
  document.getElementById("backup-settings-form").addEventListener("submit", saveBackupSettings);

  loadPaths().catch((error) => Routine.toast(error.message, "danger"));
  loadBackups().catch((error) => Routine.toast(error.message, "danger"));
  loadBackupSettings().catch((error) => Routine.toast(error.message, "danger"));
});

async function loadPaths() {
  const paths = await Routine.requestJson("/api/app/paths");
  Routine.setText("database-path", paths.database_path);
  Routine.setText("backups-dir", paths.backups_dir);
  Routine.setText("exports-dir", paths.exports_dir);
}

async function loadBackups() {
  const data = await Routine.requestJson("/api/backup/list");
  renderBackups(data.backups || []);
}

async function createBackup() {
  const button = document.getElementById("create-backup");
  Routine.setButtonLoading(button, true, "Criando...");
  try {
    await Routine.requestJson("/api/backup/create", { method: "POST" });
    await loadBackups();
    Routine.toast("Backup criado com sucesso.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  } finally {
    Routine.setButtonLoading(button, false);
  }
}

async function openDataDir() {
  try {
    await Routine.requestJson("/api/app/open-data-dir", { method: "POST" });
  } catch (error) {
    Routine.toast(error.message, "warning");
  }
}

function renderBackups(backups) {
  const body = document.getElementById("backup-body");
  if (!backups.length) {
    body.innerHTML = '<tr><td colspan="5" class="muted">Nenhum backup criado ainda.</td></tr>';
    return;
  }

  body.innerHTML = backups
    .map(
      (backup) => `
        <tr>
          <td><code>${Routine.escapeHtml(backup.filename)}</code></td>
          <td><span class="badge ${backup.status === "success" ? "badge-success" : "badge-danger"}">${Routine.escapeHtml(backup.status)}</span></td>
          <td>${Routine.formatFileSize(backup.size)}</td>
          <td>${Routine.formatDateTime(backup.created_at)}</td>
          <td>${Routine.escapeHtml(backup.message || "")}</td>
        </tr>
      `
    )
    .join("");
}

async function loadBackupSettings() {
  const data = await Routine.requestJson("/api/backup/settings");
  const settings = data.settings || {};
  document.getElementById("backup-enabled").checked = Boolean(Number(settings.enabled));
  document.getElementById("backup-frequency").value = settings.frequency || "daily";
  document.getElementById("backup-keep-last").value = settings.keep_last || 10;
  Routine.setText(
    "backup-auto-status",
    Number(settings.enabled) ? `Ativo · ${settings.frequency}` : "Desativado"
  );
}

async function saveBackupSettings(event) {
  event.preventDefault();
  try {
    await Routine.requestJson("/api/backup/settings", {
      method: "POST",
      body: {
        enabled: document.getElementById("backup-enabled").checked,
        frequency: document.getElementById("backup-frequency").value,
        keep_last: document.getElementById("backup-keep-last").value,
      },
    });
    await loadBackupSettings();
    Routine.toast("Configuracao de backup salva.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}
