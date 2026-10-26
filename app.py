from __future__ import annotations

import os
import threading
import webbrowser
import atexit
from datetime import datetime

from flask import Flask, current_app, jsonify, request, send_file

from backend.backup import (
    create_backup,
    get_auto_backup_settings,
    get_backup_dir,
    list_backups,
    maybe_create_auto_backup,
    update_auto_backup_settings,
)
from backend.calendar_utils import get_month_calendar, parse_month_param
from backend.database import init_db
from backend.export import (
    export_focus_csv,
    export_health_csv,
    export_history_csv,
    export_nutrition_csv,
    export_project_time_csv,
    export_projects_csv,
    export_table_csv,
)
from backend.focus_timer import complete_focus_session, list_focus_sessions, save_focus_session, start_focus_session
from backend.health_import import import_health_csv
from backend.insights import get_week_comparison
from backend.nutrition import (
    get_nutrition_record,
    list_nutrition_records,
    upsert_nutrition_record,
    weekly_nutrition_summary,
)
from backend.paths import get_app_data_dir, get_database_path, get_exports_dir, resource_path
from backend.pdf_report import generate_weekly_pdf
from backend.projects import (
    add_project_time,
    archive_project,
    get_project,
    list_project_time,
    list_projects,
    project_summary,
    save_project,
)
from backend.reports import generate_weekly_ai_report, generate_weekly_report
from backend.smart_goals import apply_suggestion, generate_smart_goal_suggestions
from backend.startup import startup_shortcut_status, sync_startup_shortcut
from backend.streaks import get_all_streaks
from backend.validators import ValidationError
from backend import models

from backend.adhd_support import (
    cant_start,
    complete_command_center,
    finish_bad_day,
    get_adhd_today,
    get_bad_day_presets,
    get_next_action_context,
    recommend_focus,
    save_minimum_day,
    start_bad_day,
)
from backend.alerts import dismiss_alert, get_alerts
from backend.ai_evaluator import evaluate_day, evaluate_week
from backend.checklists import list_checklists, log_checklist
from backend.evolution import get_evolution_summary
from backend.life_os import (
    archive_habit,
    archive_life_goal,
    complete_life_goal,
    complete_weekly_plan_item,
    generate_weekly_plan,
    get_bad_day,
    get_habit,
    get_life_goal,
    get_studies,
    get_weekly_planner,
    get_weekly_review,
    habit_summary,
    life_goal_summary,
    list_habits,
    list_life_goals,
    list_study_errors,
    log_habit,
    save_bad_day,
    save_habit,
    save_life_goal,
    save_mock_exam,
    save_study_error,
    save_study_session,
    save_weekly_plan,
    save_weekly_review,
    study_summary,
)
from backend.load_balance import get_load_balance
from backend.microtasks import generate_microtasks, list_microtasks, toggle_microtask
from backend.patterns import detect_patterns

from core.tools.monitoring.monitoring_service import (
    delete_monitoring_data,
    get_monitoring_status,
    get_today_summary,
    get_week_summary,
    pause_monitoring,
    resume_monitoring,
    run_monitoring_tick,
    start_monitoring,
    stop_monitoring,
)
from core.tools.background_worker.worker_controller import (
    ensure_background_worker,
    get_background_worker_overview,
)
from core.tools.health_importer.health_scheduler import (
    get_health_import_scheduler_status,
    start_health_import_scheduler,
    stop_health_import_scheduler,
)
from core.tools.health_importer.health_service import (
    get_health_import_status,
    get_health_summary_last_7_days,
    get_health_summary_today,
    run_health_import,
    update_health_import_settings,
)
from core.tools.routine_analytics.analytics_service import get_routine_analytics
from core.tools.day_planner.planner_service import (
    complete_block,
    generate_day_plan,
    get_today_plan,
    replan_day,
    save_energy_checkin,
    skip_block,
    start_block,
)
from core.tools.focus_mode.focus_service import (
    abandon_focus_session,
    complete_focus_session_v5,
    get_current_focus_session,
    get_focus_history,
    get_focus_session,
    get_focus_summary_today,
    pause_focus_session,
    resume_focus_session,
    start_focus_session_v5,
)
from core.tools.weekly_review.weekly_service import (
    current_week_review,
    previous_week_review,
    range_weekly_review,
)
from web.pages import register_page_routes
from web.workspace_api import workspace_api




HOST = "127.0.0.1"
PORT = 5000
APP_URL = f"http://{HOST}:{PORT}"
_app_instance: Flask | None = None
_shutdown_hook_registered = False


def create_app(*, enable_runtime: bool = True) -> Flask:
    app = Flask(
        __name__,
        template_folder=resource_path("frontend/templates"),
        static_folder=resource_path("frontend/static"),
    )
    init_db()
    register_page_routes(app)
    app.register_blueprint(workspace_api)
    if enable_runtime:
        _start_runtime_services()

    @app.errorhandler(ValidationError)
    def handle_validation_error(exc: ValidationError):
        return jsonify({"ok": False, "error": str(exc), "errors": exc.errors}), 400

    @app.errorhandler(ValueError)
    def handle_value_error(exc: ValueError):
        return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/dashboard")
    def api_dashboard():
        reference_date = request.args.get("date")
        return jsonify(models.weekly_dashboard(reference_date))

    @app.get("/api/daily")
    def api_daily_get():
        date_value = request.args.get("date") or models.today_iso()
        record = models.get_daily_record(date_value)
        return jsonify(
            {
                "exists": record is not None,
                "record": record,
                "date": date_value,
                "weekday": models.weekday_for(date_value),
            }
        )

    @app.post("/api/daily")
    def api_daily_save():
        record = models.upsert_daily_record(request.get_json(silent=True) or {})
        return jsonify({"ok": True, "record": record})

    @app.get("/api/today")
    def api_today_get():
        return jsonify(models.get_today_bundle(request.args.get("date")))

    @app.post("/api/today")
    def api_today_save():
        return jsonify(models.save_today_bundle(request.get_json(silent=True) or {}))

    @app.post("/api/ai/day-evaluation")
    def api_ai_day_evaluation():
        payload = request.get_json(silent=True) or {}
        return jsonify(evaluate_day(payload.get("date") or request.args.get("date")))

    @app.get("/api/day-planner/today")
    def api_day_planner_today():
        return jsonify(get_today_plan(request.args.get("date")))

    @app.post("/api/day-planner/generate")
    def api_day_planner_generate():
        return jsonify(generate_day_plan(request.get_json(silent=True) or {}))

    @app.post("/api/day-planner/replan")
    def api_day_planner_replan():
        return jsonify(replan_day(request.get_json(silent=True) or {}))

    @app.post("/api/day-planner/checkin")
    def api_day_planner_checkin():
        return jsonify(save_energy_checkin(request.get_json(silent=True) or {}))

    @app.post("/api/day-planner/block/start")
    def api_day_planner_block_start():
        return jsonify(start_block(request.get_json(silent=True) or {}))

    @app.post("/api/day-planner/block/complete")
    def api_day_planner_block_complete():
        return jsonify(complete_block(request.get_json(silent=True) or {}))

    @app.post("/api/day-planner/block/skip")
    def api_day_planner_block_skip():
        return jsonify(skip_block(request.get_json(silent=True) or {}))

    @app.get("/api/adhd/today")
    def api_adhd_today():
        return jsonify(get_adhd_today(request.args.get("date")))

    @app.get("/api/adhd/command-center")
    def api_adhd_command_center():
        return jsonify(get_next_action_context(request.args.get("date")))

    @app.post("/api/adhd/command-center/complete")
    def api_adhd_command_center_complete():
        return jsonify({"ok": True, **complete_command_center(request.get_json(silent=True) or {})})

    @app.post("/api/adhd/cant-start")
    def api_adhd_cant_start():
        return jsonify({"ok": True, **cant_start(request.get_json(silent=True) or {})})

    @app.post("/api/today/save-minimum")
    def api_today_save_minimum():
        return jsonify({"ok": True, **save_minimum_day(request.get_json(silent=True) or {})})

    @app.get("/api/microtasks")
    def api_microtasks():
        return jsonify(list_microtasks(request.args.get("date")))

    @app.post("/api/microtasks/generate")
    def api_microtasks_generate():
        return jsonify({"ok": True, **generate_microtasks(request.get_json(silent=True) or {})})

    @app.post("/api/microtasks/toggle")
    def api_microtasks_toggle():
        return jsonify({"ok": True, **toggle_microtask(request.get_json(silent=True) or {})})

    @app.get("/api/checklists")
    def api_checklists():
        return jsonify(list_checklists(request.args.get("date"), request.args.get("context")))

    @app.post("/api/checklists/log")
    def api_checklists_log():
        return jsonify({"ok": True, **log_checklist(request.get_json(silent=True) or {})})

    @app.get("/api/goals")
    def api_goals_get():
        goals = models.get_goals()
        active_weight_total = sum(float(goal["daily_weight"]) for goal in goals if goal["active"])
        return jsonify({"goals": goals, "active_weight_total": round(active_weight_total, 2)})

    @app.post("/api/goals")
    def api_goals_save_bulk():
        try:
            goals = models.update_goals_bulk(request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        active_weight_total = sum(float(goal["daily_weight"]) for goal in goals if goal["active"])
        return jsonify({"ok": True, "goals": goals, "active_weight_total": round(active_weight_total, 2)})

    @app.put("/api/goals/<category>")
    def api_goals_update(category):
        try:
            goal = models.update_goal(category, request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 404
        return jsonify({"ok": True, "goal": goal})

    @app.post("/api/goals/reset")
    def api_goals_reset():
        goals = models.reset_goals_to_default()
        active_weight_total = sum(float(goal["daily_weight"]) for goal in goals if goal["active"])
        return jsonify({"ok": True, "goals": goals, "active_weight_total": round(active_weight_total, 2)})

    @app.get("/api/smart-goals")
    def api_smart_goals():
        return jsonify({"suggestions": generate_smart_goal_suggestions()})

    @app.post("/api/smart-goals/apply")
    def api_smart_goals_apply():
        return jsonify({"ok": True, **apply_suggestion(request.get_json(silent=True) or {})})

    @app.get("/api/history")
    def api_history():
        records = models.list_daily_records(request.args.get("start"), request.args.get("end"))
        nutrition_rows = list_nutrition_records(request.args.get("start"), request.args.get("end"))
        nutrition_by_date = {row["date"]: row for row in nutrition_rows}
        for record in records:
            nutrition = nutrition_by_date.get(record["date"]) or {}
            record["nutrition_score"] = nutrition.get("nutrition_score", 0)
            record["water_liters"] = nutrition.get("water_liters", 0)
            record["protein_ok"] = nutrition.get("protein_ok", 0)
            record["fruits_vegetables_ok"] = nutrition.get("fruits_vegetables_ok", 0)
        summary = models.history_summary(request.args.get("start"), request.args.get("end"))
        return jsonify({"records": records, "summary": summary})

    @app.get("/api/history/export")
    def api_history_export():
        path, filename = export_history_csv(request.args.get("start"), request.args.get("end"))
        return send_file(path, as_attachment=True, download_name=filename, mimetype="text/csv")

    @app.get("/api/health")
    @app.get("/api/health-data")
    def api_health_get():
        records = models.list_health_data(request.args.get("start"), request.args.get("end"))
        return jsonify({"records": records})

    @app.post("/api/health")
    @app.post("/api/health-data")
    def api_health_save():
        record = models.upsert_health_data(request.get_json(silent=True) or {})
        return jsonify({"ok": True, "record": record})

    @app.get("/api/health/export")
    def api_health_export():
        path, filename = export_health_csv(request.args.get("start"), request.args.get("end"))
        return send_file(path, as_attachment=True, download_name=filename, mimetype="text/csv")

    @app.get("/api/health-import/status")
    @app.get("/api/health/status")
    def api_health_import_status():
        status = get_health_import_status(request.args.get("date"))
        auto_enabled = str(status.get("settings", {}).get("health_auto_import_enabled", "true")).lower() == "true"
        worker_attempt = None
        if auto_enabled and models.get_setting_bool("background_worker_enabled", True):
            worker_attempt = _ensure_worker_if_allowed()
        worker_overview = get_background_worker_overview()
        if worker_attempt:
            worker_overview["last_start_attempt"] = worker_attempt
        worker_status = worker_overview.get("worker") or {}
        worker_scheduler = worker_status.get("health_importer") or {}
        scheduler = worker_scheduler if worker_status.get("running") and worker_scheduler.get("running") else get_health_import_scheduler_status()
        status["scheduler"] = scheduler
        status["worker"] = worker_overview
        status["next_import_at"] = scheduler.get("next_run_at", "")
        if scheduler.get("last_error") and not status["scan"].get("errors"):
            status["scan"]["errors"] = [scheduler["last_error"]]
        status["operation"] = _health_operation_payload(status, worker_overview, scheduler)
        return jsonify(status)

    @app.get("/api/health/summary/today")
    def api_health_summary_today():
        return jsonify(get_health_summary_today(request.args.get("date")))

    @app.get("/api/health/summary/last-7-days")
    def api_health_summary_last_7_days():
        return jsonify(get_health_summary_last_7_days(request.args.get("date")))

    @app.post("/api/health-import/settings")
    @app.post("/api/health/settings")
    def api_health_import_settings():
        settings = update_health_import_settings(request.get_json(silent=True) or {})
        worker = _ensure_worker_if_allowed()
        if not worker.get("enabled"):
            if settings.get("health_auto_import_enabled") == "true":
                start_health_import_scheduler()
            else:
                stop_health_import_scheduler()
        return jsonify({"ok": True, "settings": settings, "worker": worker, "scheduler": get_health_import_scheduler_status()})

    @app.post("/api/health-import/run")
    @app.post("/api/health/import-now")
    def api_health_import_run():
        payload = request.get_json(silent=True) or {}
        result = run_health_import(payload.get("health_sync_base_path") or None)
        return jsonify(result), 200 if result.get("ok", True) or result.get("status") in {"success", "partial"} else 400

    @app.post("/api/health/open-folder")
    def api_health_open_folder():
        payload = request.get_json(silent=True) or {}
        settings = models.get_settings()
        base_path = payload.get("health_sync_base_path") or settings.get("health_sync_base_path") or r"G:\Meu Drive"
        base_path = os.path.expanduser(str(base_path).strip())
        if not os.path.isdir(base_path):
            return jsonify(
                {
                    "ok": False,
                    "success": False,
                    "error": "Pasta nao encontrada. Verifique se o Google Drive esta aberto e sincronizado.",
                    "path": base_path,
                }
            ), 404
        if hasattr(os, "startfile"):
            os.startfile(base_path)  # type: ignore[attr-defined]
            return jsonify({"ok": True, "success": True, "opened": True, "path": base_path})
        return jsonify({"ok": True, "success": True, "opened": False, "path": base_path})

    @app.get("/api/nutrition")
    def api_nutrition_get():
        date_value = request.args.get("date") or models.today_iso()
        return jsonify(
            {
                "date": date_value,
                "record": get_nutrition_record(date_value),
                "summary": weekly_nutrition_summary(date_value),
            }
        )

    @app.post("/api/nutrition")
    def api_nutrition_save():
        record = upsert_nutrition_record(request.get_json(silent=True) or {})
        return jsonify({"ok": True, "record": record})

    @app.get("/api/nutrition/history")
    def api_nutrition_history():
        start = request.args.get("start")
        end = request.args.get("end")
        return jsonify({"records": list_nutrition_records(start, end), "summary": weekly_nutrition_summary(start)})

    @app.get("/api/nutrition/export")
    def api_nutrition_export():
        path, filename = export_nutrition_csv(request.args.get("start"), request.args.get("end"))
        return send_file(path, as_attachment=True, download_name=filename, mimetype="text/csv")

    @app.get("/api/streaks")
    def api_streaks():
        return jsonify(get_all_streaks())

    @app.get("/api/week-comparison")
    def api_week_comparison():
        return jsonify(get_week_comparison(request.args.get("week_start")))

    @app.get("/api/calendar")
    def api_calendar():
        year, month = parse_month_param(request.args.get("month"))
        return jsonify(get_month_calendar(year, month))

    @app.post("/api/health/import")
    def api_health_import():
        upload = request.files.get("file")
        if not upload or not upload.filename:
            return jsonify({"ok": False, "error": "Envie um arquivo CSV."}), 400

        imports_dir = get_exports_dir() / "imports"
        imports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"health_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path = imports_dir / filename
        upload.save(path)
        result = import_health_csv(path)
        return jsonify({"ok": True, **result})

    @app.get("/api/focus/sessions")
    def api_focus_sessions():
        history = get_focus_history(int(request.args.get("days") or 30))
        return jsonify(
            {
                "sessions": history["sessions"],
                "projects": list_projects(),
            }
        )

    @app.get("/api/focus/current")
    def api_focus_current():
        return jsonify(get_current_focus_session())

    @app.get("/api/focus/recommend")
    def api_focus_recommend():
        return jsonify(recommend_focus(request.args.get("date"), request.args.get("task_type")))

    @app.post("/api/focus/start")
    def api_focus_start():
        return jsonify({"ok": True, "session": start_focus_session_v5(request.get_json(silent=True) or {})})

    @app.post("/api/focus/pause")
    def api_focus_pause():
        return jsonify({"ok": True, "session": pause_focus_session(request.get_json(silent=True) or {})})

    @app.post("/api/focus/resume")
    def api_focus_resume():
        return jsonify({"ok": True, "session": resume_focus_session(request.get_json(silent=True) or {})})

    @app.post("/api/focus/complete")
    def api_focus_complete():
        return jsonify({"ok": True, "session": complete_focus_session_v5(request.get_json(silent=True) or {})})

    @app.post("/api/focus/abandon")
    def api_focus_abandon():
        return jsonify({"ok": True, "session": abandon_focus_session(request.get_json(silent=True) or {})})

    @app.post("/api/focus/save")
    def api_focus_save():
        return jsonify({"ok": True, "session": save_focus_session(request.get_json(silent=True) or {})})

    @app.get("/api/focus/session/<int:session_id>")
    def api_focus_session(session_id):
        return jsonify(get_focus_session(session_id))

    @app.get("/api/focus/history")
    def api_focus_history():
        return jsonify(get_focus_history(int(request.args.get("days") or 7)))

    @app.get("/api/focus/summary/today")
    def api_focus_summary_today():
        return jsonify(get_focus_summary_today(request.args.get("date")))

    @app.get("/api/focus/export")
    def api_focus_export():
        path, filename = export_focus_csv(request.args.get("start"), request.args.get("end"))
        return send_file(path, as_attachment=True, download_name=filename, mimetype="text/csv")

    @app.get("/api/projects")
    def api_projects():
        include_archived = request.args.get("include_archived") in {"1", "true", "yes"}
        return jsonify({"projects": list_projects(include_archived=include_archived), "summary": project_summary()})

    @app.post("/api/projects")
    def api_projects_create():
        project = save_project(request.get_json(silent=True) or {})
        return jsonify({"ok": True, "project": project})

    @app.get("/api/projects/<int:project_id>")
    def api_project_get(project_id):
        project = get_project(project_id)
        if not project:
            return jsonify({"ok": False, "error": "Projeto nao encontrado."}), 404
        return jsonify({"project": project})

    @app.post("/api/projects/<int:project_id>")
    def api_project_update(project_id):
        project = save_project(request.get_json(silent=True) or {}, project_id=project_id)
        return jsonify({"ok": True, "project": project})

    @app.post("/api/projects/<int:project_id>/archive")
    def api_project_archive(project_id):
        return jsonify({"ok": True, "project": archive_project(project_id)})

    @app.get("/api/projects/<int:project_id>/time")
    def api_project_time(project_id):
        return jsonify({"entries": list_project_time(project_id, request.args.get("start"), request.args.get("end"))})

    @app.post("/api/projects/<int:project_id>/time")
    def api_project_time_add(project_id):
        return jsonify({"ok": True, "entry": add_project_time(project_id, request.get_json(silent=True) or {})})

    @app.get("/api/projects/export")
    def api_projects_export():
        path, filename = export_projects_csv()
        return send_file(path, as_attachment=True, download_name=filename, mimetype="text/csv")

    @app.get("/api/projects/time/export")
    def api_project_time_export():
        path, filename = export_project_time_csv(request.args.get("start"), request.args.get("end"))
        return send_file(path, as_attachment=True, download_name=filename, mimetype="text/csv")

    @app.get("/api/settings")
    def api_settings_get():
        return jsonify({"settings": models.get_settings()})

    @app.post("/api/settings")
    def api_settings_save():
        settings = models.update_settings(request.get_json(silent=True) or {})
        worker = _ensure_worker_if_allowed() if settings.get("background_worker_enabled") == "true" else None
        return jsonify({"ok": True, "settings": settings, "worker": worker})

    @app.post("/api/settings/reset")
    def api_settings_reset():
        settings = models.reset_settings_to_default()
        worker = _ensure_worker_if_allowed() if settings.get("background_worker_enabled") == "true" else None
        return jsonify({"ok": True, "settings": settings, "worker": worker})

    @app.get("/api/settings/startup-status")
    def api_settings_startup_status():
        return jsonify({"startup": startup_shortcut_status()})

    @app.post("/api/settings/startup-sync")
    def api_settings_startup_sync():
        settings = models.get_settings()
        result = sync_startup_shortcut(
            settings.get("start_with_windows") == "true",
            start_minimized=settings.get("start_minimized") == "true",
        )
        return jsonify({"ok": True, "startup": result})

    @app.post("/api/backup/create")
    def api_backup_create():
        try:
            backup = create_backup()
        except RuntimeError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500
        return jsonify({"ok": True, "backup": backup})

    @app.get("/api/backup/list")
    def api_backup_list():
        return jsonify({"backups": list_backups()})

    @app.get("/api/backup/settings")
    def api_backup_settings_get():
        return jsonify({"settings": get_auto_backup_settings()})

    @app.post("/api/backup/settings")
    def api_backup_settings_save():
        settings = update_auto_backup_settings(request.get_json(silent=True) or {})
        return jsonify({"ok": True, "settings": settings})


    @app.get("/api/life-goals")
    def api_life_goals():
        include_archived = request.args.get("include_archived") in {"1", "true", "yes"}
        return jsonify({"goals": list_life_goals(include_archived=include_archived), "summary": life_goal_summary(request.args.get("date"))})

    @app.post("/api/life-goals")
    def api_life_goals_create():
        return jsonify({"ok": True, "goal": save_life_goal(request.get_json(silent=True) or {})})

    @app.get("/api/life-goals/<int:goal_id>")
    def api_life_goal_get(goal_id):
        goal = get_life_goal(goal_id)
        if not goal:
            return jsonify({"ok": False, "error": "Objetivo nao encontrado."}), 404
        return jsonify({"goal": goal})

    @app.post("/api/life-goals/<int:goal_id>")
    def api_life_goal_update(goal_id):
        return jsonify({"ok": True, "goal": save_life_goal(request.get_json(silent=True) or {}, goal_id=goal_id)})

    @app.post("/api/life-goals/<int:goal_id>/archive")
    def api_life_goal_archive(goal_id):
        return jsonify({"ok": True, "goal": archive_life_goal(goal_id)})

    @app.post("/api/life-goals/<int:goal_id>/complete")
    def api_life_goal_complete(goal_id):
        return jsonify({"ok": True, "goal": complete_life_goal(goal_id)})

    @app.get("/api/weekly-planner")
    def api_weekly_planner():
        return jsonify(get_weekly_planner(request.args.get("week_start")))

    @app.post("/api/weekly-planner/generate")
    def api_weekly_planner_generate():
        return jsonify({"ok": True, "plan": generate_weekly_plan(request.get_json(silent=True) or {})})

    @app.post("/api/weekly-planner/save")
    def api_weekly_planner_save():
        return jsonify({"ok": True, **save_weekly_plan(request.get_json(silent=True) or {})})

    @app.post("/api/weekly-planner/complete-item")
    def api_weekly_planner_complete_item():
        return jsonify({"ok": True, "item": complete_weekly_plan_item(request.get_json(silent=True) or {})})

    @app.get("/api/weekly-review")
    def api_weekly_review():
        week_start = request.args.get("week_start")
        if week_start:
            return jsonify(range_weekly_review(week_start, None, label="Semana selecionada"))
        return jsonify(current_week_review())

    @app.get("/api/weekly-review/current")
    def api_weekly_review_current():
        return jsonify(current_week_review())

    @app.get("/api/weekly-review/previous")
    def api_weekly_review_previous():
        return jsonify(previous_week_review())

    @app.get("/api/weekly-review/range")
    def api_weekly_review_range():
        start = request.args.get("start")
        end = request.args.get("end")
        if not start or not end:
            raise ValueError("Informe start e end no formato YYYY-MM-DD.")
        return jsonify(range_weekly_review(start, end, label="Periodo personalizado"))

    @app.post("/api/weekly-review")
    def api_weekly_review_save():
        return jsonify({"ok": True, **save_weekly_review(request.get_json(silent=True) or {})})

    @app.post("/api/ai/week-evaluation")
    def api_ai_week_evaluation():
        payload = request.get_json(silent=True) or {}
        return jsonify(evaluate_week(payload.get("week_start") or payload.get("start"), payload.get("week_end") or payload.get("end")))

    @app.get("/api/patterns")
    def api_patterns():
        return jsonify(detect_patterns(request.args.get("start_date"), request.args.get("end_date")))

    @app.get("/api/alerts")
    def api_alerts():
        return jsonify(get_alerts(request.args.get("date")))

    @app.post("/api/alerts/<int:alert_id>/dismiss")
    def api_alert_dismiss(alert_id):
        return jsonify({"ok": True, "alert": dismiss_alert(alert_id)})

    @app.get("/api/habits")
    def api_habits():
        include_archived = request.args.get("include_archived") in {"1", "true", "yes"}
        start, end = models.week_range(request.args.get("date"))
        return jsonify({"habits": list_habits(include_archived=include_archived), "summary": habit_summary(start, end)})

    @app.post("/api/habits")
    def api_habits_create():
        return jsonify({"ok": True, "habit": save_habit(request.get_json(silent=True) or {})})

    @app.get("/api/habits/<int:habit_id>")
    def api_habit_get(habit_id):
        habit = get_habit(habit_id)
        if not habit:
            return jsonify({"ok": False, "error": "Habito nao encontrado."}), 404
        return jsonify({"habit": habit})

    @app.post("/api/habits/<int:habit_id>")
    def api_habit_update(habit_id):
        return jsonify({"ok": True, "habit": save_habit(request.get_json(silent=True) or {}, habit_id=habit_id)})

    @app.post("/api/habits/<int:habit_id>/archive")
    def api_habit_archive(habit_id):
        return jsonify({"ok": True, "habit": archive_habit(habit_id)})

    @app.post("/api/habits/log")
    def api_habit_log():
        return jsonify({"ok": True, "log": log_habit(request.get_json(silent=True) or {})})

    @app.get("/api/studies")
    def api_studies():
        return jsonify(get_studies(request.args.get("start"), request.args.get("end")))

    @app.post("/api/studies/session")
    def api_studies_session():
        return jsonify({"ok": True, "session": save_study_session(request.get_json(silent=True) or {})})

    @app.get("/api/studies/summary")
    def api_studies_summary():
        start, end = models.week_range(request.args.get("date"))
        return jsonify({"summary": study_summary(start, end), "week_start": start, "week_end": end})

    @app.post("/api/studies/mock-exam")
    def api_studies_mock_exam():
        return jsonify({"ok": True, "mock_exam": save_mock_exam(request.get_json(silent=True) or {})})

    @app.get("/api/studies/errors")
    def api_studies_errors():
        reviewed = request.args.get("reviewed")
        reviewed_value = None if reviewed in {None, ""} else int(reviewed)
        return jsonify({"errors": list_study_errors(reviewed_value)})

    @app.post("/api/studies/errors")
    def api_studies_error_create():
        return jsonify({"ok": True, "error_record": save_study_error(request.get_json(silent=True) or {})})

    @app.get("/api/load-balance")
    def api_load_balance():
        return jsonify(get_load_balance(request.args.get("date")))

    @app.get("/api/bad-day")
    def api_bad_day():
        return jsonify(get_bad_day(request.args.get("date")))

    @app.post("/api/bad-day/save")
    def api_bad_day_save():
        return jsonify({"ok": True, **save_bad_day(request.get_json(silent=True) or {})})

    @app.get("/api/bad-day/presets")
    def api_bad_day_presets():
        return jsonify(get_bad_day_presets())

    @app.post("/api/bad-day/start")
    def api_bad_day_start():
        return jsonify({"ok": True, **start_bad_day(request.get_json(silent=True) or {})})

    @app.post("/api/bad-day/finish")
    def api_bad_day_finish():
        return jsonify({"ok": True, **finish_bad_day(request.get_json(silent=True) or {})})

    @app.get("/api/evolution")
    def api_evolution():
        return jsonify(get_evolution_summary(request.args.get("period") or "month"))

    @app.get("/api/routine-analytics")
    def api_routine_analytics():
        try:
            period = int(request.args.get("period") or 7)
        except ValueError:
            period = 7
        return jsonify(get_routine_analytics(period, request.args.get("date")))

    @app.get("/api/export/<table_name>")
    def api_generic_export(table_name):
        path, filename = export_table_csv(table_name, request.args.get("start"), request.args.get("end"))
        return send_file(path, as_attachment=True, download_name=filename, mimetype="text/csv")

    @app.get("/api/monitoring-level1/status")
    def api_monitoring_level1_status():
        return jsonify(_monitoring_status_payload())

    @app.post("/api/monitoring-level1/start")
    def api_monitoring_level1_start():
        payload = request.get_json(silent=True) or {}
        interval = payload.get("interval_seconds") or models.get_setting_int("monitoring_interval_seconds", 60)
        models.set_settings_values(
            {
                "auto_start_monitoring": "true",
                "monitoring_worker_state": "active",
                "monitoring_interval_seconds": str(interval),
            }
        )
        worker = _ensure_worker_if_allowed()
        if not worker.get("enabled"):
            start_monitoring(interval)
        return jsonify({"ok": True, **_monitoring_status_payload(worker)})

    @app.post("/api/monitoring-level1/pause")
    def api_monitoring_level1_pause():
        models.set_settings_values({"monitoring_worker_state": "paused"})
        worker = _ensure_worker_if_allowed()
        if not worker.get("enabled"):
            pause_monitoring()
        return jsonify({"ok": True, **_monitoring_status_payload(worker)})

    @app.post("/api/monitoring-level1/resume")
    def api_monitoring_level1_resume():
        models.set_settings_values({"auto_start_monitoring": "true", "monitoring_worker_state": "active"})
        worker = _ensure_worker_if_allowed()
        if not worker.get("enabled"):
            resume_monitoring()
        return jsonify({"ok": True, **_monitoring_status_payload(worker)})

    @app.post("/api/monitoring-level1/stop")
    def api_monitoring_level1_stop():
        models.set_settings_values({"auto_start_monitoring": "false", "monitoring_worker_state": "off"})
        stop_monitoring()
        return jsonify({"ok": True, **_monitoring_status_payload()})

    @app.post("/api/monitoring-level1/tick")
    def api_monitoring_level1_tick():
        payload = request.get_json(silent=True) or {}
        return jsonify(run_monitoring_tick(interval_seconds=payload.get("interval_seconds")))

    @app.get("/api/monitoring-level1/summary")
    def api_monitoring_level1_summary():
        return jsonify(get_today_summary(request.args.get("date")))

    @app.get("/api/monitoring-level1/week")
    def api_monitoring_level1_week():
        return jsonify(get_week_summary(request.args.get("date")))

    @app.post("/api/monitoring-level1/delete-data")
    def api_monitoring_level1_delete_data():
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **delete_monitoring_data(payload.get("scope") or "today")})

    @app.get("/api/background-worker/status")
    def api_background_worker_status():
        return jsonify({"ok": True, **get_background_worker_overview()})

    @app.post("/api/background-worker/start")
    def api_background_worker_start():
        return jsonify({"ok": True, **_ensure_worker_if_allowed(force=True)})

    @app.get("/api/app/paths")
    def api_app_paths():
        return jsonify(
            {
                "app_data_dir": str(get_app_data_dir()),
                "database_path": str(get_database_path()),
                "exports_dir": str(get_exports_dir()),
                "backups_dir": str(get_backup_dir()),
            }
        )

    @app.post("/api/app/open-data-dir")
    def api_app_open_data_dir():
        path = get_app_data_dir()
        if hasattr(os, "startfile"):
            os.startfile(path)  # type: ignore[attr-defined]
            return jsonify({"ok": True, "path": str(path)})
        return jsonify({"ok": False, "error": "Abertura de pasta nao disponivel neste sistema."}), 400

    @app.post("/api/app/quit")
    def api_app_quit():
        def shutdown_process() -> None:
            _shutdown_runtime_services()
            os._exit(0)

        threading.Timer(0.4, shutdown_process).start()
        return jsonify({"ok": True})

    @app.get("/api/report")
    def api_report():
        week_start = request.args.get("week_start")
        week_end = request.args.get("week_end")
        if not week_start or not week_end:
            week_start, week_end = models.week_range()
        return jsonify(generate_weekly_ai_report(week_start, week_end))

    @app.get("/api/reports/weekly")
    def api_weekly_report():
        week_start = request.args.get("week_start")
        week_end = request.args.get("week_end")
        if not week_start or not week_end:
            week_start, week_end = models.week_range()
        return jsonify(generate_weekly_report(week_start, week_end))

    @app.get("/api/reports/weekly/pdf")
    def api_weekly_pdf():
        week_start = request.args.get("week_start")
        if not week_start:
            week_start, _ = models.week_range()
        path, filename = generate_weekly_pdf(week_start)
        return send_file(path, as_attachment=True, download_name=filename, mimetype="application/pdf")

    return app


def _start_runtime_services() -> None:
    global _shutdown_hook_registered
    worker_enabled = models.get_setting_bool("background_worker_enabled", True)
    if worker_enabled:
        try:
            ensure_background_worker()
        except Exception:
            pass
    else:
        try:
            if models.get_setting_bool("auto_start_monitoring", False):
                start_monitoring(models.get_setting_int("monitoring_interval_seconds", 60))
        except Exception:
            pass
        try:
            if models.get_setting_bool("health_auto_import_enabled", True):
                start_health_import_scheduler()
        except Exception:
            pass
    try:
        maybe_create_auto_backup("startup")
    except Exception:
        pass
    if not _shutdown_hook_registered:
        atexit.register(_shutdown_runtime_services)
        _shutdown_hook_registered = True


def _shutdown_runtime_services() -> None:
    try:
        stop_monitoring()
    except Exception:
        pass
    try:
        stop_health_import_scheduler()
    except Exception:
        pass
    try:
        maybe_create_auto_backup("shutdown")
    except Exception:
        pass


def _monitoring_status_payload(worker_result: dict | None = None) -> dict:
    overview = get_background_worker_overview()
    if worker_result:
        overview["last_start_attempt"] = worker_result
    worker = overview.get("worker") or {}
    worker_monitoring = worker.get("monitoring") or {}
    status = worker_monitoring if worker.get("running") else get_monitoring_status()
    payload = dict(status)
    payload["worker"] = overview
    payload["background_mode"] = overview.get("enabled", False)
    payload["desired_state"] = overview.get("desired_monitoring_state", "off")
    if overview.get("enabled") and not worker.get("running"):
        payload["status"] = "worker_off" if payload.get("status") == "off" else payload.get("status")
        payload["last_error"] = payload.get("last_error") or "Worker em segundo plano ainda nao confirmou heartbeat."
    return payload


def _health_operation_payload(status: dict, worker_overview: dict, scheduler: dict) -> dict:
    settings = status.get("settings") or {}
    scan = status.get("scan") or {}
    worker = worker_overview.get("worker") or {}
    last_import = status.get("last_import") or {}
    errors = list(scan.get("errors") or [])
    scheduler_error = scheduler.get("last_error") or ""
    last_error = scheduler_error or last_import.get("error_message") or (errors[0] if errors else "")
    auto_enabled = str(settings.get("health_auto_import_enabled", "true")).lower() == "true"
    worker_enabled = bool(worker_overview.get("enabled"))
    worker_running = bool(worker.get("running"))
    scheduler_running = bool(scheduler.get("running"))
    folder_ready = bool(scan.get("exists"))

    payload = {
        "level": "ok",
        "code": "ready",
        "title": "Health Importer pronto",
        "message": "Importacao local pronta para usar dados do Health Sync.",
        "action": "",
        "auto_import_enabled": auto_enabled,
        "worker_enabled": worker_enabled,
        "worker_running": worker_running,
        "scheduler_running": scheduler_running,
        "folder_ready": folder_ready,
        "last_error": last_error,
    }

    if not folder_ready:
        payload.update(
            {
                "level": "error",
                "code": "folder_missing",
                "title": "Pasta do Health Sync nao encontrada",
                "message": "O app ainda nao encontrou a pasta base configurada para importar CSVs.",
                "action": "Abra o Google Drive Desktop ou ajuste o caminho em Avancado.",
            }
        )
    elif last_import.get("status") == "error":
        payload.update(
            {
                "level": "error",
                "code": "last_import_error",
                "title": "Ultima importacao falhou",
                "message": last_error or "A ultima importacao terminou com erro.",
                "action": "Confira os logs recentes e tente importar novamente.",
            }
        )
    elif not auto_enabled:
        payload.update(
            {
                "level": "warning",
                "code": "auto_disabled",
                "title": "Importacao automatica desligada",
                "message": "Os dados de saude so serao atualizados quando voce importar manualmente.",
                "action": "Ative a importacao automatica em Avancado quando quiser rodar em segundo plano.",
            }
        )
    elif worker_enabled and not worker_running:
        payload.update(
            {
                "level": "warning",
                "code": "worker_waiting",
                "title": "Worker aguardando heartbeat",
                "message": "O app tentou usar o worker em segundo plano, mas ele ainda nao confirmou atividade.",
                "action": "Aguarde alguns segundos ou use Iniciar worker em Configuracoes.",
            }
        )
    elif not worker_enabled and not scheduler_running:
        payload.update(
            {
                "level": "warning",
                "code": "scheduler_stopped",
                "title": "Scheduler local parado",
                "message": "A importacao automatica esta ligada, mas o scheduler desta janela nao esta rodando.",
                "action": "Salve as configuracoes de saude ou reinicie o app.",
            }
        )
    elif scheduler_error:
        payload.update(
            {
                "level": "warning",
                "code": "scheduler_error",
                "title": "Scheduler encontrou um erro",
                "message": scheduler_error,
                "action": "Confira o caminho configurado e os arquivos CSV recentes.",
            }
        )
    elif scan.get("missing_folders"):
        payload.update(
            {
                "level": "warning",
                "code": "folders_missing",
                "title": "Algumas pastas nao foram encontradas",
                "message": "O importador esta ativo, mas nem todas as pastas esperadas do Health Sync existem.",
                "action": "Verifique as pastas sincronizadas pelo Health Sync no Google Drive Desktop.",
            }
        )

    return payload


def _ensure_worker_if_allowed(force: bool = False) -> dict:
    if current_app and current_app.config.get("TESTING"):
        return {"started": False, "enabled": False, "testing": True, "worker": get_background_worker_overview().get("worker")}
    if force or models.get_setting_bool("background_worker_enabled", True):
        return ensure_background_worker()
    return {"started": False, "enabled": False, "worker": get_background_worker_overview().get("worker")}


def get_app() -> Flask:
    global _app_instance
    if _app_instance is None:
        _app_instance = create_app()
    return _app_instance


def should_open_browser() -> bool:
    value = os.getenv("ROUTINE_IA_OPEN_BROWSER")
    if value is not None:
        normalized = value.strip().lower()
        if normalized in {"0", "false", "no", "off"}:
            return False
        if normalized in {"1", "true", "yes", "on"}:
            return True
    try:
        return models.get_setting_bool("auto_open_browser", True)
    except Exception:
        return True


def open_browser_later(url: str = APP_URL) -> None:
    timer = threading.Timer(1.0, lambda: webbrowser.open_new(url))
    timer.daemon = True
    timer.start()


def run_web_app() -> None:
    debug = os.getenv("ROUTINE_IA_DEBUG", "0").strip().lower() in {"1", "true", "yes"}
    if should_open_browser():
        open_browser_later()
    get_app().run(host=HOST, port=PORT, debug=debug, use_reloader=False)


def run_desktop_app() -> None:
    run_web_app()


if __name__ == "__main__":
    run_web_app()
