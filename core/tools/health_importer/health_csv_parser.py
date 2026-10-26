from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .health_schemas import (
    ActivityRecord,
    DailyHeartRateSummary,
    DailySleepSummary,
    DailyStepsSummary,
    SleepStageRecord,
    StepsRecord,
)


DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d.%m.%Y",
    "%Y.%m.%d",
    "%d-%m-%Y",
    "%Y/%m/%d",
)
DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d.%m.%Y %H:%M:%S",
    "%Y.%m.%d %H:%M:%S",
)


def parse_sleep_csv(file_path: str | Path) -> dict:
    records: list[SleepStageRecord] = []
    errors = []
    for line_number, row in _read_rows(file_path, errors):
        try:
            date_value = _parse_date(_pick(row, "data", "date"))
            duration = _parse_duration(_pick(row, "duracaoemsegundos", "duracao", "durationseconds", "duration"))
            if duration <= 0:
                continue
            records.append(
                SleepStageRecord(
                    date=date_value,
                    start_time=_parse_time(_pick(row, "hora", "time", "starttime")),
                    duration_seconds=duration,
                    stage=_normalize_sleep_stage(_pick(row, "fasedosono", "fase", "sleepstage", "stage")),
                    source_file=str(file_path),
                )
            )
        except ValueError as exc:
            errors.append({"line": line_number, "error": str(exc)})
    return {"records": records, "summaries": summarize_sleep(records), "errors": errors}


def parse_steps_csv(file_path: str | Path) -> dict:
    records: list[StepsRecord] = []
    errors = []
    for line_number, row in _read_rows(file_path, errors):
        try:
            date_value = _parse_date(_pick(row, "data", "date"))
            steps = _parse_int(_pick(row, "passos", "steps"))
            if steps <= 0:
                continue
            records.append(
                StepsRecord(
                    date=date_value,
                    time=_parse_time(_pick(row, "hora", "time")),
                    steps=steps,
                    source_file=str(file_path),
                )
            )
        except ValueError as exc:
            errors.append({"line": line_number, "error": str(exc)})
    return {"records": records, "summaries": summarize_steps(records), "errors": errors}


def parse_activities_csv(file_path: str | Path) -> dict:
    records: list[ActivityRecord] = []
    errors = []
    for line_number, row in _read_rows(file_path, errors):
        try:
            date_value = _parse_date(_pick(row, "data", "date"))
            elapsed = _parse_duration(_pick(row, "tempodecorrido", "elapsedtime", "elapsedseconds"))
            active = _parse_duration(_pick(row, "tempoativo", "activetime", "activeseconds"), default=elapsed)
            if elapsed <= 0 and active <= 0:
                continue
            records.append(
                ActivityRecord(
                    date=date_value,
                    start_time=_parse_time(_pick(row, "hora", "time", "starttime")),
                    activity_type=_clean_text(_pick(row, "tipodeatividade", "activitytype", "tipo")),
                    activity_name=_clean_text(_pick(row, "nomedaatividade", "activityname", "nome")),
                    elapsed_seconds=elapsed,
                    active_seconds=active,
                    distance_km=_parse_float(_pick(row, "distanciakm", "distancia", "distancekm", "distance"), default=0),
                    source_file=str(file_path),
                )
            )
        except ValueError as exc:
            errors.append({"line": line_number, "error": str(exc)})
    return {"records": records, "errors": errors}


def parse_heart_rate_csv(file_path: str | Path) -> dict:
    values_by_date: dict[str, list[int]] = defaultdict(list)
    errors = []
    for line_number, row in _read_rows(file_path, errors):
        try:
            date_value = _parse_date(_pick(row, "data", "date"))
            bpm = _parse_int(_pick(row, "frequenciacardiaca", "heart_rate", "heartrate", "bpm"))
            if bpm <= 0:
                continue
            values_by_date[date_value].append(bpm)
        except ValueError as exc:
            errors.append({"line": line_number, "error": str(exc)})

    summaries = []
    for date_value, values in values_by_date.items():
        summaries.append(
            DailyHeartRateSummary(
                date=date_value,
                avg_bpm=round(sum(values) / len(values)),
                min_bpm=min(values),
                max_bpm=max(values),
                samples_count=len(values),
            )
        )
    return {"summaries": summaries, "errors": errors}


def summarize_sleep(records: list[SleepStageRecord]) -> list[DailySleepSummary]:
    by_date: dict[str, dict[str, int]] = defaultdict(lambda: {"light": 0, "deep": 0, "rem": 0, "awake": 0})
    for record in records:
        by_date[record.date][record.stage] += record.duration_seconds
    return [
        DailySleepSummary(
            date=date_value,
            total_sleep_seconds=stages["light"] + stages["deep"] + stages["rem"],
            light_sleep_seconds=stages["light"],
            deep_sleep_seconds=stages["deep"],
            rem_sleep_seconds=stages["rem"],
            awake_seconds=stages["awake"],
        )
        for date_value, stages in sorted(by_date.items())
    ]


def summarize_steps(records: list[StepsRecord]) -> list[DailyStepsSummary]:
    totals: dict[str, int] = defaultdict(int)
    for record in records:
        totals[record.date] += record.steps
    return [DailyStepsSummary(date=date_value, total_steps=steps) for date_value, steps in sorted(totals.items())]


def _read_rows(file_path: str | Path, errors: list) -> list[tuple[int, dict]]:
    try:
        with open(file_path, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                errors.append({"line": 1, "error": "CSV vazio ou sem cabecalho."})
                return []
            rows = []
            for line_number, row in enumerate(reader, start=2):
                rows.append((line_number, {_normalize_key(key): value for key, value in row.items()}))
            return rows
    except UnicodeDecodeError:
        with open(file_path, newline="", encoding="latin-1") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                errors.append({"line": 1, "error": "CSV vazio ou sem cabecalho."})
                return []
            return [
                (line_number, {_normalize_key(key): value for key, value in row.items()})
                for line_number, row in enumerate(reader, start=2)
            ]
    except OSError as exc:
        errors.append({"line": 0, "error": f"Erro ao ler arquivo: {exc}"})
        return []


def _pick(row: dict, *keys: str) -> str:
    for key in keys:
        normalized = _normalize_key(key)
        value = row.get(normalized)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _parse_date(value: str) -> str:
    if not value:
        raise ValueError("Data ausente.")
    text = value.strip()
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Data invalida: {value}")


def _parse_time(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", value)
    if not match:
        return value.strip()[:20]
    hour, minute, second = match.group(1), match.group(2), match.group(3) or "00"
    return f"{int(hour):02d}:{minute}:{second}"


def _parse_duration(value: str, default: int = 0) -> int:
    if not value:
        return default
    text = value.strip().replace(",", ".")
    if ":" in text:
        parts = [int(float(part or 0)) for part in text.split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
    return max(0, int(round(float(_numeric_text(text)))))


def _parse_int(value: str, default: int = 0) -> int:
    if not value:
        return default
    return max(0, int(round(float(_numeric_text(value)))))


def _parse_float(value: str, default: float = 0) -> float:
    if not value:
        return default
    return max(0.0, float(_numeric_text(value)))


def _numeric_text(value: str) -> str:
    text = value.strip()
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif re.search(r"\d+\.\d{3}(?:\D|$)", text):
        text = text.replace(".", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        raise ValueError(f"Valor numerico invalido: {value}")
    return match.group(0)


def _normalize_sleep_stage(value: str) -> str:
    text = _normalize_key(value)
    if text in {"deep", "profundo", "sonoprofundo"}:
        return "deep"
    if text in {"rem", "sonorem"}:
        return "rem"
    if text in {"awake", "acordado", "desperto", "vigilia"}:
        return "awake"
    return "light"


def _normalize_key(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", ascii_value.casefold())


def _clean_text(value: str) -> str:
    return str(value or "").strip()[:120]
