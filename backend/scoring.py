from __future__ import annotations


ACTIVITY_FIELDS = {
    "workout": ("workout_done", "workout_hours"),
    "study": ("study_done", "study_hours"),
    "programming": ("programming_done", "programming_hours"),
    "reading": ("reading_done", "reading_hours"),
}


def calculate_daily_score(record: dict, goals: dict[str, dict]) -> float:
    score = 0.0

    for category, (done_field, hours_field) in ACTIVITY_FIELDS.items():
        goal = goals.get(category, {})
        if not int(goal.get("active", 1)):
            continue

        done = bool(record.get(done_field))
        hours = max(float(record.get(hours_field) or 0), 0)
        daily_goal = float(goal.get("daily_hours_goal") or 0)
        weight = float(goal.get("daily_weight") or 0)

        if done and daily_goal > 0:
            score += min(hours / daily_goal, 1) * weight

    sleep_goal = goals.get("sleep", {})
    if int(sleep_goal.get("active", 1)):
        sleep_hours = max(float(record.get("sleep_hours") or 0), 0)
        sleep_weight = float(sleep_goal.get("daily_weight") or 20)
        score += _sleep_score(sleep_hours, sleep_weight)

    return round(min(score, 100), 2)


def _sleep_score(sleep_hours: float, weight: float) -> float:
    if 8 <= sleep_hours <= 10:
        return weight
    if 7 <= sleep_hours < 8:
        return weight * 0.6
    if sleep_hours > 10:
        return weight * 0.75
    return 0
