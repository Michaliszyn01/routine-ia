from __future__ import annotations

from flask import Blueprint, jsonify, request

from backend.db_engine import diagnostics
from backend.study_reviews import list_due_reviews, record_review
from backend.tasks import archive_task, complete_task, create_task, get_task, list_tasks, update_task
from backend.workspace import get_workspace


workspace_api = Blueprint("workspace_api", __name__)


@workspace_api.get("/api/workspace")
def api_workspace():
    return jsonify(get_workspace(request.args.get("date")))


@workspace_api.get("/api/tasks")
def api_tasks_list():
    return jsonify(
        {
            "ok": True,
            "tasks": list_tasks(
                status=request.args.get("status"),
                area=request.args.get("area"),
                reference_date=request.args.get("date"),
                include_archived=request.args.get("include_archived") == "1",
            ),
        }
    )


@workspace_api.post("/api/tasks")
def api_tasks_create():
    return jsonify({"ok": True, "task": create_task(request.get_json(silent=True) or {})}), 201


@workspace_api.get("/api/tasks/<int:task_id>")
def api_tasks_get(task_id: int):
    task = get_task(task_id)
    if not task:
        return jsonify({"ok": False, "error": "Tarefa nao encontrada."}), 404
    return jsonify({"ok": True, "task": task})


@workspace_api.patch("/api/tasks/<int:task_id>")
def api_tasks_update(task_id: int):
    try:
        task = update_task(task_id, request.get_json(silent=True) or {})
    except LookupError as error:
        return jsonify({"ok": False, "error": str(error)}), 404
    return jsonify({"ok": True, "task": task})


@workspace_api.post("/api/tasks/<int:task_id>/complete")
def api_tasks_complete(task_id: int):
    payload = request.get_json(silent=True) or {}
    try:
        task = complete_task(task_id, payload.get("completed", True) is not False)
    except LookupError as error:
        return jsonify({"ok": False, "error": str(error)}), 404
    return jsonify({"ok": True, "task": task})


@workspace_api.delete("/api/tasks/<int:task_id>")
def api_tasks_archive(task_id: int):
    try:
        task = archive_task(task_id)
    except LookupError as error:
        return jsonify({"ok": False, "error": str(error)}), 404
    return jsonify({"ok": True, "task": task})


@workspace_api.get("/api/studies/reviews")
def api_study_reviews():
    return jsonify({"ok": True, "reviews": list_due_reviews(request.args.get("date"))})


@workspace_api.post("/api/studies/reviews/<int:study_error_id>")
def api_study_review_complete(study_error_id: int):
    payload = request.get_json(silent=True) or {}
    quality = int(payload.get("quality", 3))
    return jsonify(
        {
            "ok": True,
            "review": record_review(study_error_id, quality, payload.get("date")),
        }
    )


@workspace_api.get("/api/system/database")
def api_database_diagnostics():
    return jsonify({"ok": True, "database": diagnostics()})
