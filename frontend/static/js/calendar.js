let calendarData = null;

document.addEventListener("DOMContentLoaded", () => {
  const monthInput = document.getElementById("calendar-month");
  monthInput.value = Routine.todayISO().slice(0, 7);
  monthInput.addEventListener("change", loadCalendar);
  loadCalendar().catch((error) => Routine.toast(error.message, "danger"));
});

async function loadCalendar() {
  const month = document.getElementById("calendar-month").value;
  calendarData = await Routine.requestJson(`/api/calendar?month=${encodeURIComponent(month)}`);
  Routine.setText("calendar-title", `Calendário ${calendarData.month_label}`);
  renderCalendar(calendarData);
}

function renderCalendar(data) {
  const grid = document.getElementById("calendar-grid");
  const blanks = Array.from({ length: data.first_weekday }, () => '<div class="calendar-empty-cell"></div>');
  const days = data.days.map(renderCalendarDay);
  grid.innerHTML = [...blanks, ...days].join("");
  grid.querySelectorAll(".calendar-day").forEach((button) => {
    button.addEventListener("click", () => showDayDetail(button.dataset.date));
  });
  const firstDay = data.days[0];
  if (firstDay) showDayDetail(firstDay.date);
}

function renderCalendarDay(day) {
  const indicators = Object.entries(day.indicators || {})
    .filter(([, active]) => active)
    .map(([key]) => `<span class="day-dot ${key}" title="${key}"></span>`)
    .join("");
  return `
    <button class="calendar-day calendar-day-${day.score_class}" data-date="${day.date}" type="button">
      <strong>${day.day}</strong>
      <span>${day.score === null ? "-" : Routine.number(day.score, 0)}</span>
      <div class="day-dots">${indicators}</div>
    </button>
  `;
}

function showDayDetail(dateValue) {
  const day = calendarData.days.find((item) => item.date === dateValue);
  const target = document.getElementById("calendar-day-detail");
  if (!day) return;
  document.querySelectorAll(".calendar-day").forEach((button) => {
    button.classList.toggle("selected", button.dataset.date === dateValue);
  });
  const daily = day.daily || {};
  const nutrition = day.nutrition || {};
  target.classList.remove("muted");
  target.innerHTML = `
    <div class="day-detail-head">
      <strong>${Routine.formatDate(day.date)}</strong>
      <span class="badge ${day.score === null ? "badge-warning" : Routine.getScoreClass(day.score)}">${day.score === null ? "Sem registro" : Routine.number(day.score, 1)}</span>
    </div>
    <dl class="detail-list">
      <div><dt>Treino</dt><dd>${Routine.boolLabel(daily.workout_done)} · ${Routine.number(daily.workout_hours, 1)}h</dd></div>
      <div><dt>Estudo</dt><dd>${Routine.boolLabel(daily.study_done)} · ${Routine.number(daily.study_hours, 1)}h</dd></div>
      <div><dt>Programação</dt><dd>${Routine.boolLabel(daily.programming_done)} · ${Routine.number(daily.programming_hours, 1)}h</dd></div>
      <div><dt>Leitura</dt><dd>${Routine.boolLabel(daily.reading_done)} · ${Routine.number(daily.reading_hours, 1)}h</dd></div>
      <div><dt>Sono</dt><dd>${Routine.number(daily.sleep_hours, 1)}h</dd></div>
      <div><dt>Alimentação</dt><dd>${Routine.number(nutrition.nutrition_score, 1)} · ${Routine.number(nutrition.water_liters, 1)}L</dd></div>
      <div><dt>Foco</dt><dd>${day.focus_sessions} sessão(ões)</dd></div>
      <div><dt>Projetos</dt><dd>${Routine.number(day.project_minutes / 60, 1)}h</dd></div>
    </dl>
    <div class="form-actions">
      <a class="button primary" href="/daily?date=${encodeURIComponent(day.date)}">Editar dia</a>
      <a class="button secondary" href="/today?date=${encodeURIComponent(day.date)}">Abrir Hoje</a>
    </div>
  `;
}
