from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewWindow:
    start_date: str
    end_date: str
    label: str
