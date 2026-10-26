from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthFileCandidate:
    path: str
    file_name: str
    data_type: str
    folder_name: str
    size_bytes: int


@dataclass(frozen=True)
class SleepStageRecord:
    date: str
    start_time: str
    duration_seconds: int
    stage: str
    source_file: str


@dataclass(frozen=True)
class DailySleepSummary:
    date: str
    total_sleep_seconds: int
    light_sleep_seconds: int
    deep_sleep_seconds: int
    rem_sleep_seconds: int
    awake_seconds: int
    source: str = "Health Sync"


@dataclass(frozen=True)
class StepsRecord:
    date: str
    time: str
    steps: int
    source_file: str


@dataclass(frozen=True)
class DailyStepsSummary:
    date: str
    total_steps: int


@dataclass(frozen=True)
class ActivityRecord:
    date: str
    start_time: str
    activity_type: str
    activity_name: str
    elapsed_seconds: int
    active_seconds: int
    distance_km: float
    source_file: str


@dataclass(frozen=True)
class DailyHeartRateSummary:
    date: str
    avg_bpm: int
    min_bpm: int
    max_bpm: int
    samples_count: int
