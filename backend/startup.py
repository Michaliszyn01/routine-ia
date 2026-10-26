from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SHORTCUT_NAME = "Routine IA.lnk"


def get_startup_dir() -> Path:
    override = os.getenv("ROUTINE_IA_STARTUP_DIR")
    if override:
        path = Path(override)
    else:
        appdata = os.getenv("APPDATA")
        if appdata:
            path = Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        else:
            path = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_startup_shortcut_path() -> Path:
    return get_startup_dir() / SHORTCUT_NAME


def get_executable_path() -> Path:
    override = os.getenv("ROUTINE_IA_EXECUTABLE")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    candidate = Path(__file__).resolve().parents[1] / "dist" / "RoutineIA.exe"
    return candidate if candidate.exists() else Path(sys.executable)


def sync_startup_shortcut(enabled: bool, *, start_minimized: bool = True) -> dict:
    shortcut = get_startup_shortcut_path()
    if not enabled:
        if shortcut.exists():
            shortcut.unlink()
        return {"enabled": False, "path": str(shortcut), "exists": shortcut.exists()}

    executable = get_executable_path()
    arguments = "--minimized" if start_minimized else ""
    _create_windows_shortcut(shortcut, executable, arguments)
    return {"enabled": True, "path": str(shortcut), "exists": shortcut.exists(), "target": str(executable)}


def startup_shortcut_status() -> dict:
    shortcut = get_startup_shortcut_path()
    return {"path": str(shortcut), "exists": shortcut.exists()}


def _create_windows_shortcut(shortcut: Path, executable: Path, arguments: str = "") -> None:
    if os.name != "nt":
        shortcut.write_text(f'"{executable}" {arguments}\n', encoding="utf-8")
        return
    command = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{_ps_escape(str(shortcut))}'); "
        f"$shortcut.TargetPath = '{_ps_escape(str(executable))}'; "
        f"$shortcut.Arguments = '{_ps_escape(arguments)}'; "
        f"$shortcut.WorkingDirectory = '{_ps_escape(str(executable.parent))}'; "
        "$shortcut.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
    )


def _ps_escape(value: str) -> str:
    return value.replace("'", "''")
