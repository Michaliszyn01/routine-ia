from __future__ import annotations

import csv


SUPPORTED_SOURCES = ("Manual", "Samsung Health", "Health Sync", "Health Connect", "CSV")


def import_health_csv(file_path):
    from .models import upsert_health_data

    imported = 0
    errors = []
    with open(file_path, newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for index, row in enumerate(reader, start=2):
            payload = normalize_health_payload(
                {
                    "date": _pick(row, "date", "data", "Date"),
                    "sleep_hours_auto": _pick(row, "sleep_hours_auto", "sleep", "sono"),
                    "steps_auto": _pick(row, "steps_auto", "steps", "passos"),
                    "workout_minutes_auto": _pick(row, "workout_minutes_auto", "workout_minutes", "treino_minutos"),
                    "average_heart_rate": _pick(row, "average_heart_rate", "heart_rate", "fc_media"),
                    "resting_heart_rate": _pick(row, "resting_heart_rate", "resting_hr", "fc_repouso"),
                    "stress_average": _pick(row, "stress_average", "stress", "estresse"),
                    "weight_kg": _pick(row, "weight_kg", "weight", "peso"),
                    "source": _pick(row, "source", "fonte") or "CSV",
                    "observation": _pick(row, "observation", "observacao", "notes"),
                }
            )
            try:
                upsert_health_data(payload)
                imported += 1
            except Exception as exc:
                errors.append({"line": index, "error": str(exc)})

    return {
        "file_path": str(file_path),
        "status": "success" if not errors else "partial",
        "imported": imported,
        "errors": errors,
        "message": f"{imported} registros importados.",
    }


def preview_csv_import(file_path):
    return import_health_csv(file_path)


def normalize_health_payload(payload: dict) -> dict:
    source = payload.get("source") or "Manual"
    if source not in SUPPORTED_SOURCES:
        source = "CSV"
    return {**payload, "source": source}


def _pick(row: dict, *keys: str):
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return ""
