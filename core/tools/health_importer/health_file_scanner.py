from __future__ import annotations

import unicodedata
from pathlib import Path

from .health_schemas import HealthFileCandidate


SUPPORTED_FOLDERS = {
    "health sync dormir": "sleep",
    "health sync passos": "steps",
    "health sync atividades": "activities",
    "health sync frequencia cardiaca": "heart_rate",
}
IGNORED_SUFFIXES = {".fit", ".tcx"}


def scan_health_sync_files(base_path: str | Path) -> dict:
    base = Path(base_path).expanduser()
    result = {
        "base_path": str(base),
        "exists": base.exists(),
        "candidates": [],
        "ignored": [],
        "missing_folders": [],
        "errors": [],
    }
    if not base.exists():
        result["errors"].append(
            f"Nao encontrei a pasta {base}. Verifique se o Google Drive esta aberto e sincronizado."
        )
        return result

    folder_map = {_normalize(child.name): child for child in base.iterdir() if child.is_dir()}
    for folder_key, data_type in SUPPORTED_FOLDERS.items():
        folder = folder_map.get(folder_key)
        if not folder:
            result["missing_folders"].append(folder_key)
            continue
        _collect_folder_files(folder, data_type, result)

    return result


def _collect_folder_files(folder: Path, data_type: str, result: dict) -> None:
    try:
        files = [path for path in folder.rglob("*") if path.is_file()]
    except OSError as exc:
        result["errors"].append(f"Erro ao ler {folder}: {exc}")
        return

    for path in files:
        suffix = path.suffix.lower()
        if suffix in IGNORED_SUFFIXES:
            result["ignored"].append({"path": str(path), "reason": f"{suffix} ignorado nesta versao"})
            continue
        if suffix != ".csv":
            result["ignored"].append({"path": str(path), "reason": "arquivo nao suportado"})
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        result["candidates"].append(
            HealthFileCandidate(
                path=str(path),
                file_name=path.name,
                data_type=data_type,
                folder_name=folder.name,
                size_bytes=size,
            )
        )


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(ascii_value.casefold().split())
