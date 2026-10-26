from __future__ import annotations

import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.request

import webview

from app import HOST, PORT as DEFAULT_PORT, create_app
from routine_worker import main as run_worker


WINDOW_TITLE = "Routine IA"
STARTUP_TIMEOUT_SECONDS = 10


def build_url(port: int) -> str:
    return f"http://{HOST}:{port}"


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        try:
            sock.bind((HOST, port))
        except OSError:
            return False
    return True


def is_routine_server_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"{build_url(port)}/api/dashboard", timeout=0.8) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def get_remote_settings(port: int) -> dict:
    try:
        with urllib.request.urlopen(f"{build_url(port)}/api/settings", timeout=1.2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("settings") or {}
    except Exception:
        return {}


def choose_port() -> tuple[int, bool]:
    if is_routine_server_running(DEFAULT_PORT):
        return DEFAULT_PORT, False

    if is_port_available(DEFAULT_PORT):
        return DEFAULT_PORT, True

    for port in range(DEFAULT_PORT + 1, DEFAULT_PORT + 20):
        if is_port_available(port):
            return port, True

    raise RuntimeError("Nenhuma porta local disponivel para iniciar o Routine IA.")


def run_flask(port: int) -> None:
    flask_app = create_app()
    flask_app.run(host=HOST, port=port, debug=False, use_reloader=False)


def wait_for_server(port: int) -> None:
    deadline = time.time() + STARTUP_TIMEOUT_SECONDS
    while time.time() < deadline:
        if is_routine_server_running(port):
            return
        time.sleep(0.2)
    raise RuntimeError("O servidor local do Routine IA nao iniciou a tempo.")


def start_desktop_app() -> None:
    port, should_start_server = choose_port()
    if should_start_server:
        flask_thread = threading.Thread(target=run_flask, args=(port,), daemon=True)
        flask_thread.start()
        wait_for_server(port)

    settings = get_remote_settings(port)
    start_minimized = "--minimized" in sys.argv or str(settings.get("start_minimized") or "false") == "true"
    run_in_background = str(settings.get("run_in_background") or "true") == "true"
    if start_minimized and should_start_server:
        keep_background_alive()
        return
    if start_minimized:
        return

    webview.create_window(
        title=WINDOW_TITLE,
        url=build_url(port),
        width=1280,
        height=800,
        min_size=(1000, 650),
        resizable=True,
    )
    webview.start()
    if should_start_server and run_in_background:
        keep_background_alive()


def keep_background_alive() -> None:
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    if "--worker" in sys.argv:
        run_worker()
    else:
        start_desktop_app()
