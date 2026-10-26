document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("bad-day-date").value = Routine.todayISO();
  document.getElementById("bad-day-date").addEventListener("change", loadBadDay);
  document.getElementById("bad-day-form").addEventListener("submit", saveBadDay);
  loadBadDay();
});
async function loadBadDay() {
  const date = document.getElementById("bad-day-date").value;
  const data = await Routine.requestJson(`/api/bad-day?date=${date}`);
  Routine.setText("bad-day-message", data.message);
  const done = new Set(data.actions_done || []);
  document.getElementById("bad-day-actions").innerHTML = data.actions.map(action => `<label class="toggle-row bad-day-item"><input type="checkbox" value="${Routine.escapeHtml(action)}" ${done.has(action) ? "checked" : ""}><span>${Routine.escapeHtml(action)}</span></label>`).join("");
}
async function saveBadDay(event) {
  event.preventDefault();
  const form = event.target;
  const payload = Routine.formToObject(form);
  payload.minimum_actions_done = [...document.querySelectorAll("#bad-day-actions input:checked")].map(input => input.value);
  await Routine.requestJson("/api/bad-day/save", {method:"POST", body: payload});
  Routine.toast("Continuidade minima salva.");
  loadBadDay();
}
