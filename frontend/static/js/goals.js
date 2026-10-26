const goalLabels = {
  workout: "Treino",
  study: "Estudo",
  programming: "Programação",
  reading: "Leitura",
  sleep: "Sono",
};

document.addEventListener("DOMContentLoaded", () => {
  loadGoals().catch((error) => Routine.toast(error.message));
  loadSmartGoals().catch((error) => Routine.toast(error.message));
  document.getElementById("goals-form").addEventListener("submit", saveGoals);
  document.getElementById("reset-goals").addEventListener("click", resetGoals);
  document.getElementById("refresh-smart-goals").addEventListener("click", () => {
    loadSmartGoals().catch((error) => Routine.toast(error.message, "danger"));
  });
});

async function loadGoals() {
  const data = await Routine.requestJson("/api/goals");
  renderGoals(data.goals);
  updateWeightWarning();
}

function renderGoals(goals) {
  const body = document.getElementById("goals-body");
  body.innerHTML = goals
    .map(
      (goal) => `
        <tr data-category="${goal.category}">
          <td><strong>${Routine.escapeHtml(goal.label || goalLabels[goal.category] || goal.category)}</strong></td>
          <td><input data-field="weekly_days_goal" type="number" min="0" max="7" step="1" value="${goal.weekly_days_goal}"></td>
          <td><input data-field="daily_hours_goal" type="number" min="0" step="0.25" value="${goal.daily_hours_goal}"></td>
          <td><input data-field="weekly_hours_goal" type="number" min="0" step="0.25" value="${goal.weekly_hours_goal}"></td>
          <td><input data-field="daily_weight" type="number" min="0" step="1" value="${goal.daily_weight}"></td>
          <td><input data-field="max_daily_hours" type="number" min="0" step="0.25" value="${goal.max_daily_hours}"></td>
          <td><input data-field="active" type="checkbox" ${Number(goal.active) ? "checked" : ""}></td>
        </tr>
      `
    )
    .join("");

  body.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", updateWeightWarning);
    input.addEventListener("change", updateWeightWarning);
  });
}

async function saveGoals(event) {
  event.preventDefault();
  const rows = [...document.querySelectorAll("#goals-body tr")];
  const goals = rows.map((row) => ({ category: row.dataset.category, ...collectGoalPayload(row) }));
  try {
    await Routine.requestJson("/api/goals", {
      method: "POST",
      body: { goals },
    });
    await loadGoals();
    Routine.toast("Metas salvas.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

async function resetGoals() {
  try {
    await Routine.requestJson("/api/goals/reset", { method: "POST" });
    await loadGoals();
    Routine.toast("Metas padrão restauradas.");
  } catch (error) {
    Routine.toast(error.message, "danger");
  }
}

function collectGoalPayload(row) {
  const payload = {};
  row.querySelectorAll("[data-field]").forEach((input) => {
    const field = input.dataset.field;
    payload[field] = input.type === "checkbox" ? input.checked : input.value;
  });
  return payload;
}

function updateWeightWarning() {
  const rows = [...document.querySelectorAll("#goals-body tr")];
  const total = rows.reduce((sum, row) => {
    const active = row.querySelector('[data-field="active"]').checked;
    const weight = Number(row.querySelector('[data-field="daily_weight"]').value || 0);
    return active ? sum + weight : sum;
  }, 0);

  Routine.setText("goal-weight-sum", `Peso total: ${Routine.number(total)}`);
  const warning = document.getElementById("weight-warning");
  warning.textContent = `A soma dos pesos está em ${Routine.number(total)}. O ideal é fechar 100 para manter a pontuação equilibrada.`;
  warning.classList.toggle("hidden", Math.round(total) === 100);
}

async function loadSmartGoals() {
  const data = await Routine.requestJson("/api/smart-goals");
  renderSmartGoals(data.suggestions || []);
}

function renderSmartGoals(suggestions) {
  const target = document.getElementById("smart-goals-list");
  if (!suggestions.length) {
    target.innerHTML = '<div class="empty-state">Nenhuma sugestao no momento.</div>';
    return;
  }
  target.innerHTML = suggestions
    .map(
      (item) => `
        <article class="suggestion-card" data-suggestion='${Routine.escapeHtml(JSON.stringify(item))}'>
          <span class="pill">${Routine.escapeHtml(item.category)}</span>
          <h3>${Routine.escapeHtml(item.diagnosis)}</h3>
          <p>${Routine.escapeHtml(item.suggestion)}</p>
          <small>${Routine.escapeHtml(item.impact)}</small>
          <div class="form-actions">
            <button class="button primary apply-suggestion" type="button" ${item.applicable ? "" : "disabled"}>Aplicar sugestao</button>
            <button class="button ghost ignore-suggestion" type="button">Ignorar</button>
          </div>
        </article>
      `
    )
    .join("");

  target.querySelectorAll(".apply-suggestion").forEach((button) => {
    button.addEventListener("click", async () => {
      const card = button.closest(".suggestion-card");
      const suggestion = JSON.parse(card.dataset.suggestion);
      try {
        await Routine.requestJson("/api/smart-goals/apply", {
          method: "POST",
          body: suggestion,
        });
        await loadGoals();
        await loadSmartGoals();
        Routine.toast("Sugestao aplicada.");
      } catch (error) {
        Routine.toast(error.message, "danger");
      }
    });
  });

  target.querySelectorAll(".ignore-suggestion").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest(".suggestion-card").remove();
    });
  });
}
