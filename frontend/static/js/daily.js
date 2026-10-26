let dailyState = {
  date: "",
  daily: {},
  nutrition: {},
};

document.addEventListener("DOMContentLoaded", () => {
  renderDailyShell();
  const params = new URLSearchParams(window.location.search);
  field("date").value = params.get("date") || Routine.todayISO();
  bindDailyMvp();
  loadDaily(field("date").value).catch((error) => Routine.toast(error.message, "danger"));
});

function renderDailyShell() {
  const content = document.querySelector(".content");
  if (!content) return;
  content.innerHTML = `
    <section class="page-intro mvp-intro">
      <h1>Registrar</h1>
      <p>Registro rápido. Dois minutos, sem planejar o dia inteiro.</p>
    </section>

    <section class="mvp-layout daily-mvp-layout">
      <form id="daily-form" class="panel form-panel mvp-quick-form">
        <div class="panel-heading">
          <div>
            <h2>Registro do dia</h2>
            <span id="record-status" class="pill">Novo registro</span>
          </div>
          <input id="date" name="date" type="date" required>
        </div>

        <div class="mvp-field-grid">
          <label class="toggle-row"><input id="study_done" type="checkbox"><span>ENEM feito?</span></label>
          <label><span>Tempo de estudo (min)</span><input id="study_minutes" type="number" min="0" max="1440" step="5" value="0"></label>
          <label class="toggle-row"><input id="workout_done" type="checkbox"><span>Treino/mobilidade feito?</span></label>
          <label class="toggle-row"><input id="decent_meal_done" type="checkbox"><span>Refeição decente além do almoço?</span></label>
          <label><span>Tempo de jogo (min)</span><input id="game_minutes" type="number" min="0" max="1440" step="5" value="0"></label>
          <label><span>Tempo de projeto (min)</span><input id="project_minutes" type="number" min="0" max="1440" step="5" value="0"></label>
          <label><span>Sono (h)</span><input id="sleep_hours" type="number" min="0" max="24" step="0.25" value="0"></label>
          <label><span>Energia 1 a 5</span><input id="energy" type="range" min="1" max="5" step="1" value="3"><output id="energy-output">3</output></label>
          <label><span>Humor 1 a 5</span><input id="mood" type="range" min="1" max="5" step="1" value="3"><output id="mood-output">3</output></label>
          <label class="wide-field"><span>Observação curta</span><textarea id="observation" rows="3" maxlength="280"></textarea></label>
        </div>

        <div class="form-actions">
          <button class="button primary" type="submit">Salvar registro</button>
          <button class="button secondary" type="button" id="save-and-close">Salvar e voltar para Hoje</button>
          <a class="button ghost" href="/today">Cancelar</a>
        </div>
      </form>

      <aside class="mvp-side">
        <article class="panel mvp-alert-panel">
          <div class="panel-heading"><h2>Regra simples</h2></div>
          <p>Registre só o que muda a próxima decisão: ENEM, corpo, refeição, jogo, projeto, sono, energia e humor.</p>
        </article>
      </aside>
    </section>
  `;
}

function bindDailyMvp() {
  field("date").addEventListener("change", () => {
    loadDaily(field("date").value).catch((error) => Routine.toast(error.message, "danger"));
  });
  ["energy", "mood"].forEach((id) => {
    field(id).addEventListener("input", () => Routine.setText(`${id}-output`, field(id).value));
  });
  field("daily-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    await saveDaily(false);
  });
  field("save-and-close").addEventListener("click", async () => {
    await saveDaily(true);
  });
}

async function loadDaily(dateValue) {
  const data = await Routine.requestJson(`/api/today?date=${encodeURIComponent(dateValue)}`);
  dailyState = {
    date: data.date,
    daily: data.daily || {},
    nutrition: data.nutrition || {},
  };
  fillDaily();
}

function fillDaily() {
  const daily = dailyState.daily || {};
  const nutrition = dailyState.nutrition || {};
  field("date").value = dailyState.date;
  field("study_done").checked = Boolean(Number(daily.study_done || 0)) || Number(daily.study_hours || 0) > 0;
  field("study_minutes").value = minutes(daily.study_hours);
  field("workout_done").checked = Boolean(Number(daily.workout_done || 0));
  field("decent_meal_done").checked = Boolean(Number(nutrition.dinner_done || 0)) || Boolean(Number(nutrition.healthy_snack_done || 0));
  field("game_minutes").value = minutes(daily.game_hours);
  field("project_minutes").value = minutes(daily.programming_hours);
  field("sleep_hours").value = daily.sleep_hours || 0;
  field("energy").value = daily.energy || 3;
  field("mood").value = daily.mood || 3;
  field("observation").value = daily.observation || "";
  Routine.setText("energy-output", field("energy").value);
  Routine.setText("mood-output", field("mood").value);
  Routine.setText("record-status", daily.date ? "Editando registro" : "Novo registro");
}

async function saveDaily(closeAfter) {
  const daily = {
    ...dailyState.daily,
    date: field("date").value,
    study_done: field("study_done").checked,
    study_hours: hoursFromMinutes(field("study_minutes").value),
    workout_done: field("workout_done").checked,
    workout_hours: field("workout_done").checked ? Math.max(Number(dailyState.daily.workout_hours || 0), 0.17) : 0,
    programming_done: Number(field("project_minutes").value || 0) > 0,
    programming_hours: hoursFromMinutes(field("project_minutes").value),
    game_hours: hoursFromMinutes(field("game_minutes").value),
    sleep_hours: field("sleep_hours").value,
    energy: field("energy").value,
    mood: field("mood").value,
    observation: field("observation").value,
  };
  const nutrition = {
    ...dailyState.nutrition,
    date: field("date").value,
    dinner_done: field("decent_meal_done").checked,
  };
  const result = await Routine.requestJson("/api/today", {
    method: "POST",
    body: { date: field("date").value, daily, nutrition },
  });
  dailyState = {
    date: result.date,
    daily: result.daily || {},
    nutrition: result.nutrition || {},
  };
  fillDaily();
  Routine.toast("Registro salvo.");
  if (closeAfter) window.location.href = "/today";
}

function hoursFromMinutes(value) {
  return Math.round((Number(value || 0) / 60) * 100) / 100;
}

function minutes(hours) {
  return Math.round(Number(hours || 0) * 60);
}

function field(id) {
  return document.getElementById(id);
}
