from __future__ import annotations

from datetime import date, datetime, timedelta

from backend import models
from core.tools.health_importer.health_repository import health_dashboard
from core.tools.monitoring.monitoring_repository import daily_summary
from core.tools.routine_analytics.analytics_service import get_routine_analytics

from .planner_repository import get_latest_checkin, get_plan, save_checkin, save_plan, update_block_status
from .planner_schemas import PlannerContext
from .planning_rules import block_profile, normalize_energy, status_message, suggest_mode
from .task_prioritizer import microsteps_for_block, pending_tasks_for_day


def get_today_plan(date_value: str | None = None) -> dict:
    target_date = _date(date_value)
    context = build_context(target_date)
    plan = get_plan(target_date)
    return {
        "ok": True,
        "date": target_date,
        "context": context.__dict__,
        "checkin": get_latest_checkin(target_date),
        "plan": plan,
        "next_step": _next_step(plan),
        "message": plan["plan"]["message"] if plan else "Gere um plano do dia para ter um proximo passo claro.",
    }


def save_energy_checkin(payload: dict) -> dict:
    checkin = save_checkin(payload)
    context = build_context(checkin["date"])
    return {"ok": True, "checkin": checkin, "context": context.__dict__}


def generate_day_plan(payload: dict | None = None) -> dict:
    payload = payload or {}
    target_date = _date(payload.get("date"))
    context = build_context(target_date, payload)
    blocks = _build_blocks(context, requested_mode=payload.get("mode"))
    plan = save_plan(
        target_date,
        {
            "mode": context.suggested_mode,
            "suggested_mode": context.suggested_mode,
            "energy_level": context.energy_level,
            "sleep_seconds": context.sleep_seconds,
            "routine_score": context.routine_score,
            "status": "ready",
            "message": status_message(context.suggested_mode),
        },
        blocks,
        preserve_done=False,
    )
    return {"ok": True, "date": target_date, "context": context.__dict__, "plan": plan, "next_step": _next_step(plan)}


def replan_day(payload: dict | None = None) -> dict:
    payload = payload or {}
    target_date = _date(payload.get("date"))
    context = build_context(target_date, {**payload, "mode": payload.get("mode") or "light"})
    blocks = _build_blocks(context, requested_mode=context.suggested_mode, replanned=True)
    plan = save_plan(
        target_date,
        {
            "mode": context.suggested_mode,
            "suggested_mode": context.suggested_mode,
            "energy_level": context.energy_level,
            "sleep_seconds": context.sleep_seconds,
            "routine_score": context.routine_score,
            "status": "adjusted",
            "message": status_message(context.suggested_mode, replanned=True),
        },
        blocks,
        preserve_done=True,
    )
    return {"ok": True, "date": target_date, "context": context.__dict__, "plan": plan, "next_step": _next_step(plan)}


def start_block(payload: dict) -> dict:
    return {"ok": True, "plan": update_block_status(int(payload.get("block_id") or payload.get("id") or 0), "active")}


def complete_block(payload: dict) -> dict:
    return {"ok": True, "plan": update_block_status(int(payload.get("block_id") or payload.get("id") or 0), "done")}


def skip_block(payload: dict) -> dict:
    return {"ok": True, "plan": update_block_status(int(payload.get("block_id") or payload.get("id") or 0), "skipped")}


def build_context(date_value: str, payload: dict | None = None) -> PlannerContext:
    payload = payload or {}
    checkin = get_latest_checkin(date_value) or {}
    energy = normalize_energy(payload.get("energy_level") or checkin.get("energy_level") or _energy_from_daily(date_value))
    health = health_dashboard(date_value)
    today = health.get("today") or {}
    daily = models.get_daily_record(date_value) or {}
    usage = daily_summary(date_value)
    analytics = get_routine_analytics(7, date_value)
    sleep_seconds = int(today.get("sleep_seconds") or round(float(daily.get("sleep_hours") or 0) * 3600))
    trained_today = bool((today.get("workout") or {}).get("has_data") or int(daily.get("workout_done") or 0))
    mode, reason = suggest_mode(
        energy_level=energy,
        sleep_seconds=sleep_seconds,
        day_late=_is_day_late(date_value),
        requested_mode=payload.get("mode"),
    )
    return PlannerContext(
        date=date_value,
        energy_level=energy,
        focus_level=str(payload.get("focus_level") or checkin.get("focus_level") or ""),
        mood_level=str(payload.get("mood_level") or checkin.get("mood_level") or ""),
        sleep_seconds=sleep_seconds,
        sleep_hours=round(sleep_seconds / 3600, 2) if sleep_seconds else 0,
        steps=int((today.get("steps_summary") or {}).get("total_steps") or daily.get("steps") or 0),
        trained_today=trained_today,
        routine_score=float(daily.get("daily_score") or 0),
        productive_minutes=float(usage.get("productive_minutes") or 0),
        risk_minutes=float(usage.get("risk_minutes") or 0),
        suggested_mode=mode,
        mode_reason=reason or (analytics.get("insights") or [{}])[0].get("message", ""),
    )


def _build_blocks(context: PlannerContext, *, requested_mode: str | None = None, replanned: bool = False) -> list[dict]:
    profile = block_profile(context.suggested_mode)
    tasks = pending_tasks_for_day(context.date)
    blocks: list[dict] = []
    current = datetime.strptime("14:00" if replanned else "09:00", "%H:%M")
    max_blocks = profile["max_blocks"]
    if context.trained_today:
        tasks = [task for task in tasks if task.get("type") != "workout"] + [task for task in tasks if task.get("type") == "workout"]
    for task in tasks:
        if len(blocks) >= max_blocks:
            break
        duration = _duration_for(task, profile, context)
        blocks.append(
            {
                "title": task["title"],
                "type": task.get("type") or "task",
                "start_time": current.strftime("%H:%M"),
                "duration_minutes": duration,
                "priority": task.get("priority") or 3,
                "status": "pending",
                "linked_task_id": task.get("linked_task_id") or "",
            }
        )
        current += timedelta(minutes=duration)
        if len(blocks) < max_blocks and task.get("type") != "break":
            blocks.append(
                {
                    "title": "Pausa",
                    "type": "break",
                    "start_time": current.strftime("%H:%M"),
                    "duration_minutes": profile["break"],
                    "priority": 9,
                    "status": "pending",
                    "linked_task_id": "",
                }
            )
            current += timedelta(minutes=profile["break"])
    if not blocks:
        blocks.append(
            {
                "title": "Registrar o minimo de hoje",
                "type": "minimum",
                "start_time": "09:00",
                "duration_minutes": profile["short"],
                "priority": 1,
                "status": "pending",
                "linked_task_id": "",
            }
        )
    return blocks[:max_blocks]


def _duration_for(task: dict, profile: dict, context: PlannerContext) -> int:
    if task.get("type") == "break":
        return profile["break"]
    if task.get("type") in {"admin", "minimum"}:
        return profile["short"]
    requested = int(task.get("duration_minutes") or profile["main"])
    if context.suggested_mode == "light":
        return min(max(10, requested), profile["main"])
    if context.suggested_mode == "strong":
        return min(max(profile["short"], requested), profile["main"])
    return min(max(profile["short"], requested), profile["main"])


def _next_step(plan: dict | None) -> dict | None:
    if not plan or not plan.get("next_block"):
        return None
    block = dict(plan["next_block"])
    block["microsteps"] = microsteps_for_block(block.get("type") or "", block.get("title") or "")
    return block


def _date(value) -> str:
    return str(value or date.today().isoformat())[:10]


def _energy_from_daily(date_value: str) -> str:
    daily = models.get_daily_record(date_value) or {}
    energy = int(float(daily.get("energy") or 3))
    if energy <= 2:
        return "baixa"
    if energy >= 4:
        return "alta"
    return "media"


def _is_day_late(date_value: str) -> bool:
    if date_value != date.today().isoformat():
        return False
    return datetime.now().hour >= 16

