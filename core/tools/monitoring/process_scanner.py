from __future__ import annotations

import ctypes
import os
from collections.abc import Iterable

from .app_rules import classify_app


SYSTEM_PROCESS_BLACKLIST = {
    "",
    "aggregatorhost.exe",
    "applicationframehost.exe",
    "audiodg.exe",
    "conhost.exe",
    "csrss.exe",
    "ctfmon.exe",
    "dllhost.exe",
    "dwm.exe",
    "fontdrvhost.exe",
    "explorer.exe",
    "idle",
    "lsaiso.exe",
    "lsass.exe",
    "memory compression",
    "nvidia container.exe",
    "nvcontainer.exe",
    "registry",
    "routineia.exe",
    "routine ia.exe",
    "runtimebroker.exe",
    "searchapp.exe",
    "searchhost.exe",
    "securityhealthsystray.exe",
    "services.exe",
    "shellexperiencehost.exe",
    "sihost.exe",
    "smss.exe",
    "spoolsv.exe",
    "startmenuexperiencehost.exe",
    "svchost.exe",
    "system",
    "system idle process",
    "systemsettings.exe",
    "taskhostw.exe",
    "textinputhost.exe",
    "widgets.exe",
    "wininit.exe",
    "winlogon.exe",
    "wmiprvse.exe",
}

IGNORED_PREFIXES = (
    "microsoft.",
    "nvidia ",
    "onedrive",
    "securityhealth",
    "startmenuexperiencehost",
    "textinputhost",
    "windowsinputexperience",
)

DWMWA_CLOAKED = 14


def scan_open_apps(
    window_iter: Iterable | None = None,
    process_name_lookup=None,
) -> list[dict]:
    windows = window_iter if window_iter is not None else _iter_visible_windows()
    lookup = process_name_lookup or _process_name_for_pid
    apps: dict[str, dict] = {}
    for window in windows:
        raw = _window_to_dict(window)
        title = str(raw.get("title") or raw.get("window_title") or "").strip()
        if not title:
            continue
        if raw.get("visible") is False or raw.get("cloaked") is True:
            continue
        process_name = str(raw.get("process_name") or raw.get("name") or "").strip()
        if not process_name:
            process_name = lookup(raw.get("pid")) or ""
        if should_ignore_process(process_name):
            continue
        classification = classify_app(
            process_name,
            window_title=title,
            url=str(raw.get("url") or ""),
        )
        app_name = classification["app_name"]
        key = app_name.lower()
        if key in apps:
            apps[key]["process_count"] += 1
            apps[key]["window_count"] += 1
            continue
        apps[key] = {
            "process_name": process_name,
            "app_name": app_name,
            "label": classification["label"],
            "process_count": 1,
            "window_count": 1,
            "context": title,
        }
    return sorted(apps.values(), key=lambda item: item["app_name"].lower())


def should_ignore_process(process_name: str | None) -> bool:
    normalized = (process_name or "").strip().lower()
    if normalized in get_system_process_blacklist():
        return True
    return any(normalized.startswith(prefix) for prefix in IGNORED_PREFIXES)


def get_system_process_blacklist() -> set[str]:
    extra = {
        item.strip().lower()
        for item in os.getenv("ROUTINE_IA_PROCESS_BLACKLIST", "").split(";")
        if item.strip()
    }
    return SYSTEM_PROCESS_BLACKLIST | extra


def _iter_visible_windows() -> list[dict]:
    if os.name != "nt":
        return []

    user32 = ctypes.windll.user32
    windows: list[dict] = []

    enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        title_length = user32.GetWindowTextLengthW(hwnd)
        if title_length <= 0:
            return True
        if _is_window_cloaked(hwnd):
            return True
        buffer = ctypes.create_unicode_buffer(title_length + 1)
        user32.GetWindowTextW(hwnd, buffer, title_length + 1)
        title = buffer.value.strip()
        if not title:
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        windows.append(
            {
                "hwnd": int(hwnd),
                "pid": int(pid.value),
                "title": title,
                "visible": True,
                "cloaked": False,
            }
        )
        return True

    user32.EnumWindows(enum_windows_proc(callback), 0)
    return windows


def _is_window_cloaked(hwnd) -> bool:
    try:
        cloaked = ctypes.c_int(0)
        result = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            ctypes.c_void_p(hwnd),
            DWMWA_CLOAKED,
            ctypes.byref(cloaked),
            ctypes.sizeof(cloaked),
        )
        return result == 0 and bool(cloaked.value)
    except Exception:
        return False


def _process_name_for_pid(pid) -> str:
    if not pid:
        return ""
    try:
        import psutil

        return psutil.Process(int(pid)).name()
    except Exception:
        return ""


def _window_to_dict(window) -> dict:
    if isinstance(window, dict):
        return window
    return {
        "hwnd": getattr(window, "hwnd", 0),
        "pid": getattr(window, "pid", 0),
        "title": getattr(window, "title", ""),
        "visible": getattr(window, "visible", True),
        "cloaked": getattr(window, "cloaked", False),
        "process_name": getattr(window, "process_name", ""),
    }
