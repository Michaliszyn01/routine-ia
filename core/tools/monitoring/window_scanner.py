from __future__ import annotations

import ctypes
import os

from .app_rules import classify_app
from .process_scanner import should_ignore_process


def get_focused_app() -> dict | None:
    if os.name != "nt":
        return None
    try:
        user32 = ctypes.windll.user32
        hwnd = int(user32.GetForegroundWindow() or 0)
        if not hwnd or not user32.IsWindowVisible(hwnd):
            return None
        title = _window_title(hwnd)
        if not title:
            return None
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = _process_name_for_pid(int(pid.value))
        if should_ignore_process(process_name):
            return None
        classification = classify_app(process_name, window_title=title)
        return {
            "hwnd": hwnd,
            "pid": int(pid.value),
            "process_name": process_name,
            "app_name": classification["app_name"],
            "label": classification["label"],
            "window_title": title,
        }
    except Exception:
        return None


def normalize_focused_app(value: dict | None) -> dict | None:
    if not value:
        return None
    process_name = str(value.get("process_name") or "").strip()
    if should_ignore_process(process_name):
        return None
    title = str(value.get("window_title") or value.get("title") or "").strip()
    classification = classify_app(
        process_name,
        window_title=title,
        url=str(value.get("url") or ""),
    )
    return {
        "hwnd": int(value.get("hwnd") or 0),
        "pid": int(value.get("pid") or 0),
        "process_name": process_name,
        "app_name": classification["app_name"],
        "label": classification["label"],
        "window_title": title,
    }


def _window_title(hwnd: int) -> str:
    user32 = ctypes.windll.user32
    title_length = user32.GetWindowTextLengthW(hwnd)
    if title_length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(title_length + 1)
    user32.GetWindowTextW(hwnd, buffer, title_length + 1)
    return buffer.value.strip()


def _process_name_for_pid(pid: int) -> str:
    try:
        import psutil

        return psutil.Process(pid).name()
    except Exception:
        return ""
