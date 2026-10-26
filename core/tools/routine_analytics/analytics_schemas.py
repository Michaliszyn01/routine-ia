from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyticsWindow:
    start_date: str
    end_date: str
    period_days: int


@dataclass(frozen=True)
class MetricCorrelation:
    key: str
    label: str
    value: float
    strength: str
    direction: str
    sample_size: int

