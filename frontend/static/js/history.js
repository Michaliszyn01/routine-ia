let historyRows = [];

document.addEventListener("DOMContentLoaded", () => {
  setCurrentWeek();
  document.getElementById("history-filters").addEventListener("submit", (event) => {
    event.preventDefault();
    loadHistory().catch((error) => Routine.toast(error.message));
  });
  document.getElementById("current-week").addEventListener("click", () => {
    setCurrentWeek();
    loadHistory().catch((error) => Routine.toast(error.message));
  });
  document.getElementById("clear-filters").addEventListener("click", () => {
    document.getElementById("start").value = "";
    document.getElementById("end").value = "";
    loadHistory().catch((error) => Routine.toast(error.message));
  });
  document.getElementById("export-csv").addEventListener("click", exportCsv);
  loadHistory().catch((error) => Routine.toast(error.message));
});

function setCurrentWeek() {
  const range = Routine.currentWeekRange();
  document.getElementById("start").value = range.start;
  document.getElementById("end").value = range.end;
}

async function loadHistory() {
  const start = document.getElementById("start").value;
  const end = document.getElementById("end").value;
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const data = await Routine.requestJson(`/api/history?${params.toString()}`);
  historyRows = data.records;
  renderSummary(data.summary || {});
  renderHistory(historyRows);
}

function renderSummary(summary) {
  Routine.setText("history-average-score", Routine.number(summary.average_score, 1));
  Routine.setText("history-workout-hours", `${Routine.number(summary.total_workout_hours, 1)}h`);
  Routine.setText("history-study-hours", `${Routine.number(summary.total_study_hours, 1)}h`);
  Routine.setText("history-programming-hours", `${Routine.number(summary.total_programming_hours, 1)}h`);
  Routine.setText("history-reading-hours", `${Routine.number(summary.total_reading_hours, 1)}h`);
  Routine.setText("history-sleep", `${Routine.number(summary.average_sleep, 1)}h`);
  Routine.setText("history-steps", Routine.number(summary.total_steps));
  Routine.setText(
    "history-energy-mood",
    `${Routine.number(summary.average_energy, 1)}/${Routine.number(summary.average_mood, 1)}`
  );
  Routine.setText("history-nutrition", Routine.number(summary.nutrition_average, 1));
  Routine.setText("history-water", `${Routine.number(summary.water_average, 1)}L`);
}

function renderHistory(records) {
  const body = document.getElementById("history-body");
  if (!records.length) {
    body.innerHTML = '<tr><td colspan="15" class="muted">Nenhum registro encontrado.</td></tr>';
    return;
  }

  body.innerHTML = records
    .map(
      (record) => `
        <tr>
          <td>${Routine.formatDate(record.date)}</td>
          <td>${record.weekday}</td>
          <td><span class="badge ${Routine.getScoreClass(record.daily_score)}">${Routine.number(record.daily_score, 1)}</span></td>
          <td>${Routine.boolLabel(record.workout_done)} · ${Routine.number(record.workout_hours, 1)}h</td>
          <td>${Routine.boolLabel(record.study_done)} · ${Routine.number(record.study_hours, 1)}h</td>
          <td>${Routine.boolLabel(record.programming_done)} · ${Routine.number(record.programming_hours, 1)}h</td>
          <td>${Routine.boolLabel(record.reading_done)} · ${Routine.number(record.reading_hours, 1)}h</td>
          <td>${Routine.number(record.sleep_hours, 1)}h</td>
          <td>${Routine.number(record.steps)}</td>
          <td>${record.energy}</td>
          <td>${record.mood}</td>
          <td><span class="badge ${Routine.getScoreClass(record.nutrition_score)}">${Routine.number(record.nutrition_score, 1)}</span></td>
          <td>${Routine.number(record.water_liters, 1)}L</td>
          <td>${Routine.boolLabel(record.protein_ok)}</td>
          <td>${Routine.escapeHtml(record.observation || "")}</td>
        </tr>
      `
    )
    .join("");
}

function exportCsv() {
  if (!historyRows.length) {
    Routine.toast("Não há registros para exportar.");
    return;
  }

  const params = new URLSearchParams();
  const start = document.getElementById("start").value;
  const end = document.getElementById("end").value;
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const url = `/api/history/export?${params.toString()}`;
  const link = document.createElement("a");
  link.href = url;
  link.click();
  Routine.toast("Exportação CSV gerada.");
}
