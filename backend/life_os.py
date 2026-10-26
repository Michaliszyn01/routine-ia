from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from .database import get_connection
from .validators import bool_to_int, sanitize_text, validate_date


LIFE_GOAL_CATEGORIES = {"Estudos", "Carreira", "Saude", "Projetos", "Espiritualidade", "Financeiro", "Pessoal", "Outro"}
LIFE_GOAL_PRIORITIES = {"baixa", "media", "alta", "maxima"}
LIFE_GOAL_STATUSES = {"ativo", "pausado", "concluido", "arquivado"}
LINKED_AREAS = {"estudo", "programacao", "treino", "alimentacao", "foco", "projetos", "saude", "habitos"}
HABIT_CATEGORIES = {"Estudos", "Saude", "Espiritualidade", "Organizacao", "Programacao", "Casa", "Social", "Outro"}
HABIT_FREQUENCIES = {"diaria", "semanal", "personalizada"}
STUDY_SUBJECTS = {"Matematica", "Linguagens", "Humanas", "Natureza", "Redacao", "Ingles", "Programacao", "Outro"}
ERROR_TYPES = {"conteudo", "interpretacao", "atencao", "calculo", "tempo", "chute", "revisao insuficiente"}
WEEKDAYS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
BAD_DAY_ACTIONS = [
    "Beber agua",
    "Registrar sono",
    "Fazer 20 minutos de estudo ou programacao",
    "Organizar uma pequena tarefa",
    "Comer uma refeicao decente",
    "Dormir mais cedo",
    "Registrar observacao do dia",
]


def today_iso() -> str:
    return date.today().isoformat()


def week_range(reference_date: str | None = None) -> tuple[str, str]:
    current = _parse_date(reference_date or today_iso())
    start = current - timedelta(days=current.weekday())
    end = start + timedelta(days=6)
    return start.isoformat(), end.isoformat()


def list_life_goals(include_archived: bool = False) -> list[dict]:
    query = "SELECT * FROM life_goals"
    params: list = []
    if not include_archived:
        query += " WHERE status != ?"
        params.append("arquivado")
    query += " ORDER BY CASE priority WHEN 'maxima' THEN 1 WHEN 'alta' THEN 2 WHEN 'media' THEN 3 ELSE 4 END, target_date IS NULL, target_date ASC, updated_at DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row(row) for row in rows]


def get_life_goal(goal_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM life_goals WHERE id = ?", (goal_id,)).fetchone()
    return _row(row) if row else None


def save_life_goal(payload: dict, goal_id: int | None = None) -> dict:
    data = _life_goal_payload(payload)
    with get_connection() as conn:
        if goal_id:
            conn.execute(
                """
                UPDATE life_goals
                SET title = ?, description = ?, category = ?, priority = ?, status = ?,
                    target_date = ?, linked_area = ?, progress_percent = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    data["title"], data["description"], data["category"], data["priority"],
                    data["status"], data["target_date"], data["linked_area"],
                    data["progress_percent"], goal_id,
                ),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO life_goals (
                    title, description, category, priority, status, target_date, linked_area, progress_percent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["title"], data["description"], data["category"], data["priority"],
                    data["status"], data["target_date"], data["linked_area"],
                    data["progress_percent"],
                ),
            )
            goal_id = int(cursor.lastrowid)
        row = conn.execute("SELECT * FROM life_goals WHERE id = ?", (goal_id,)).fetchone()
    return _row(row)


def archive_life_goal(goal_id: int) -> dict:
    return _update_life_goal_status(goal_id, "arquivado")


def complete_life_goal(goal_id: int) -> dict:
    with get_connection() as conn:
        conn.execute(
            "UPDATE life_goals SET status = 'concluido', progress_percent = 100, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (goal_id,),
        )
        row = conn.execute("SELECT * FROM life_goals WHERE id = ?", (goal_id,)).fetchone()
    return _row(row)


def life_goal_summary(reference_date: str | None = None) -> dict:
    goals = list_life_goals()
    active = [goal for goal in goals if goal["status"] == "ativo"]
    today = _parse_date(reference_date or today_iso())
    due_soon = []
    for goal in active:
        target = goal.get("target_date")
        if not target:
            continue
        target_date = _parse_date(target)
        days_left = (target_date - today).days
        if 0 <= days_left <= 14:
            item = dict(goal)
            item["days_left"] = days_left
            due_soon.append(item)
    main_goal = sorted(active, key=lambda item: (_priority_rank(item["priority"]), -float(item["progress_percent"] or 0)))[0] if active else None
    average_progress = _avg([goal["progress_percent"] for goal in active])
    return {
        "active_count": len(active),
        "total_count": len(goals),
        "main_goal": main_goal,
        "average_progress": average_progress,
        "due_soon": due_soon[:5],
        "goals": active[:6],
    }


def get_weekly_planner(week_start: str | None = None) -> dict:
    start, end = week_range(week_start)
    with get_connection() as conn:
        plan_row = conn.execute("SELECT * FROM weekly_plans WHERE week_start = ?", (start,)).fetchone()
        items = []
        if plan_row:
            rows = conn.execute(
                "SELECT * FROM weekly_plan_items WHERE plan_id = ? ORDER BY date ASC, id ASC",
                (plan_row["id"],),
            ).fetchall()
            items = [_row(row) for row in rows]
    plan = _row(plan_row) if plan_row else None
    return {
        "week_start": start,
        "week_end": end,
        "plan": plan,
        "items": items,
        "suggestion": generate_weekly_plan({"week_start": start}) if not plan else None,
    }


def generate_weekly_plan(payload: dict | None = None) -> dict:
    payload = payload or {}
    start, end = week_range(payload.get("week_start"))
    start_date = _parse_date(start)
    from .models import get_goals_by_category, history_summary
    from .projects import list_projects

    goals = get_goals_by_category()
    history = history_summary(start, end)
    projects = list_projects()
    life_goals = [goal for goal in list_life_goals() if goal["status"] == "ativo"]
    energy = float(history.get("average_energy") or 0)
    sleep = float(history.get("average_sleep") or 0)
    lighter = bool(energy and energy < 3) or bool(sleep and sleep < 7)
    items: list[dict] = []

    study_minutes = 60 if lighter else int(float(goals.get("study", {}).get("daily_hours_goal") or 1) * 60)
    programming_minutes = 50 if lighter else int(float(goals.get("programming", {}).get("daily_hours_goal") or 1.5) * 60)
    workout_minutes = 35 if lighter else 60
    main_project = projects[0] if projects else None
    main_goal = life_goals[0] if life_goals else None

    for index in range(7):
        current = start_date + timedelta(days=index)
        day = current.isoformat()
        weekday = WEEKDAYS[index]
        if index in {0, 2, 4}:
            items.append(_planner_item(day, weekday, "treino", "Treino sustentavel", workout_minutes, None, main_goal))
        if index < 5:
            items.append(_planner_item(day, weekday, "estudo", "Estudo principal", study_minutes, None, _goal_for_area(life_goals, "estudo")))
            items.append(_planner_item(day, weekday, "programacao", "Projeto principal", programming_minutes, main_project, _goal_for_area(life_goals, "programacao")))
        if index == 6:
            items.append(_planner_item(day, weekday, "revisao", "Revisao semanal guiada", 45, None, None))
            items.append(_planner_item(day, weekday, "sistema", "Planejar semana e criar backup", 30, None, None))
    return {
        "week_start": start,
        "week_end": end,
        "title": f"Plano semanal {start}",
        "generated_by": "rules-v3",
        "items": items,
        "context": {
            "average_energy": energy,
            "average_sleep": sleep,
            "active_life_goals": len(life_goals),
            "active_projects": len(projects),
            "mode": "leve" if lighter else "normal",
        },
    }


def save_weekly_plan(payload: dict) -> dict:
    start, end = week_range(payload.get("week_start"))
    title = sanitize_text(payload.get("title") or f"Plano semanal {start}", 160)
    generated_by = sanitize_text(payload.get("generated_by") or "manual", 40)
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise ValueError("Itens do plano precisam estar em lista.")
    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM weekly_plans WHERE week_start = ?", (start,)).fetchone()
        if existing:
            plan_id = int(existing["id"])
            conn.execute(
                "UPDATE weekly_plans SET week_end = ?, title = ?, generated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (end, title, generated_by, plan_id),
            )
            conn.execute("DELETE FROM weekly_plan_items WHERE plan_id = ?", (plan_id,))
        else:
            cursor = conn.execute(
                "INSERT INTO weekly_plans (week_start, week_end, title, generated_by) VALUES (?, ?, ?, ?)",
                (start, end, title, generated_by),
            )
            plan_id = int(cursor.lastrowid)
        for item in items:
            data = _weekly_item_payload(item, start)
            conn.execute(
                """
                INSERT INTO weekly_plan_items (
                    plan_id, date, weekday, category, title, estimated_minutes,
                    linked_project_id, linked_goal_id, completed, note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_id, data["date"], data["weekday"], data["category"], data["title"],
                    data["estimated_minutes"], data["linked_project_id"], data["linked_goal_id"],
                    data["completed"], data["note"],
                ),
            )
    return get_weekly_planner(start)


def complete_weekly_plan_item(payload: dict) -> dict:
    item_id = _int(payload.get("item_id") or payload.get("id"), 0)
    completed = bool_to_int(payload.get("completed", True))
    if not item_id:
        raise ValueError("item_id obrigatorio.")
    with get_connection() as conn:
        conn.execute(
            "UPDATE weekly_plan_items SET completed = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (completed, item_id),
        )
        row = conn.execute("SELECT * FROM weekly_plan_items WHERE id = ?", (item_id,)).fetchone()
    return _row(row)


def get_weekly_review(week_start: str | None = None) -> dict:
    start, end = week_range(week_start)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM weekly_reviews WHERE week_start = ?", (start,)).fetchone()
    return {"week_start": start, "week_end": end, "review": _row(row) if row else None, "context": weekly_review_context(start, end)}


def save_weekly_review(payload: dict) -> dict:
    start, end = week_range(payload.get("week_start"))
    data = {
        "what_worked": sanitize_text(payload.get("what_worked"), 3000),
        "what_failed": sanitize_text(payload.get("what_failed"), 3000),
        "best_day": sanitize_text(payload.get("best_day"), 80),
        "worst_day": sanitize_text(payload.get("worst_day"), 80),
        "main_obstacle": sanitize_text(payload.get("main_obstacle"), 1000),
        "main_win": sanitize_text(payload.get("main_win"), 1000),
        "next_week_adjustment": sanitize_text(payload.get("next_week_adjustment"), 1000),
        "emotional_state": sanitize_text(payload.get("emotional_state"), 80),
        "energy_reflection": sanitize_text(payload.get("energy_reflection"), 1000),
        "discipline_score": _clamp(payload.get("discipline_score"), 0, 10, 5),
    }
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO weekly_reviews (
                week_start, week_end, what_worked, what_failed, best_day, worst_day,
                main_obstacle, main_win, next_week_adjustment, emotional_state,
                energy_reflection, discipline_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_start, week_end) DO UPDATE SET
                what_worked = excluded.what_worked,
                what_failed = excluded.what_failed,
                best_day = excluded.best_day,
                worst_day = excluded.worst_day,
                main_obstacle = excluded.main_obstacle,
                main_win = excluded.main_win,
                next_week_adjustment = excluded.next_week_adjustment,
                emotional_state = excluded.emotional_state,
                energy_reflection = excluded.energy_reflection,
                discipline_score = excluded.discipline_score,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                start, end, data["what_worked"], data["what_failed"], data["best_day"], data["worst_day"],
                data["main_obstacle"], data["main_win"], data["next_week_adjustment"], data["emotional_state"],
                data["energy_reflection"], data["discipline_score"],
            ),
        )
    return get_weekly_review(start)


def weekly_review_context(week_start: str, week_end: str) -> dict:
    from .focus_timer import focus_summary
    from .models import history_summary, list_daily_records
    from .nutrition import nutrition_summary
    from .projects import project_summary

    records = sorted(list_daily_records(week_start, week_end), key=lambda item: item["date"])
    best = max(records, key=lambda item: float(item["daily_score"]), default=None)
    worst = min(records, key=lambda item: float(item["daily_score"]), default=None)
    return {
        "summary": history_summary(week_start, week_end),
        "best_day": best,
        "worst_day": worst,
        "nutrition": nutrition_summary(week_start, week_end),
        "focus": focus_summary(week_start, week_end),
        "projects": project_summary(week_start),
    }


def list_habits(include_archived: bool = False) -> list[dict]:
    query = "SELECT * FROM custom_habits"
    if not include_archived:
        query += " WHERE active = 1"
    query += " ORDER BY active DESC, category ASC, name ASC"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [_row(row) for row in rows]


def get_habit(habit_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM custom_habits WHERE id = ?", (habit_id,)).fetchone()
    return _row(row) if row else None


def save_habit(payload: dict, habit_id: int | None = None) -> dict:
    data = _habit_payload(payload)
    with get_connection() as conn:
        if habit_id:
            conn.execute(
                """
                UPDATE custom_habits
                SET name = ?, description = ?, category = ?, frequency = ?, target_per_week = ?,
                    weight = ?, active = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    data["name"], data["description"], data["category"], data["frequency"],
                    data["target_per_week"], data["weight"], data["active"], habit_id,
                ),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO custom_habits (name, description, category, frequency, target_per_week, weight, active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"], data["description"], data["category"], data["frequency"],
                    data["target_per_week"], data["weight"], data["active"],
                ),
            )
            habit_id = int(cursor.lastrowid)
        row = conn.execute("SELECT * FROM custom_habits WHERE id = ?", (habit_id,)).fetchone()
    return _row(row)


def archive_habit(habit_id: int) -> dict:
    with get_connection() as conn:
        conn.execute("UPDATE custom_habits SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (habit_id,))
        row = conn.execute("SELECT * FROM custom_habits WHERE id = ?", (habit_id,)).fetchone()
    return _row(row)


def log_habit(payload: dict) -> dict:
    habit_id = _int(payload.get("habit_id"), 0)
    if not habit_id:
        raise ValueError("habit_id obrigatorio.")
    date_value = validate_date(payload.get("date") or today_iso())
    completed = bool_to_int(payload.get("completed", True))
    value = sanitize_text(payload.get("value"), 80)
    note = sanitize_text(payload.get("note"), 1000)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO habit_logs (habit_id, date, completed, value, note)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(habit_id, date) DO UPDATE SET
                completed = excluded.completed,
                value = excluded.value,
                note = excluded.note,
                created_at = CURRENT_TIMESTAMP
            """,
            (habit_id, date_value, completed, value, note),
        )
        row = conn.execute(
            """
            SELECT l.*, h.name AS habit_name, h.category AS habit_category
            FROM habit_logs l
            JOIN custom_habits h ON h.id = l.habit_id
            WHERE l.habit_id = ? AND l.date = ?
            """,
            (habit_id, date_value),
        ).fetchone()
    return _row(row)


def get_todays_habits(date_value: str | None = None) -> dict:
    date_value = validate_date(date_value or today_iso())
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT h.*, l.completed, l.value, l.note, l.created_at AS logged_at
            FROM custom_habits h
            LEFT JOIN habit_logs l ON l.habit_id = h.id AND l.date = ?
            WHERE h.active = 1
            ORDER BY h.category ASC, h.name ASC
            """,
            (date_value,),
        ).fetchall()
    habits = [_row(row) for row in rows]
    completed = sum(1 for item in habits if int(item.get("completed") or 0))
    return {"date": date_value, "habits": habits, "completed": completed, "total": len(habits)}


def habit_summary(start: str | None = None, end: str | None = None) -> dict:
    start, end = start or week_range()[0], end or week_range()[1]
    with get_connection() as conn:
        habits = conn.execute("SELECT * FROM custom_habits WHERE active = 1 ORDER BY name").fetchall()
        rows = conn.execute(
            """
            SELECT h.id, h.name, h.target_per_week, COALESCE(SUM(CASE WHEN l.completed = 1 THEN 1 ELSE 0 END), 0) AS completed
            FROM custom_habits h
            LEFT JOIN habit_logs l ON l.habit_id = h.id AND l.date >= ? AND l.date <= ?
            WHERE h.active = 1
            GROUP BY h.id
            ORDER BY completed DESC, h.name ASC
            """,
            (start, end),
        ).fetchall()
    items = [_row(row) for row in rows]
    total_completed = sum(int(item["completed"] or 0) for item in items)
    best = items[0] if items and int(items[0]["completed"] or 0) else None
    neglected = sorted(items, key=lambda item: (int(item["completed"] or 0), item["name"]))[0] if items else None
    return {
        "active_count": len(habits),
        "completed_this_week": total_completed,
        "best_habit": best,
        "neglected_habit": neglected,
        "habits": items,
    }


def get_studies(start: str | None = None, end: str | None = None) -> dict:
    start, end = start or week_range()[0], end or week_range()[1]
    with get_connection() as conn:
        sessions = conn.execute(
            "SELECT * FROM study_sessions WHERE date >= ? AND date <= ? ORDER BY date DESC, id DESC",
            (start, end),
        ).fetchall()
        mocks = conn.execute(
            "SELECT * FROM mock_exams WHERE date >= ? AND date <= ? ORDER BY date DESC, id DESC",
            (start, end),
        ).fetchall()
        errors = conn.execute(
            "SELECT * FROM study_errors WHERE date >= ? AND date <= ? ORDER BY reviewed ASC, date DESC, id DESC",
            (start, end),
        ).fetchall()
    session_rows = [_row(row) for row in sessions]
    return {
        "week_start": start,
        "week_end": end,
        "sessions": session_rows,
        "mock_exams": [_row(row) for row in mocks],
        "errors": [_row(row) for row in errors],
        "summary": study_summary(start, end, session_rows),
    }


def save_study_session(payload: dict) -> dict:
    data = _study_session_payload(payload)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO study_sessions (
                date, subject, topic, duration_minutes, questions_done, correct_answers,
                wrong_answers, difficulty, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["date"], data["subject"], data["topic"], data["duration_minutes"],
                data["questions_done"], data["correct_answers"], data["wrong_answers"],
                data["difficulty"], data["note"],
            ),
        )
        row = conn.execute("SELECT * FROM study_sessions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row(row)


def save_mock_exam(payload: dict) -> dict:
    data = _mock_exam_payload(payload)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO mock_exams (
                date, exam_name, area, score, total_questions, correct_answers,
                wrong_answers, essay_score, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["date"], data["exam_name"], data["area"], data["score"],
                data["total_questions"], data["correct_answers"], data["wrong_answers"],
                data["essay_score"], data["note"],
            ),
        )
        row = conn.execute("SELECT * FROM mock_exams WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row(row)


def save_study_error(payload: dict) -> dict:
    data = _study_error_payload(payload)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO study_errors (
                date, subject, topic, error_type, description, correction, reviewed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["date"], data["subject"], data["topic"], data["error_type"],
                data["description"], data["correction"], data["reviewed"],
            ),
        )
        error_id = int(cursor.lastrowid)
        row = conn.execute("SELECT * FROM study_errors WHERE id = ?", (error_id,)).fetchone()
    from .study_reviews import schedule_review

    schedule_review(error_id, data["date"])
    return _row(row)


def list_study_errors(reviewed: int | None = None) -> list[dict]:
    query = "SELECT * FROM study_errors"
    params: list = []
    if reviewed is not None:
        query += " WHERE reviewed = ?"
        params.append(int(reviewed))
    query += " ORDER BY reviewed ASC, date DESC, id DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row(row) for row in rows]


def study_summary(start: str | None = None, end: str | None = None, sessions: list[dict] | None = None) -> dict:
    start, end = start or week_range()[0], end or week_range()[1]
    if sessions is None:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM study_sessions WHERE date >= ? AND date <= ?", (start, end)).fetchall()
            sessions = [_row(row) for row in rows]
    total_minutes = sum(int(item.get("duration_minutes") or 0) for item in sessions)
    questions = sum(int(item.get("questions_done") or 0) for item in sessions)
    correct = sum(int(item.get("correct_answers") or 0) for item in sessions)
    wrong = sum(int(item.get("wrong_answers") or 0) for item in sessions)
    by_subject: dict[str, float] = {}
    for item in sessions:
        subject = item.get("subject") or "Outro"
        by_subject[subject] = round(by_subject.get(subject, 0) + int(item.get("duration_minutes") or 0) / 60, 2)
    with get_connection() as conn:
        weak_rows = conn.execute(
            """
            SELECT subject, topic, COUNT(*) AS total
            FROM study_errors
            WHERE reviewed = 0
            GROUP BY subject, topic
            ORDER BY total DESC, subject ASC
            LIMIT 6
            """
        ).fetchall()
        pending = conn.execute("SELECT COUNT(*) AS total FROM study_errors WHERE reviewed = 0").fetchone()["total"]
    return {
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 2),
        "questions_done": questions,
        "correct_answers": correct,
        "wrong_answers": wrong,
        "accuracy": round((correct / questions) * 100, 1) if questions else 0,
        "by_subject": by_subject,
        "weak_topics": [_row(row) for row in weak_rows],
        "pending_reviews": int(pending or 0),
    }


def get_bad_day(date_value: str | None = None) -> dict:
    date_value = validate_date(date_value or today_iso())
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM bad_day_logs WHERE date = ?", (date_value,)).fetchone()
    log = _row(row) if row else None
    actions_done = []
    if log and log.get("minimum_actions_done"):
        try:
            actions_done = json.loads(log["minimum_actions_done"])
        except json.JSONDecodeError:
            actions_done = []
    return {
        "date": date_value,
        "message": "Hoje nao precisa ser perfeito. O objetivo e manter o minimo para nao quebrar a sequencia.",
        "actions": BAD_DAY_ACTIONS,
        "actions_done": actions_done,
        "log": log,
    }


def save_bad_day(payload: dict) -> dict:
    date_value = validate_date(payload.get("date") or today_iso())
    actions = payload.get("minimum_actions_done") or payload.get("actions_done") or []
    if not isinstance(actions, list):
        actions = []
    clean_actions = [sanitize_text(item, 120) for item in actions if sanitize_text(item, 120)]
    preset = sanitize_text(payload.get("preset"), 80)
    reason = sanitize_text(payload.get("reason"), 1000)
    note = sanitize_text(payload.get("note"), 2000)
    completed_at = datetime.now().isoformat(timespec="seconds") if payload.get("completed") else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO bad_day_logs (date, preset, reason, minimum_actions_done, note, completed_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(date) DO UPDATE SET
                preset = excluded.preset,
                reason = excluded.reason,
                minimum_actions_done = excluded.minimum_actions_done,
                note = excluded.note,
                completed_at = COALESCE(excluded.completed_at, bad_day_logs.completed_at),
                updated_at = CURRENT_TIMESTAMP
            """,
            (date_value, preset, reason, json.dumps(clean_actions, ensure_ascii=True), note, completed_at),
        )
    return get_bad_day(date_value)


def bad_day_summary(start: str | None = None, end: str | None = None) -> dict:
    start, end = start or week_range()[0], end or week_range()[1]
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM bad_day_logs WHERE date >= ? AND date <= ? ORDER BY date DESC", (start, end)).fetchall()
    logs = [_row(row) for row in rows]
    total_actions = 0
    for log in logs:
        try:
            total_actions += len(json.loads(log.get("minimum_actions_done") or "[]"))
        except json.JSONDecodeError:
            pass
    return {"count": len(logs), "minimum_actions": total_actions, "logs": logs}


def _life_goal_payload(payload: dict) -> dict:
    title = sanitize_text(payload.get("title"), 160)
    if not title:
        raise ValueError("Titulo do objetivo obrigatorio.")
    category = sanitize_text(payload.get("category") or "Outro", 40)
    if category not in LIFE_GOAL_CATEGORIES:
        category = "Outro"
    priority = _normalize(payload.get("priority") or "media")
    if priority not in LIFE_GOAL_PRIORITIES:
        priority = "media"
    status = _normalize(payload.get("status") or "ativo")
    if status not in LIFE_GOAL_STATUSES:
        status = "ativo"
    target_date = payload.get("target_date") or None
    if target_date:
        target_date = validate_date(target_date, "target_date")
    linked_area = _normalize(payload.get("linked_area") or "")
    if linked_area not in LINKED_AREAS:
        linked_area = ""
    return {
        "title": title,
        "description": sanitize_text(payload.get("description"), 3000),
        "category": category,
        "priority": priority,
        "status": status,
        "target_date": target_date,
        "linked_area": linked_area,
        "progress_percent": _clamp(payload.get("progress_percent"), 0, 100, 0),
    }


def _habit_payload(payload: dict) -> dict:
    name = sanitize_text(payload.get("name"), 120)
    if not name:
        raise ValueError("Nome do habito obrigatorio.")
    category = sanitize_text(payload.get("category") or "Outro", 40)
    if category not in HABIT_CATEGORIES:
        category = "Outro"
    frequency = _normalize(payload.get("frequency") or "diaria")
    if frequency not in HABIT_FREQUENCIES:
        frequency = "diaria"
    return {
        "name": name,
        "description": sanitize_text(payload.get("description"), 2000),
        "category": category,
        "frequency": frequency,
        "target_per_week": _clamp(payload.get("target_per_week"), 1, 7, 5),
        "weight": _clamp(payload.get("weight"), 1, 20, 5),
        "active": bool_to_int(payload.get("active", True)),
    }


def _study_session_payload(payload: dict) -> dict:
    subject = sanitize_text(payload.get("subject") or "Outro", 40)
    if subject not in STUDY_SUBJECTS:
        subject = "Outro"
    questions = _clamp(payload.get("questions_done"), 0, 1000, 0)
    correct = _clamp(payload.get("correct_answers"), 0, questions, 0) if questions else _clamp(payload.get("correct_answers"), 0, 1000, 0)
    wrong = _clamp(payload.get("wrong_answers"), 0, 1000, max(questions - correct, 0) if questions else 0)
    return {
        "date": validate_date(payload.get("date") or today_iso()),
        "subject": subject,
        "topic": sanitize_text(payload.get("topic"), 160),
        "duration_minutes": _clamp(payload.get("duration_minutes"), 1, 1440, 60),
        "questions_done": questions,
        "correct_answers": correct,
        "wrong_answers": wrong,
        "difficulty": _clamp(payload.get("difficulty"), 1, 5, 3),
        "note": sanitize_text(payload.get("note"), 2000),
    }


def _mock_exam_payload(payload: dict) -> dict:
    total = _clamp(payload.get("total_questions"), 0, 300, 0)
    correct = _clamp(payload.get("correct_answers"), 0, total or 300, 0)
    return {
        "date": validate_date(payload.get("date") or today_iso()),
        "exam_name": sanitize_text(payload.get("exam_name") or "Simulado", 120),
        "area": sanitize_text(payload.get("area") or "Geral", 80),
        "score": _clamp(payload.get("score"), 0, 1000, 0),
        "total_questions": total,
        "correct_answers": correct,
        "wrong_answers": _clamp(payload.get("wrong_answers"), 0, total or 300, max(total - correct, 0) if total else 0),
        "essay_score": _clamp(payload.get("essay_score"), 0, 1000, 0),
        "note": sanitize_text(payload.get("note"), 2000),
    }


def _study_error_payload(payload: dict) -> dict:
    subject = sanitize_text(payload.get("subject") or "Outro", 40)
    if subject not in STUDY_SUBJECTS:
        subject = "Outro"
    error_type = _normalize(payload.get("error_type") or "conteudo")
    if error_type not in ERROR_TYPES:
        error_type = "conteudo"
    return {
        "date": validate_date(payload.get("date") or today_iso()),
        "subject": subject,
        "topic": sanitize_text(payload.get("topic"), 160),
        "error_type": error_type,
        "description": sanitize_text(payload.get("description"), 3000),
        "correction": sanitize_text(payload.get("correction"), 3000),
        "reviewed": bool_to_int(payload.get("reviewed", False)),
    }


def _weekly_item_payload(payload: dict, default_week_start: str) -> dict:
    date_value = validate_date(payload.get("date") or default_week_start)
    weekday = sanitize_text(payload.get("weekday") or WEEKDAYS[_parse_date(date_value).weekday()], 40)
    return {
        "date": date_value,
        "weekday": weekday,
        "category": sanitize_text(payload.get("category") or "rotina", 80),
        "title": sanitize_text(payload.get("title") or "Item do plano", 180),
        "estimated_minutes": _clamp(payload.get("estimated_minutes"), 0, 1440, 30),
        "linked_project_id": _optional_int(payload.get("linked_project_id")),
        "linked_goal_id": _optional_int(payload.get("linked_goal_id")),
        "completed": bool_to_int(payload.get("completed", False)),
        "note": sanitize_text(payload.get("note"), 1000),
    }


def _planner_item(day: str, weekday: str, category: str, title: str, minutes: int, project: dict | None, goal: dict | None) -> dict:
    return {
        "date": day,
        "weekday": weekday,
        "category": category,
        "title": title,
        "estimated_minutes": minutes,
        "linked_project_id": project.get("id") if project else None,
        "linked_goal_id": goal.get("id") if goal else None,
        "completed": 0,
        "note": "",
    }


def _goal_for_area(goals: list[dict], area: str) -> dict | None:
    for goal in goals:
        if goal.get("linked_area") == area:
            return goal
    return None


def _update_life_goal_status(goal_id: int, status: str) -> dict:
    with get_connection() as conn:
        conn.execute("UPDATE life_goals SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, goal_id))
        row = conn.execute("SELECT * FROM life_goals WHERE id = ?", (goal_id,)).fetchone()
    return _row(row)


def _normalize(value) -> str:
    text = sanitize_text(value, 80).lower()
    replacements = {"é": "e", "á": "a", "ã": "a", "ç": "c", "í": "i", "ó": "o", "ú": "u", "â": "a", "ê": "e"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _row(row) -> dict:
    return dict(row) if row else {}


def _priority_rank(priority: str) -> int:
    return {"maxima": 0, "alta": 1, "media": 2, "baixa": 3}.get(priority, 4)


def _avg(values) -> float:
    clean = [float(value or 0) for value in values if value is not None]
    return round(sum(clean) / len(clean), 2) if clean else 0


def _int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _optional_int(value) -> int | None:
    if value in (None, "", "null"):
        return None
    parsed = _int(value, 0)
    return parsed or None


def _clamp(value, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))
