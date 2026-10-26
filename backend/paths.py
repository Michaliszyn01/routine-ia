from __future__ import annotations

import os
import sys
from pathlib import Path


APP_NAME = "RoutineIA"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_base_path() -> Path:
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def resource_path(relative_path: str) -> str:
    """
    Retorna o caminho correto para arquivos do projeto,
    funcionando tanto em desenvolvimento quanto no executável PyInstaller.
    """
    return str(get_base_path() / relative_path)


def get_app_data_dir() -> Path:
    """
    Retorna uma pasta persistente para salvar banco de dados e arquivos do usuário.
    No Windows, usa LOCALAPPDATA.
    """
    override = os.getenv("ROUTINE_IA_DATA_DIR")
    if override:
        path = Path(override)
    else:
        app_data = os.getenv("LOCALAPPDATA")
        if app_data:
            path = Path(app_data) / APP_NAME
        else:
            path = Path.home() / ".routine_ia"

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path() -> Path:
    return get_app_data_dir() / "routine.db"


def get_exports_dir() -> Path:
    path = get_app_data_dir() / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_backups_dir() -> Path:
    path = get_app_data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
