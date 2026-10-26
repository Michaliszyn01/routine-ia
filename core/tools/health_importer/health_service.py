from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from backend import models

from .health_csv_parser import (
    parse_activities_csv,
    parse_heart_rate_csv,
    parse_sleep_csv,
    parse_steps_csv,
)
from .health_file_scanner import scan_health_sync_files
from .health_repository import (
    file_sha256,
    has_successful_import,
    health_dashboard,
    import_file_stats,
    latest_import_row,
    mirror_health_data_for_dates,
    record_imported_file,
    save_activity_records,
    save_heart_rate_summaries,
    save_sleep_records,
    save_steps_records,
)


_import_lock = threading.Lock()


def get_health_import_status(reference_date: str | None = None) -> dict:
    settings = models.get_settings()
    base_path = settings.get("health_sync_base_path") or r"G:\Meu Drive"
    scan = scan_health_sync_files(base_path)
    latest = latest_import_row()
    dashboard = health_dashboard(reference_date)
    return {
        "ok": True,
        "success": True,
        "settings": _public_settings(settings),
        "scan": {
            "base_path": scan["base_path"],
            "exists": scan["exists"],
            "folder_status": "found" if scan["exists"] else "missing",
            "candidate_count": len(scan["candidates"]),
            "ignored_count": len(scan["ignored"]),
            "missing_folders": scan["missing_folders"],
            "errors": scan["errors"],
        },
        "last_import": latest,
        "import_stats": import_file_stats(),
        "dashboard": dashboard,
        "today": dashboard["today"],
        "last_7_days": dashboard["daily"],
    }


def get_health_summary_today(reference_date: str | None = None) -> dict:
    dashboard = health_dashboard(reference_date)
    return {"ok": True, "success": True, "data": dashboard["today"]}


def get_health_summary_last_7_days(reference_date: str | None = None) -> dict:
    dashboard = health_dashboard(reference_date)
    return {"ok": True, "success": True, "data": dashboard["daily"]}


def update_health_import_settings(payload: dict) -> dict:
    current = models.get_settings()
    merged = dict(current)
    if "health_sync_base_path" in payload:
        base_path = str(payload.get("health_sync_base_path") or "").strip() or r"G:\Meu Drive"
        if not Path(base_path).expanduser().exists():
            raise ValueError(
                "Pasta nao encontrada. Verifique se o Google Drive esta aberto e sincronizado."
            )
        merged["health_sync_base_path"] = base_path
    if "health_auto_import_enabled" in payload:
        merged["health_auto_import_enabled"] = "true" if _bool(payload.get("health_auto_import_enabled")) else "false"
    if "health_import_interval_hours" in payload:
        merged["health_import_interval_hours"] = str(_interval_hours(payload.get("health_import_interval_hours")))
    settings = models.update_settings(merged)
    return _public_settings(settings)


def run_health_import(base_path: str | None = None) -> dict:
    if not _import_lock.acquire(blocking=False):
        return {"ok": False, "status": "busy", "message": "Importacao de saude ja esta em andamento."}
    try:
        settings = models.get_settings()
        target_base = base_path or settings.get("health_sync_base_path") or r"G:\Meu Drive"
        scan = scan_health_sync_files(target_base)
        if not scan["exists"]:
            return _result("error", scan["errors"][0] if scan["errors"] else "Pasta base nao encontrada.", scan)

        imported = 0
        skipped = 0
        errors = []
        affected_dates: set[str] = set()
        for candidate in scan["candidates"]:
            file_hash = ""
            try:
                file_hash = file_sha256(candidate.path)
                if has_successful_import(file_hash, candidate.data_type):
                    skipped += 1
                    continue
                rows, dates, parser_errors = _import_candidate(candidate)
                imported += rows
                affected_dates.update(dates)
                status = "success" if not parser_errors else "partial"
                record_imported_file(
                    file_path=candidate.path,
                    file_hash=file_hash,
                    data_type=candidate.data_type,
                    rows_imported=rows,
                    status=status,
                    error_message=_format_parser_errors(parser_errors),
                )
                if parser_errors:
                    errors.append({"file": candidate.file_name, "errors": parser_errors[:5]})
            except Exception as exc:
                errors.append({"file": candidate.file_name, "error": str(exc)})
                if file_hash:
                    record_imported_file(
                        file_path=candidate.path,
                        file_hash=file_hash,
                        data_type=candidate.data_type,
                        rows_imported=0,
                        status="error",
                        error_message=str(exc),
                    )

        mirror_health_data_for_dates(affected_dates)
        message = _build_message(imported, skipped, errors, scan)
        return {
            "ok": not (errors and not imported),
            "status": "partial" if errors and imported else "error" if errors else "success",
            "message": message,
            "imported_rows": imported,
            "skipped_files": skipped,
            "errors": errors,
            "scan": {
                "candidate_count": len(scan["candidates"]),
                "ignored_count": len(scan["ignored"]),
                "missing_folders": scan["missing_folders"],
            },
            "ran_at": datetime.now().isoformat(timespec="seconds"),
        }
    finally:
        _import_lock.release()


def _import_candidate(candidate) -> tuple[int, set[str], list]:
    if candidate.data_type == "sleep":
        parsed = parse_sleep_csv(candidate.path)
        inserted, dates = save_sleep_records(parsed["records"])
        return inserted, dates, parsed["errors"]
    if candidate.data_type == "steps":
        parsed = parse_steps_csv(candidate.path)
        inserted, dates = save_steps_records(parsed["records"])
        return inserted, dates, parsed["errors"]
    if candidate.data_type == "activities":
        parsed = parse_activities_csv(candidate.path)
        inserted, dates = save_activity_records(parsed["records"])
        return inserted, dates, parsed["errors"]
    if candidate.data_type == "heart_rate":
        parsed = parse_heart_rate_csv(candidate.path)
        inserted, dates = save_heart_rate_summaries(parsed["summaries"])
        return inserted, dates, parsed["errors"]
    return 0, set(), [{"line": 0, "error": "Tipo de dado nao suportado."}]


def _result(status: str, message: str, scan: dict) -> dict:
    return {
        "ok": status == "success",
        "status": status,
        "message": message,
        "imported_rows": 0,
        "skipped_files": 0,
        "errors": scan.get("errors", []),
        "scan": {
            "candidate_count": len(scan.get("candidates", [])),
            "ignored_count": len(scan.get("ignored", [])),
            "missing_folders": scan.get("missing_folders", []),
        },
        "ran_at": datetime.now().isoformat(timespec="seconds"),
    }


def _build_message(imported: int, skipped: int, errors: list, scan: dict) -> str:
    if not scan["candidates"]:
        return "Nenhum arquivo CSV novo encontrado nas pastas do Health Sync."
    if errors and not imported:
        return "Nao foi possivel importar os arquivos de saude. Veja os erros do importador."
    if errors:
        return f"{imported} registros importados, com alguns arquivos em erro."
    if skipped and not imported:
        return "Todos os arquivos encontrados ja tinham sido importados."
    return f"{imported} registros importados. {skipped} arquivos duplicados ignorados."


def _format_parser_errors(errors: list) -> str:
    if not errors:
        return ""
    return "; ".join(str(item.get("error", item)) for item in errors[:5])


def _public_settings(settings: dict) -> dict:
    return {
        "health_sync_base_path": settings.get("health_sync_base_path") or r"G:\Meu Drive",
        "health_auto_import_enabled": settings.get("health_auto_import_enabled", "true"),
        "health_import_interval_hours": settings.get("health_import_interval_hours", "4"),
    }


def _bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "sim"}
    return bool(value)


def _interval_hours(value) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        parsed = 4
    return min(24, max(1, parsed))
