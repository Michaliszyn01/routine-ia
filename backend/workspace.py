from __future__ import annotations

from datetime import date

from core.tools.day_planner.planner_service import get_today_plan
from core.tools.focus_mode.focus_service import get_current_focus_session, get_focus_summary_today

from . import models
from .life_os import get_todays_habits, study_summary, week_range
from .load_balance import get_load_balance
from .study_reviews import list_due_reviews
from .tasks import task_overview


def get_workspace(reference_date: str | None = None) -> dict:
    day = reference_date or date.today().isoformat()
    start, end = week_range(day)
    daily = models.get_daily_record(day)
    planner = get_today_plan(day)
    tasks = task_overview(day)
    studies = study_summary(start, end)
    reviews = list_due_reviews(day)
    focus = get_focus_summary_today(day)
    return {
        "ok": True,
        "date": day,
        "daily": daily,
        "planner": planner,
        "tasks": tasks,
        "studies": {**studies, "due_reviews": len(reviews)},
        "reviews": reviews[:6],
        "habits": get_todays_habits(day),
        "focus": focus,
        "current_focus": get_current_focus_session(),
        "load_balance": get_load_balance(day),
    }
