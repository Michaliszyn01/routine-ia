from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FocusStartPayload:
    date: str
    plan_block_id: int | None
    title: str
    focus_type: str
    planned_minutes: int
    next_step: str


def today_iso() -> str:
    return date.today().isoformat()
