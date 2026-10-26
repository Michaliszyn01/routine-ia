from __future__ import annotations

import json
from datetime import date

from .database import get_connection
from .validators import validate_date


def get_adhd_today(date_value: str | None = None) -> dict:
    target_date = validate_date(date_value or date.today().isoformat())
    from .checklists import list_checklists
    from .microtasks import list_microtasks
    from core.tools.monitoring.monitoring_repository import daily_summary
    from .life_os import get_bad_day, get_todays_habits, get_weekly_planner, life_goal_summary
    from .load_balance import get_load_balance
    from .models import get_daily_record, get_settings, week_range

    daily = get_daily_record(target_date) or {}
    habits = get_todays_habits(target_date)
    planner = get_weekly_planner(target_date)
    load = get_load_balance(target_date)
    usage = daily_summary(target_date)
    goals = life_goal_summary(target_date)
    bad_day = get_bad_day(target_date)
    week_start, week_end = week_range(target_date)

    command = get_next_action_context(target_date)
    action = command["primary_action"]
    focus = recommend_focus(target_date, action.get("category"))
    mode = _today_mode(daily, load, usage, bad_day)
    microtasks = list_microtasks(target_date)
    checklists = list_checklists(target_date, action.get("category"))
    minimum = get_minimum_day_save(target_date)
    settings = get_settings()

    return {
        "date": target_date,
        "week_start": week_start,
        "week_end": week_end,
        "mode": mode,
        "command_center": command,
        "next_action": action,
        "micro_steps": action.get("microsteps") or _micro_steps(action),
        "microtasks": microtasks,
        "checklist": checklists.get("suggested"),
        "checklists": checklists,
        "focus": focus,
        "rescue_actions": _rescue_actions(mode),
        "minimum_save": minimum,
        "low_friction_mode": str(settings.get("low_friction_mode") or "false") == "true",
        "signals": {
            "energy": int(float(daily.get("energy") or 0)),
            "mood": int(float(daily.get("mood") or 0)),
            "sleep_hours": float(daily.get("sleep_hours") or 0),
            "load_index": load.get("index", 0),
            "load_level": load.get("level", "leve"),
            "productive_minutes": usage.get("productive_minutes", 0),
            "distraction_minutes": usage.get("distraction_minutes", 0),
            "bad_day_logged": bool(bad_day.get("log")),
        },
    }


def get_next_action_context(date_value: str | None = None) -> dict:
    target_date = validate_date(date_value or date.today().isoformat())
    from core.tools.monitoring.monitoring_repository import daily_summary
    from .life_os import get_bad_day, get_todays_habits, get_weekly_planner, life_goal_summary
    from .load_balance import get_load_balance
    from .models import get_daily_record
    from .nutrition import get_nutrition_record

    daily = get_daily_record(target_date) or {}
    nutrition = get_nutrition_record(target_date) or {}
    usage = daily_summary(target_date)
    bad_day = get_bad_day(target_date)
    habits = get_todays_habits(target_date)
    planner = get_weekly_planner(target_date)
    goals = life_goal_summary(target_date)
    load = get_load_balance(target_date)

    energy = int(float(daily.get("energy") or 0))
    mood = int(float(daily.get("mood") or 0))
    sleep_hours = float(daily.get("sleep_hours") or 0)
    energy_band = _energy_band(energy)
    risk_level = "high" if float(usage.get("distraction_minutes") or 0) >= 90 else "moderate" if float(usage.get("distraction_minutes") or 0) >= 30 else "low"

    if bad_day.get("log"):
        action = _command_action(
            "Salvar rotina minima",
            "rotina",
            5,
            "Hoje ja esta em Modo Dia Ruim. O melhor e manter o minimo sem tentar compensar tudo.",
            ["Beber agua", "Registrar energia e humor", "Fazer 5 minutos de algo util", "Salvar minimo"],
            "Fechar o dia sem culpa",
            "minimum",
        )
        mode = "bad_day"
        urgency = "medium"
    elif energy and energy <= 2:
        action = _choose_small_unfinished_action(daily, planner, habits, goals, target_date, 5)
        action["reason"] = "Sua energia esta baixa, entao a melhor chance e comecar pequeno."
        mode = "low_energy"
        urgency = "medium"
    elif sleep_hours and sleep_hours < 7:
        action = _choose_small_unfinished_action(daily, planner, habits, goals, target_date, 10)
        action["reason"] = "Seu sono ficou abaixo de 7h. Um bloco curto protege energia e ainda conta."
        mode = "low_sleep"
        urgency = "medium"
    elif not int(daily.get("study_done") or 0) and _has_study_goal(goals):
        action = _command_action(
            "Fazer 5 minutos de matematica",
            "estudo",
            5,
            "Voce ainda nao estudou hoje e existe objetivo de estudo ativo. Cinco minutos ja reabrem o trilho.",
            ["Abrir o material", "Escolher 1 exercicio", "Fazer por 5 minutos", "Marcar dificuldade"],
            "Salvar minimo do dia",
            "daily_study",
        )
        mode = "study_recovery"
        urgency = "medium"
    elif not int(daily.get("programming_done") or 0):
        action = _command_action(
            "Abrir um projeto por 5 minutos",
            "programacao",
            5,
            "Programacao ainda nao apareceu no dia. A primeira acao e so abrir contexto.",
            ["Abrir VS Code", "Abrir o projeto", "Escolher uma tarefa pequena", "Rodar app ou teste"],
            "Organizar a proxima tarefa",
            "daily_programming",
        )
        mode = "programming_start"
        urgency = "low"
    elif float(usage.get("distraction_minutes") or 0) >= 60:
        action = _command_action(
            "Fazer um bloco protegido de foco",
            "trabalho",
            10,
            "A distracao ficou alta hoje. Um bloco curto com uma janela so ajuda a voltar.",
            ["Fechar abas extras", "Abrir so a ferramenta certa", "Iniciar timer", "Fazer 10 minutos"],
            "Beber agua e salvar minimo",
            "distraction_redirect",
        )
        mode = "redirect"
        urgency = "medium"
    elif _already_did_enough(daily):
        action = _command_action(
            "Fechar o dia com revisao leve",
            "rotina",
            5,
            "Voce ja fez bastante coisa. Agora vale consolidar sem inventar peso novo.",
            ["Salvar observacao", "Ver amanha", "Escolher 1 prioridade", "Encerrar"],
            "Salvar minimo do dia",
            "light_review",
        )
        mode = "wrap_up"
        urgency = "low"
    else:
        action = _choose_small_unfinished_action(daily, planner, habits, goals, target_date, 5)
        mode = "simple_start"
        urgency = "low"

    suggested_focus = "5_min_start" if action["estimated_minutes"] <= 5 else "short_block"
    return {
        "mode": mode,
        "primary_action": action,
        "reason": action["reason"],
        "estimated_minutes": action["estimated_minutes"],
        "microsteps": action["microsteps"],
        "fallback_action": action["fallback_action"],
        "urgency": urgency,
        "energy_band": energy_band,
        "risk_level": risk_level,
        "suggested_focus_mode": suggested_focus,
        "signals": {
            "energy": energy,
            "mood": mood,
            "sleep_hours": sleep_hours,
            "water_liters": float(nutrition.get("water_liters") or 0),
            "load_index": load.get("index", 0),
            "distraction_minutes": usage.get("distraction_minutes", 0),
            "bad_day_active": bool(bad_day.get("log")),
        },
    }


def cant_start(payload: dict) -> dict:
    energy = str(payload.get("energy_level") or "baixa").lower()
    area = str(payload.get("desired_area") or "organizar").lower()
    try:
        minutes = int(float(payload.get("available_minutes") or 5))
    except (TypeError, ValueError):
        minutes = 5
    minutes = min(max(minutes, 5), 15)
    category_map = {
        "estudar": "estudo",
        "estudo": "estudo",
        "programar": "programacao",
        "programacao": "programacao",
        "organizar": "rotina",
        "saude": "saude",
        "salvar": "rotina",
    }
    category = category_map.get(area, "rotina")
    title = {
        "estudo": f"Estudar por {minutes} minutos",
        "programacao": f"Abrir projeto por {minutes} minutos",
        "saude": "Cuidar do corpo no minimo",
        "rotina": "Salvar o minimo do dia",
    }.get(category, "Comecar pequeno")
    steps = _micro_steps({"title": title, "category": category})[:4]
    message = "Beleza. Vamos comecar pequeno. Nao precisa resolver tudo agora."
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO adhd_cant_start_logs (
                date, energy_level, desired_area, available_minutes, suggested_action
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (date.today().isoformat(), energy, area, minutes, title),
        )
    return {
        "suggested_action": title,
        "microsteps": [step["title"] for step in steps],
        "duration": minutes,
        "message": message,
        "start_focus_available": True,
    }


def recommend_focus(date_value: str | None = None, task_type: str | None = None) -> dict:
    target_date = validate_date(date_value or date.today().isoformat())
    from core.tools.monitoring.monitoring_repository import daily_summary
    from .focus_timer import focus_summary
    from .life_os import get_bad_day
    from .load_balance import get_load_balance
    from .models import get_daily_record, week_range

    daily = get_daily_record(target_date) or {}
    energy = int(float(daily.get("energy") or 3))
    sleep = float(daily.get("sleep_hours") or 0)
    mood = int(float(daily.get("mood") or 3))
    usage = daily_summary(target_date)
    load = get_load_balance(target_date)
    bad_day = get_bad_day(target_date)
    start, end = week_range(target_date)
    focus = focus_summary(start, end)

    if bad_day.get("log"):
        minutes, mode, label = 5, "bad_day", "Bloco minimo"
        reason = "Modo Dia Ruim ativo. Cinco minutos ja contam."
    elif energy <= 2 or mood <= 2:
        minutes, mode, label = 5 if sleep and sleep < 7 else 10, "low_energy", "Bloco leve"
        reason = "Sua energia esta baixa, entao um bloco curto tem mais chance de funcionar."
    elif energy == 3:
        minutes, mode, label = 15, "steady", "Bloco curto"
        reason = "Energia mediana combina com um bloco simples, sem virar maratona."
    else:
        minutes, mode, label = 25, "normal", "Bloco foco"
        reason = "Sua energia permite um bloco um pouco maior."

    if sleep and sleep < 7:
        minutes = min(minutes, 10)
        reason = "Sono abaixo de 7h. Melhor reduzir o bloco e proteger energia."
    if float(usage.get("distraction_minutes") or 0) >= 60:
        minutes = min(minutes, 10)
        mode = "distraction_redirect"
        reason = "Distracao alta hoje. Comece com um bloco protegido e menor."
    if int(load.get("index") or 0) >= 80:
        minutes = min(minutes, 10)
        reason = "Carga alta no dia. Bloco curto evita sobrecarga."

    return {
        "recommended_minutes": minutes,
        "minutes": minutes,
        "reason": reason,
        "mode": mode,
        "break_minutes": 3 if minutes <= 10 else 5,
        "label": label,
        "category": _focus_category(task_type),
        "weekly_focus_sessions": focus.get("sessions", 0),
    }


def save_minimum_day(payload: dict) -> dict:
    from .models import get_daily_record, upsert_daily_record

    date_value = validate_date(payload.get("date") or date.today().isoformat())
    energy = _clamp_int(payload.get("energy"), 1, 5, 3)
    mood = _clamp_int(payload.get("mood"), 1, 5, 3)
    sleep_hours = max(float(payload.get("sleep_hours") or 0), 0)
    note = str(payload.get("note") or payload.get("minimum_save_note") or "")[:1000]
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO minimum_day_saves (date, energy, mood, sleep_hours, note, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(date) DO UPDATE SET
                energy = excluded.energy,
                mood = excluded.mood,
                sleep_hours = excluded.sleep_hours,
                note = excluded.note,
                updated_at = CURRENT_TIMESTAMP
            """,
            (date_value, energy, mood, sleep_hours, note),
        )
    existing = get_daily_record(date_value) or {
        "date": date_value,
        "workout_done": 0,
        "workout_hours": 0,
        "study_done": 0,
        "study_hours": 0,
        "programming_done": 0,
        "programming_hours": 0,
        "reading_done": 0,
        "reading_hours": 0,
        "sleep_hours": sleep_hours,
        "steps": 0,
        "energy": energy,
        "mood": mood,
        "observation": "",
    }
    existing["energy"] = energy
    existing["mood"] = mood
    if sleep_hours:
        existing["sleep_hours"] = sleep_hours
    existing["observation"] = (existing.get("observation") or "") or note or "Dia salvo no minimo."
    daily = upsert_daily_record(existing)
    return {
        "success": True,
        "message": "Dia salvo no minimo. Isso ja conta como continuidade.",
        "streak_preserved": True,
        "next_suggestion": "Fechar sem culpa ou fazer so mais 5 minutos.",
        "minimum_save": get_minimum_day_save(date_value),
        "daily": daily,
    }


def get_minimum_day_save(date_value: str | None = None) -> dict | None:
    target_date = validate_date(date_value or date.today().isoformat())
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM minimum_day_saves WHERE date = ?", (target_date,)).fetchone()
    return dict(row) if row else None


def complete_command_center(payload: dict) -> dict:
    date_value = validate_date(payload.get("date") or date.today().isoformat())
    title = str(payload.get("action_title") or payload.get("title") or "Proxima acao")[:180]
    source_type = str(payload.get("source_type") or payload.get("source") or "command_center")[:80]
    source_id = str(payload.get("source_id") or "")[:80]
    note = str(payload.get("note") or "")[:1000]
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO command_center_completions (date, action_title, source_type, source_id, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date_value, title, source_type, source_id, note),
        )
        row = conn.execute("SELECT * FROM command_center_completions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return {"completion": dict(row), "message": "Boa. Voce comecou."}


BAD_DAY_PRESETS = {
    "sem_energia": ["beber agua", "registrar sono", "fazer 5 minutos de algo util", "comer uma refeicao simples", "fechar o dia sem culpa"],
    "travado": ["escolher uma tarefa pequena", "abrir o material", "fazer 5 minutos", "marcar como iniciado", "parar ou continuar"],
    "sobrecarregado": ["tirar uma coisa da lista", "respirar 30 segundos", "salvar minimo", "escolher so o proximo passo"],
    "sem_tempo": ["salvar minimo", "fazer 1 habito pequeno", "registrar observacao", "preparar amanha"],
    "baguncado": ["abrir tela Hoje", "salvar energia e humor", "escolher uma microtarefa", "organizar so uma coisa"],
    "emocionalmente_cansado": ["beber agua", "reduzir meta", "fazer uma acao gentil", "fechar sem culpa"],
    "dia_corrido": ["salvar minimo", "registrar nota rapida", "separar prioridade de amanha", "descansar"],
}


def get_bad_day_presets() -> dict:
    return {
        "presets": [
            {
                "key": key,
                "label": key.replace("_", " "),
                "actions": actions,
                "message": "Hoje nao precisa ser perfeito. O objetivo e manter o minimo.",
            }
            for key, actions in BAD_DAY_PRESETS.items()
        ]
    }


def start_bad_day(payload: dict) -> dict:
    from .life_os import save_bad_day

    preset = str(payload.get("preset") or "travado")
    actions = BAD_DAY_PRESETS.get(preset, BAD_DAY_PRESETS["travado"])
    result = save_bad_day({
        "date": payload.get("date"),
        "preset": preset,
        "reason": payload.get("reason") or preset.replace("_", " "),
        "actions_done": [],
        "note": payload.get("note") or "Modo Dia Ruim iniciado.",
    })
    return {"message": "Modo Dia Ruim ativado. O minimo ja e o plano.", "preset": preset, "actions": actions, **result}


def finish_bad_day(payload: dict) -> dict:
    from .life_os import save_bad_day

    preset = str(payload.get("preset") or "travado")
    actions = payload.get("minimum_actions_done") or payload.get("actions_done") or BAD_DAY_PRESETS.get(preset, [])
    result = save_bad_day({
        "date": payload.get("date"),
        "preset": preset,
        "reason": payload.get("reason") or preset.replace("_", " "),
        "actions_done": actions,
        "note": payload.get("note") or "Modo Dia Ruim finalizado.",
        "completed": True,
    })
    return {"message": "Dia ruim recuperado no minimo. Isso conta.", "preset": preset, **result}


def phase2_summary(start: str, end: str) -> dict:
    with get_connection() as conn:
        minimum = conn.execute(
            "SELECT COUNT(*) AS total, AVG(energy) AS energy_avg FROM minimum_day_saves WHERE date >= ? AND date <= ?",
            (start, end),
        ).fetchone()
        cant_start = conn.execute(
            "SELECT COUNT(*) AS total FROM adhd_cant_start_logs WHERE date >= ? AND date <= ?",
            (start, end),
        ).fetchone()
        completions = conn.execute(
            "SELECT COUNT(*) AS total FROM command_center_completions WHERE date >= ? AND date <= ?",
            (start, end),
        ).fetchone()
    return {
        "minimum_days": int(minimum["total"] or 0),
        "minimum_energy_average": round(float(minimum["energy_avg"] or 0), 1),
        "cant_start_uses": int(cant_start["total"] or 0),
        "command_completions": int(completions["total"] or 0),
    }


def _command_action(
    title: str,
    category: str,
    minutes: int,
    reason: str,
    microsteps: list[str],
    fallback: str,
    source: str,
) -> dict:
    clean_steps = microsteps[:5]
    return {
        "source": source,
        "source_id": None,
        "title": title,
        "category": category,
        "minutes": minutes,
        "estimated_minutes": minutes,
        "reason": reason,
        "microsteps": clean_steps,
        "fallback_action": fallback,
        "can_complete": False,
    }


def _choose_small_unfinished_action(daily: dict, planner: dict, habits: dict, goals: dict, target_date: str, minutes: int) -> dict:
    action = _next_action(target_date, daily, planner, habits, goals)
    title = action.get("title") or "Comecar com 5 minutos de uma tarefa importante"
    category = action.get("category") or "rotina"
    return _command_action(
        title,
        category,
        min(max(int(action.get("minutes") or minutes), 5), 10),
        action.get("reason") or "Ainda ha uma acao pequena que pode destravar o dia.",
        [step["title"] for step in _micro_steps(action)],
        "Salvar minimo do dia",
        action.get("source") or "next_action",
    ) | {
        "source_id": action.get("source_id"),
        "linked_project_id": action.get("linked_project_id"),
        "linked_goal_id": action.get("linked_goal_id"),
        "can_complete": bool(action.get("can_complete")),
    }


def _energy_band(energy: int) -> str:
    if energy <= 0:
        return "unknown"
    if energy <= 2:
        return "low"
    if energy == 3:
        return "medium"
    return "high"


def _has_study_goal(goals: dict) -> bool:
    main_goal = goals.get("main_goal") or {}
    area = str(main_goal.get("linked_area") or main_goal.get("title") or "").lower()
    return any(token in area for token in ["enem", "estudo", "matemat", "prova"]) or bool(goals.get("active_count"))


def _already_did_enough(daily: dict) -> bool:
    done = sum(
        1
        for key in ["workout_done", "study_done", "programming_done", "reading_done"]
        if int(daily.get(key) or 0)
    )
    return done >= 3 or float(daily.get("daily_score") or 0) >= 75


def _clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _next_action(target_date: str, daily: dict, planner: dict, habits: dict, goals: dict) -> dict:
    planner_items = planner.get("items") or []
    if not planner_items and planner.get("suggestion"):
        planner_items = planner["suggestion"].get("items") or []
    today_items = [
        item for item in planner_items
        if item.get("date") == target_date and not int(item.get("completed") or 0)
    ]
    if today_items:
        item = sorted(today_items, key=lambda row: (_category_rank(row.get("category")), int(row.get("id") or 999999)))[0]
        return {
            "source": "planner_item" if item.get("id") else "planner_suggestion",
            "source_id": item.get("id"),
            "title": item.get("title") or "Bloco planejado",
            "category": item.get("category") or "foco",
            "minutes": int(item.get("estimated_minutes") or 5),
            "linked_project_id": item.get("linked_project_id"),
            "linked_goal_id": item.get("linked_goal_id"),
            "reason": "item do plano semanal",
            "can_complete": bool(item.get("id")),
        }

    habit_items = habits.get("habits") or []
    incomplete_habit = next((item for item in habit_items if not int(item.get("completed") or 0)), None)
    if incomplete_habit:
        return {
            "source": "habit",
            "source_id": incomplete_habit.get("id"),
            "title": incomplete_habit.get("name") or "Habito minimo",
            "category": _habit_category(incomplete_habit.get("category")),
            "minutes": 5,
            "linked_project_id": None,
            "linked_goal_id": None,
            "reason": "habito ativo ainda nao feito",
            "can_complete": True,
        }

    if not int(daily.get("study_done") or 0):
        return _daily_action("daily_study", "Estudo minimo", "estudo", "manter sequencia de estudo")
    if not int(daily.get("programming_done") or 0):
        return _daily_action("daily_programming", "Abrir projeto por 5 minutos", "programacao", "reduzir barreira de inicio")
    if not int(daily.get("reading_done") or 0):
        return _daily_action("daily_reading", "Ler uma pagina", "leitura", "fechar uma acao pequena")

    main_goal = goals.get("main_goal")
    if main_goal:
        return {
            "source": "life_goal",
            "source_id": main_goal.get("id"),
            "title": f"Avancar: {main_goal.get('title')}",
            "category": main_goal.get("linked_area") or "foco",
            "minutes": 10,
            "linked_project_id": None,
            "linked_goal_id": main_goal.get("id"),
            "reason": "objetivo principal ativo",
            "can_complete": False,
        }

    return _daily_action("minimum", "Registrar o minimo de hoje", "rotina", "manter continuidade")


def _daily_action(source: str, title: str, category: str, reason: str) -> dict:
    return {
        "source": source,
        "source_id": None,
        "title": title,
        "category": category,
        "minutes": 5,
        "linked_project_id": None,
        "linked_goal_id": None,
        "reason": reason,
        "can_complete": False,
    }


def _focus_preset(action: dict, daily: dict, load: dict, usage: dict) -> dict:
    energy = int(float(daily.get("energy") or 0))
    mood = int(float(daily.get("mood") or 0))
    load_index = int(load.get("index") or 0)
    distraction = float(usage.get("distraction_minutes") or 0)
    action_minutes = int(action.get("minutes") or 5)

    if energy and energy <= 2 or mood and mood <= 2 or load_index >= 80:
        minutes = 5
        label = "resgate"
    elif load_index >= 65 or distraction >= 30:
        minutes = 10
        label = "curto"
    elif action_minutes <= 15:
        minutes = max(5, min(15, action_minutes))
        label = "micro"
    else:
        minutes = 15
        label = "padrao"

    return {
        "minutes": minutes,
        "break_minutes": 2 if minutes <= 10 else 5,
        "category": _focus_category(action.get("category")),
        "label": label,
        "note": f"Inicio guiado: {action.get('title')}",
        "linked_project_id": action.get("linked_project_id"),
    }


def _today_mode(daily: dict, load: dict, usage: dict, bad_day: dict) -> dict:
    if bad_day.get("log"):
        return {"key": "minimum", "label": "modo minimo", "tone": "warning"}
    energy = int(float(daily.get("energy") or 0))
    mood = int(float(daily.get("mood") or 0))
    if energy and energy <= 2 or mood and mood <= 2:
        return {"key": "rescue", "label": "resgate", "tone": "danger"}
    if int(load.get("index") or 0) >= 70:
        return {"key": "light", "label": "leve", "tone": "warning"}
    if float(usage.get("distraction_minutes") or 0) > float(usage.get("productive_minutes") or 0) and usage.get("total_seconds"):
        return {"key": "redirect", "label": "redirecionar", "tone": "info"}
    return {"key": "normal", "label": "acao simples", "tone": "success"}


def _micro_steps(action: dict) -> list[dict]:
    category = _focus_category(action.get("category"))
    title = action.get("title") or "acao"
    presets = {
        "estudo": ["Abrir o material certo", "Fazer uma questao ou um resumo curto", "Marcar o que travou"],
        "programacao": ["Abrir o projeto", "Escolher um arquivo ou erro pequeno", "Fazer uma mudanca minima"],
        "leitura": ["Abrir o livro ou artigo", "Ler uma pagina", "Anotar uma frase util"],
        "treino": ["Trocar de roupa ou separar tenis", "Aquecer por 3 minutos", "Fazer o primeiro bloco"],
        "trabalho": ["Abrir a ferramenta certa", "Definir a primeira entrega minima", "Executar por 5 minutos"],
    }
    steps = presets.get(category) or ["Abrir o contexto certo", f"Fazer 5 minutos de {title}", "Registrar o minimo feito"]
    return [{"order": index + 1, "title": step, "done": False} for index, step in enumerate(steps)]


def _rescue_actions(mode: dict) -> list[str]:
    actions = ["Beber agua", "Respirar 30 segundos", "Deixar so a janela necessaria aberta", "Comecar 5 minutos"]
    if mode.get("key") in {"rescue", "minimum"}:
        actions.insert(2, "Reduzir a meta para uma acao minima")
    return actions


def _category_rank(category: str | None) -> int:
    order = {
        "foco": 0,
        "estudo": 1,
        "programacao": 2,
        "projetos": 3,
        "treino": 4,
        "revisao": 5,
    }
    return order.get((category or "").lower(), 9)


def _habit_category(category: str | None) -> str:
    value = (category or "").lower()
    if "estudo" in value:
        return "estudo"
    if "program" in value:
        return "programacao"
    if "saude" in value:
        return "treino"
    return "habitos"


def _focus_category(category: str | None) -> str:
    value = (category or "").lower()
    if value in {"estudo", "programacao", "leitura", "trabalho"}:
        return value
    if value in {"projetos", "foco"}:
        return "programacao"
    return "outro"
