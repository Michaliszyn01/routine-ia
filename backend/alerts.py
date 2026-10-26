from __future__ import annotations

from datetime import date, datetime, timedelta

from .database import get_connection


def get_alerts(reference_date: str | None = None) -> dict:
    reference = date.fromisoformat(reference_date or date.today().isoformat())
    candidates = _build_candidates(reference)
    with get_connection() as conn:
        for candidate in candidates:
            _upsert_alert(conn, candidate)
        rows = conn.execute(
            """
            SELECT * FROM smart_alerts
            WHERE dismissed = 0
            ORDER BY CASE severity WHEN 'danger' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END, created_at DESC, id DESC
            LIMIT 12
            """
        ).fetchall()
    return {"alerts": [dict(row) for row in rows], "count": len(rows)}


def dismiss_alert(alert_id: int) -> dict:
    with get_connection() as conn:
        conn.execute("UPDATE smart_alerts SET dismissed = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (alert_id,))
        row = conn.execute("SELECT * FROM smart_alerts WHERE id = ?", (alert_id,)).fetchone()
    return dict(row) if row else {}


def _build_candidates(reference: date) -> list[dict]:
    from .backup import list_backups
    from .life_os import life_goal_summary
    from .models import get_goals_by_category, list_daily_records, week_range
    from .nutrition import nutrition_summary
    from .projects import project_summary

    today = reference.isoformat()
    start, end = week_range(today)
    week_records = list_daily_records(start, end)
    last_three = [(reference - timedelta(days=index)).isoformat() for index in range(3)]
    recent_records = {row["date"]: row for row in list_daily_records(last_three[-1], today)}
    candidates: list[dict] = []

    if all(day not in recent_records for day in last_three):
        candidates.append(_candidate("routine_gap", "3 dias sem registrar rotina", "Voce esta ha 3 dias sem registro. Use a tela Hoje para retomar com o minimo.", "warning", today))
    if sum(float(recent_records.get(day, {}).get("study_hours") or 0) for day in last_three) <= 0:
        candidates.append(_candidate("study_gap", "3 dias sem estudo", "O estudo ficou parado nos ultimos 3 dias. Um bloco curto ja reabre a sequencia.", "warning", today))
    if sum(float(recent_records.get(day, {}).get("programming_hours") or 0) for day in last_three) <= 0:
        candidates.append(_candidate("programming_gap", "3 dias sem programacao", "A programacao ficou sem registro nos ultimos 3 dias.", "warning", today))

    sleep_values = [float(row["sleep_hours"] or 0) for row in week_records if float(row["sleep_hours"] or 0) > 0]
    avg_sleep = sum(sleep_values) / len(sleep_values) if sleep_values else 0
    if avg_sleep and avg_sleep < 7:
        candidates.append(_candidate("low_sleep", "Sono medio abaixo de 7h", f"Sono medio da semana: {avg_sleep:.1f}h.", "danger", start))
    energy_values = [float(row["energy"] or 0) for row in week_records]
    avg_energy = sum(energy_values) / len(energy_values) if energy_values else 0
    if avg_energy and avg_energy < 3:
        candidates.append(_candidate("low_energy", "Energia media baixa", f"Energia media da semana: {avg_energy:.1f}/5.", "warning", start))

    nutrition = nutrition_summary(start, end)
    if nutrition.get("record_count") and nutrition.get("average_score", 0) < 55:
        candidates.append(_candidate("low_nutrition", "Alimentacao media baixa", "A alimentacao da semana esta abaixo do ideal para energia.", "warning", start))
    if nutrition.get("record_count") and nutrition.get("average_water", 0) < 2:
        candidates.append(_candidate("low_hydration", "Hidratacao baixa", "Agua media abaixo de 2L nos registros da semana.", "info", start))

    goals = get_goals_by_category()
    study_goal = float(goals.get("study", {}).get("weekly_hours_goal") or 0)
    programming_goal = float(goals.get("programming", {}).get("weekly_hours_goal") or 0)
    study_total = sum(float(row["study_hours"] or 0) for row in week_records)
    programming_total = sum(float(row["programming_hours"] or 0) for row in week_records)
    if study_goal and study_total < study_goal * 0.45:
        candidates.append(_candidate("study_goal_gap", "Meta de estudo muito abaixo", f"Estudo esta em {study_total:.1f}h de {study_goal:.1f}h.", "warning", start))
    if programming_goal and programming_total < programming_goal * 0.45:
        candidates.append(_candidate("programming_goal_gap", "Meta de programacao muito abaixo", f"Programacao esta em {programming_total:.1f}h de {programming_goal:.1f}h.", "warning", start))

    with get_connection() as conn:
        focus = conn.execute("SELECT COUNT(*) AS total FROM focus_sessions WHERE completed = 1 AND date >= ? AND date <= ?", (start, end)).fetchone()["total"]
    if int(focus or 0) == 0:
        candidates.append(_candidate("no_focus", "Muitos dias sem foco", "Nenhuma sessao de foco concluida apareceu nesta semana.", "info", start))

    projects = project_summary(today)
    if projects.get("active_projects") and float(projects.get("total_hours") or 0) <= 0:
        candidates.append(_candidate("project_no_time", "Projeto ativo sem tempo registrado", "Ha projetos ativos, mas nenhum tempo registrado nesta semana.", "info", start))

    backups = list_backups(limit=1)
    if not backups:
        candidates.append(_candidate("no_backup", "Nenhum backup recente", "Crie um backup manual para proteger seu banco local.", "warning", today))
    else:
        last = _parse_datetime(backups[0].get("created_at"))
        if last and datetime.now() - last > timedelta(days=7):
            candidates.append(_candidate("old_backup", "Nenhum backup recente", "O ultimo backup parece ter mais de 7 dias.", "warning", today))

    goal_summary = life_goal_summary(today)
    for goal in goal_summary.get("due_soon", []):
        if float(goal.get("progress_percent") or 0) < 70:
            candidates.append(_candidate("life_goal_due", "Objetivo proximo do prazo sem progresso", f"{goal['title']} esta perto do prazo e com {goal['progress_percent']:.0f}% de progresso.", "danger", goal.get("target_date") or today))
            break
    return candidates


def _candidate(alert_type: str, title: str, message: str, severity: str, related_date: str) -> dict:
    return {"alert_type": alert_type, "title": title, "message": message, "severity": severity, "related_date": related_date}


def _upsert_alert(conn, candidate: dict) -> None:
    row = conn.execute(
        "SELECT * FROM smart_alerts WHERE alert_type = ? AND related_date = ? ORDER BY id DESC LIMIT 1",
        (candidate["alert_type"], candidate["related_date"]),
    ).fetchone()
    if row:
        if int(row["dismissed"] or 0):
            return
        conn.execute(
            """
            UPDATE smart_alerts
            SET title = ?, message = ?, severity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (candidate["title"], candidate["message"], candidate["severity"], row["id"]),
        )
        return
    conn.execute(
        """
        INSERT INTO smart_alerts (alert_type, title, message, severity, related_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (candidate["alert_type"], candidate["title"], candidate["message"], candidate["severity"], candidate["related_date"]),
    )


def _parse_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace(" ", "T"))
    except ValueError:
        return None
