import os
from pathlib import Path

from core.tools.monitoring.app_rules import classify_app
from core.tools.monitoring.monitoring_repository import add_usage_seconds, daily_summary
from core.tools.monitoring.monitoring_service import delete_monitoring_data, get_monitoring_status, run_monitoring_tick, start_monitoring, stop_monitoring
from core.tools.monitoring.process_scanner import scan_open_apps
from core.tools.monitoring.usage_tracker import UsageTracker
from core.tools.monitoring.window_scanner import normalize_focused_app
from backend.database import get_connection
from backend.startup import sync_startup_shortcut, startup_shortcut_status


def test_focused_app_adds_usage_time(client):
    tracker = UsageTracker(interval_seconds=60)
    increments = tracker.calculate_focus_increment(
        {"process_name": "Code.exe", "app_name": "VS Code", "label": "Projeto"}
    )

    assert increments == [
        {"app_name": "VS Code", "label": "Projeto", "seconds": 60},
    ]


def test_missing_focus_does_not_add_usage_time(client):
    tracker = UsageTracker(interval_seconds=60)

    assert tracker.calculate_focus_increment(None) == []


def test_ignored_focused_app_does_not_add_usage_time(client):
    assert normalize_focused_app({"process_name": "RuntimeBroker.exe", "title": "Runtime"}) is None


def test_ignored_app_does_not_enter_report(client):
    apps = scan_open_apps(
        [
            {"title": "Service", "process_name": "svchost.exe", "visible": True, "cloaked": False},
            {"title": "Routine IA", "process_name": "Code.exe", "visible": True, "cloaked": False},
            {"title": "System", "process_name": "System", "visible": True, "cloaked": False},
        ]
    )

    assert [app["app_name"] for app in apps] == ["VS Code"]


def test_windows_system_hosts_are_ignored_even_with_titles(client):
    apps = scan_open_apps(
        [
            {"title": "Aggregator", "process_name": "AggregatorHost.exe", "visible": True, "cloaked": False},
            {"title": "Application Frame", "process_name": "ApplicationFrameHost.exe", "visible": True, "cloaked": False},
            {"title": "Runtime", "process_name": "RuntimeBroker.exe", "visible": True, "cloaked": False},
            {"title": "Shell", "process_name": "ShellExperienceHost.exe", "visible": True, "cloaked": False},
            {"title": "Search", "process_name": "SearchApp.exe", "visible": True, "cloaked": False},
            {"title": "Widgets", "process_name": "Widgets.exe", "visible": True, "cloaked": False},
            {"title": "NVIDIA", "process_name": "NVIDIA Container.exe", "visible": True, "cloaked": False},
            {"title": "NVIDIA", "process_name": "nvcontainer.exe", "visible": True, "cloaked": False},
            {"title": "Chrome", "process_name": "chrome.exe", "visible": True, "cloaked": False},
        ]
    )

    assert [app["app_name"] for app in apps] == ["Chrome"]


def test_process_blacklist_accepts_local_override(client, monkeypatch):
    monkeypatch.setenv("ROUTINE_IA_PROCESS_BLACKLIST", "CustomHelper.exe")

    apps = scan_open_apps(
        [
            {"title": "Helper", "process_name": "CustomHelper.exe", "visible": True, "cloaked": False},
            {"title": "Chrome", "process_name": "chrome.exe", "visible": True, "cloaked": False},
        ]
    )

    assert [app["app_name"] for app in apps] == ["Chrome"]


def test_only_visible_top_level_windows_with_titles_are_counted(client):
    apps = scan_open_apps(
        [
            {"title": "", "process_name": "chrome.exe", "visible": True, "cloaked": False},
            {"title": "Hidden Chrome", "process_name": "chrome.exe", "visible": False, "cloaked": False},
            {"title": "Cloaked Chrome", "process_name": "chrome.exe", "visible": True, "cloaked": True},
            {"title": "Routine IA - VS Code", "process_name": "Code.exe", "visible": True, "cloaked": False},
        ]
    )

    assert [app["app_name"] for app in apps] == ["VS Code"]


def test_real_apps_are_kept_and_deduplicated_per_interval(client):
    apps = scan_open_apps(
        [
            {"title": "Chrome - Profile 1", "process_name": "chrome.exe", "visible": True, "cloaked": False},
            {"title": "Chrome - Profile 2", "process_name": "chrome.exe", "visible": True, "cloaked": False},
            {"title": "Routine IA - VS Code", "process_name": "Code.exe", "visible": True, "cloaked": False},
            {"title": "Spotify", "process_name": "Spotify.exe", "visible": True, "cloaked": False},
            {"title": "Steam", "process_name": "steam.exe", "visible": True, "cloaked": False},
            {"title": "Discord", "process_name": "Discord.exe", "visible": True, "cloaked": False},
        ]
    )

    assert [app["app_name"] for app in apps] == ["Chrome", "Discord", "Spotify", "Steam", "VS Code"]
    assert next(app for app in apps if app["app_name"] == "Chrome")["window_count"] == 2
    assert len([app for app in apps if app["app_name"] == "Chrome"]) == 1


def test_process_name_can_be_resolved_from_window_pid(client):
    apps = scan_open_apps(
        [{"title": "Spotify", "pid": 123, "visible": True, "cloaked": False}],
        process_name_lookup=lambda pid: "Spotify.exe" if pid == 123 else "",
    )

    assert apps[0]["app_name"] == "Spotify"


def test_monitoring_tick_counts_only_focused_app_not_all_open_apps(client):
    delete_monitoring_data("today")

    result = run_monitoring_tick(
        window_iter=[
            {"title": "Chrome", "process_name": "chrome.exe", "visible": True, "cloaked": False},
            {"title": "Routine IA - VS Code", "process_name": "Code.exe", "visible": True, "cloaked": False},
        ],
        focused_app={"process_name": "Code.exe", "app_name": "VS Code", "label": "Projeto", "title": "Routine IA - VS Code"},
        interval_seconds=60,
    )

    assert result["ok"] is True
    assert [app["app_name"] for app in result["open_apps"]] == ["Chrome", "VS Code"]
    assert result["focused_app"]["app_name"] == "VS Code"
    assert result["summary"]["total_seconds"] == 60
    assert [row["app_name"] for row in result["summary"]["by_app"]] == ["VS Code"]


def test_monitoring_does_not_start_duplicate_thread(client):
    stop_monitoring()
    try:
        first = start_monitoring(60)
        second = start_monitoring(30)

        assert first["thread_alive"] is True
        assert second["thread_alive"] is True
        assert get_monitoring_status()["interval_seconds"] == 30
    finally:
        stop_monitoring()


def test_startup_shortcut_can_be_created_and_removed(client, monkeypatch):
    startup_dir = Path(os.environ["ROUTINE_IA_DATA_DIR"]) / "startup-test"
    startup_dir.mkdir(parents=True, exist_ok=True)
    shortcut = startup_dir / "Routine IA.lnk"
    if shortcut.exists():
        shortcut.unlink()
    monkeypatch.setenv("ROUTINE_IA_STARTUP_DIR", str(startup_dir))
    monkeypatch.setenv("ROUTINE_IA_EXECUTABLE", str(startup_dir / "RoutineIA.exe"))

    def fake_create_shortcut(shortcut, executable, arguments=""):
        shortcut.write_text(f"{executable} {arguments}", encoding="utf-8")

    monkeypatch.setattr("backend.startup._create_windows_shortcut", fake_create_shortcut)

    created = sync_startup_shortcut(True, start_minimized=True)
    assert created["exists"] is True
    assert startup_shortcut_status()["exists"] is True

    removed = sync_startup_shortcut(False)
    assert removed["exists"] is False


def test_label_is_applied_from_rules(client):
    assert classify_app("Code.exe")["label"] == "Projeto"
    assert classify_app("Anki.exe")["label"] == "Estudo"
    assert classify_app("Discord.exe")["label"] == "Risco"


def test_chatgpt_desktop_is_productive_and_games_are_risk(client):
    assert classify_app("ChatGPT.exe") == {"app_name": "ChatGPT", "label": "Produtivo"}
    assert classify_app("MinecraftLauncher.exe")["label"] == "Risco"
    assert classify_app("RobloxPlayerBeta.exe")["label"] == "Risco"


def test_chatgpt_browser_projects_use_url_context(client):
    routine = classify_app(
        "chrome.exe",
        window_title="ChatGPT",
        url="https://chatgpt.com/g/g-p-6a48173c443c8191b1bb3edb3f1bf47d-rotina/c/abc",
    )
    work = classify_app(
        "chrome.exe",
        window_title="ChatGPT",
        url="https://chatgpt.com/g/g-p-6a0f0b77a22c819190f50b67efe79634-work/project",
    )

    assert routine == {"app_name": "ChatGPT - Rotina", "label": "Produtivo"}
    assert work == {"app_name": "ChatGPT - Work", "label": "Projeto"}


def test_chatgpt_browser_context_uses_window_title_and_unknown_sites_stay_neutral(client):
    assert classify_app("chrome.exe", window_title="Estudos - ChatGPT")["label"] == "Estudo"
    assert classify_app("chrome.exe", window_title="Ingles - ChatGPT") == {
        "app_name": "ChatGPT - Ingles",
        "label": "Estudo",
    }


def test_context_rule_overrides_stale_caller_label(client):
    focused = normalize_focused_app(
        {
            "process_name": "chrome.exe",
            "app_name": "Chrome",
            "label": "Neutro",
            "title": "ChatGPT - rotina - Google Chrome",
        }
    )

    assert focused["app_name"] == "ChatGPT - Rotina"
    assert focused["label"] == "Produtivo"
    assert classify_app("chrome.exe", window_title="Noticias - outro site") == {
        "app_name": "Chrome",
        "label": "Neutro",
    }


def test_daily_summary_returns_categories(client):
    add_usage_seconds("VS Code", "Projeto", 120, "2026-06-29")
    add_usage_seconds("Chrome", "Neutro", 60, "2026-06-29")
    add_usage_seconds("Discord", "Risco", 30, "2026-06-29")

    summary = daily_summary("2026-06-29")

    assert summary["total_seconds"] == 210
    assert summary["productive_seconds"] == 120
    assert summary["risk_seconds"] == 30
    assert [row["label"] for row in summary["by_category"]] == ["Projeto", "Neutro", "Risco"]


def test_database_upserts_daily_app_without_duplicate_records(client):
    with get_connection() as conn:
        conn.execute("DELETE FROM monitoring_app_usage_daily WHERE date = ?", ("2026-06-30",))

    add_usage_seconds("VS Code", "Projeto", 60, "2026-06-30")
    add_usage_seconds("VS Code", "Projeto", 60, "2026-06-30")

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT app_name, label, total_seconds
            FROM monitoring_app_usage_daily
            WHERE date = ? AND app_name = ?
            """,
            ("2026-06-30", "VS Code"),
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["label"] == "Projeto"
    assert rows[0]["total_seconds"] == 120


def test_weekly_summary_aggregates_same_app_across_days(client):
    add_usage_seconds("ChatGPT - Rotina", "Produtivo", 60, "2026-06-29")
    add_usage_seconds("ChatGPT - Rotina", "Produtivo", 120, "2026-06-30")

    summary = daily_summary("2026-06-29")
    daily_row = next(row for row in summary["by_app"] if row["app_name"] == "ChatGPT - Rotina")
    assert daily_row["seconds"] == 60

    from core.tools.monitoring.monitoring_repository import weekly_summary

    week = weekly_summary("2026-06-30")
    rows = [row for row in week["by_app"] if row["app_name"] == "ChatGPT - Rotina"]
    assert len(rows) == 1
    assert rows[0]["seconds"] == 180


def test_monitoring_level1_routes_shape(client):
    response = client.get("/api/monitoring-level1/summary")

    assert response.status_code == 200
    body = response.get_json()
    assert "by_app" in body
    assert "by_category" in body
    assert "result" in body
