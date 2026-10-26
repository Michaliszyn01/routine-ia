from __future__ import annotations

from dataclasses import dataclass


PLAN_MODES = {"light", "normal", "strong"}
ENERGY_LEVELS = {"baixa", "media", "alta"}
BLOCK_STATUSES = {"pending", "active", "done", "skipped", "rescheduled"}


@dataclass(frozen=True)
class PlannerContext:
    date: str
    energy_level: str
    focus_level: str
    mood_level: str
    sleep_seconds: int
    sleep_hours: float
    steps: int
    trained_today: bool
    routine_score: float
    productive_minutes: float
    risk_minutes: float
    suggested_mode: str
    mode_reason: str

