const nutritionCharts = {};

document.addEventListener("DOMContentLoaded", () => {
  field("nutrition-date").value = Routine.todayISO();
  field("nutrition-date").addEventListener("change", () => loadNutrition().catch(showError));
  field("nutrition-form").addEventListener("submit", saveNutrition);
  field("nutrition-load-today").addEventListener("click", () => {
    field("nutrition-date").value = Routine.todayISO();
    loadNutrition().catch(showError);
  });
  field("nutrition-export").addEventListener("click", () => {
    window.location.href = "/api/nutrition/export";
  });
  loadNutrition().catch(showError);
});

async function loadNutrition() {
  const date = field("nutrition-date").value;
  const data = await Routine.requestJson(`/api/nutrition?date=${encodeURIComponent(date)}`);
  fillNutrition(data.record || {});
  renderNutritionSummary(data.summary || {});
  const range = Routine.currentWeekRange();
  const history = await Routine.requestJson(`/api/nutrition/history?start=${range.start}&end=${range.end}`);
  renderNutritionHistory(history.records || []);
}

async function saveNutrition(event) {
  event.preventDefault();
  try {
    const result = await Routine.requestJson("/api/nutrition", {
      method: "POST",
      body: collectNutritionPayload(),
    });
    fillNutrition(result.record);
    await loadNutrition();
    Routine.toast("Alimentacao salva.");
  } catch (error) {
    showError(error);
  }
}

function collectNutritionPayload() {
  return {
    date: value("nutrition-date"),
    breakfast_done: checked("breakfast-done"),
    lunch_done: checked("lunch-done"),
    dinner_done: checked("dinner-done"),
    healthy_snack_done: checked("healthy-snack-done"),
    water_liters: value("water-liters"),
    protein_ok: checked("protein-ok"),
    fruits_vegetables_ok: checked("fruits-vegetables-ok"),
    ultra_processed_control: checked("ultra-processed-control"),
    meals_count: value("meals-count"),
    observation: value("nutrition-observation"),
  };
}

function fillNutrition(record) {
  setChecked("breakfast-done", record.breakfast_done);
  setChecked("lunch-done", record.lunch_done);
  setChecked("dinner-done", record.dinner_done);
  setChecked("healthy-snack-done", record.healthy_snack_done);
  setValue("water-liters", record.water_liters || 0);
  setChecked("protein-ok", record.protein_ok);
  setChecked("fruits-vegetables-ok", record.fruits_vegetables_ok);
  setChecked("ultra-processed-control", record.ultra_processed_control);
  setValue("meals-count", record.meals_count || 0);
  setValue("nutrition-observation", record.observation || "");
  Routine.setText("nutrition-score", Routine.number(record.nutrition_score || 0, 1));
}

function renderNutritionSummary(summary) {
  Routine.setText("nutrition-week-score", Routine.number(summary.average_score, 1));
  Routine.setText("nutrition-week-water", `${Routine.number(summary.average_water, 1)}L`);
  Routine.setText("nutrition-week-protein", summary.protein_days || 0);
  Routine.setText("nutrition-week-meals", summary.three_meals_days || 0);
  document.getElementById("nutrition-insights").innerHTML = (summary.insights || [])
    .map((item) => `<li>${Routine.escapeHtml(item)}</li>`)
    .join("");
  drawNutritionChart("nutrition-score-chart", "Nota", summary.labels || [], summary.score_by_day || [], "#38b99b", 100);
  drawNutritionChart("nutrition-water-chart", "Agua", summary.labels || [], summary.water_by_day || [], "#73a2f5", 3);
}

function renderNutritionHistory(records) {
  const body = field("nutrition-history-body");
  if (!records.length) {
    body.innerHTML = '<tr><td colspan="7" class="muted">Nenhum registro alimentar.</td></tr>';
    return;
  }
  body.innerHTML = records
    .map(
      (record) => `
        <tr>
          <td>${Routine.formatDate(record.date)}</td>
          <td><span class="badge ${Routine.getScoreClass(record.nutrition_score)}">${Routine.number(record.nutrition_score, 1)}</span></td>
          <td>${Routine.number(record.water_liters, 1)}L</td>
          <td>${Routine.boolLabel(record.protein_ok)}</td>
          <td>${Routine.boolLabel(record.fruits_vegetables_ok)}</td>
          <td>${record.meals_count}</td>
          <td>${Routine.escapeHtml(record.observation || "")}</td>
        </tr>
      `
    )
    .join("");
}

function drawNutritionChart(id, label, labels, values, color, max) {
  const canvas = field(id);
  if (!canvas || !window.Chart) return;
  if (nutritionCharts[id]) nutritionCharts[id].destroy();
  nutritionCharts[id] = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label,
          data: values,
          borderColor: color,
          backgroundColor: `${color}22`,
          fill: true,
          tension: 0.35,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, suggestedMax: max } },
    },
  });
}

function field(id) {
  return document.getElementById(id);
}

function value(id) {
  return field(id).value;
}

function checked(id) {
  return field(id).checked;
}

function setValue(id, value) {
  field(id).value = value ?? "";
}

function setChecked(id, value) {
  field(id).checked = Boolean(Number(value));
}

function showError(error) {
  Routine.toast(error.message, "danger");
}
