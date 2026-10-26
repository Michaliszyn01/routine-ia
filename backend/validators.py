from __future__ import annotations

from datetime import datetime


class ValidationError(ValueError):
    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


def validate_date(value: str | None, field: str = "date") -> str:
    if not value:
        raise ValidationError("Data obrigatória.", {field: "Data obrigatória."})
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError("Data inválida.", {field: "Use o formato YYYY-MM-DD."}) from exc
    return value


def number(value, default: float = 0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Valor numérico inválido.") from exc


def bounded_float(
    value,
    field: str,
    label: str,
    *,
    minimum: float = 0,
    maximum: float | None = None,
    default: float = 0,
) -> float:
    parsed = number(value, default)
    if parsed < minimum:
        raise ValidationError(f"{label} não pode ser negativo.", {field: f"{label} não pode ser negativo."})
    if maximum is not None and parsed > maximum:
        raise ValidationError(f"{label} não pode passar de {maximum:g}.", {field: f"Máximo permitido: {maximum:g}."})
    return parsed


def bounded_int(
    value,
    field: str,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
    default: int = 0,
) -> int:
    parsed = int(round(bounded_float(value, field, label, minimum=minimum, maximum=maximum, default=default)))
    return parsed


def bool_to_int(value) -> int:
    if isinstance(value, str):
        return int(value.strip().lower() in {"1", "true", "yes", "on", "sim"})
    return int(bool(value))


def sanitize_text(value, limit: int = 2000) -> str:
    return str(value or "").strip()[:limit]


def validate_daily_payload(payload: dict) -> dict:
    date_value = validate_date(payload.get("date"))
    return {
        "date": date_value,
        "workout_done": bool_to_int(payload.get("workout_done")),
        "workout_hours": bounded_float(payload.get("workout_hours"), "workout_hours", "Horas de treino", maximum=24),
        "study_done": bool_to_int(payload.get("study_done")),
        "study_hours": bounded_float(payload.get("study_hours"), "study_hours", "Horas de estudo", maximum=24),
        "programming_done": bool_to_int(payload.get("programming_done")),
        "programming_hours": bounded_float(payload.get("programming_hours"), "programming_hours", "Horas de programação", maximum=24),
        "game_hours": bounded_float(payload.get("game_hours"), "game_hours", "Horas de jogo", maximum=24),
        "reading_done": bool_to_int(payload.get("reading_done")),
        "reading_hours": bounded_float(payload.get("reading_hours"), "reading_hours", "Horas de leitura", maximum=24),
        "sleep_hours": bounded_float(payload.get("sleep_hours"), "sleep_hours", "Sono", maximum=24),
        "steps": bounded_int(payload.get("steps"), "steps", "Passos"),
        "energy": bounded_int(payload.get("energy"), "energy", "Energia", minimum=1, maximum=5, default=3),
        "mood": bounded_int(payload.get("mood"), "mood", "Humor", minimum=1, maximum=5, default=3),
        "observation": sanitize_text(payload.get("observation")),
    }


def validate_goal_payload(payload: dict) -> dict:
    return {
        "weekly_days_goal": bounded_int(payload.get("weekly_days_goal"), "weekly_days_goal", "Dias por semana", minimum=0, maximum=7),
        "daily_hours_goal": bounded_float(payload.get("daily_hours_goal"), "daily_hours_goal", "Meta de horas por dia", maximum=24),
        "weekly_hours_goal": bounded_float(payload.get("weekly_hours_goal"), "weekly_hours_goal", "Meta de horas por semana", maximum=168),
        "daily_weight": bounded_float(payload.get("daily_weight"), "daily_weight", "Peso diário", maximum=100),
        "max_daily_hours": bounded_float(payload.get("max_daily_hours"), "max_daily_hours", "Limite máximo diário", maximum=24),
        "active": bool_to_int(payload.get("active", True)),
    }


def validate_health_payload(payload: dict) -> dict:
    date_value = validate_date(payload.get("date"))
    source = sanitize_text(payload.get("source") or "Manual", 80) or "Manual"
    if source not in {"Manual", "Samsung Health", "Health Sync", "Health Connect", "CSV"}:
        source = "Manual"
    return {
        "date": date_value,
        "sleep_hours_auto": bounded_float(payload.get("sleep_hours_auto"), "sleep_hours_auto", "Sono automático", maximum=24),
        "steps_auto": bounded_int(payload.get("steps_auto"), "steps_auto", "Passos automáticos"),
        "workout_minutes_auto": bounded_int(payload.get("workout_minutes_auto"), "workout_minutes_auto", "Minutos de treino", maximum=1440),
        "average_heart_rate": bounded_int(payload.get("average_heart_rate"), "average_heart_rate", "Frequência cardíaca média", maximum=250),
        "resting_heart_rate": bounded_int(payload.get("resting_heart_rate"), "resting_heart_rate", "Frequência cardíaca em repouso", maximum=250),
        "stress_average": bounded_float(payload.get("stress_average"), "stress_average", "Estresse médio", maximum=100),
        "weight_kg": bounded_float(payload.get("weight_kg"), "weight_kg", "Peso", maximum=500),
        "source": source,
        "observation": sanitize_text(payload.get("observation")),
    }


def validate_settings_payload(payload: dict) -> dict:
    theme = sanitize_text(payload.get("theme") or "dark", 20)
    if theme not in {"dark", "light"}:
        theme = "dark"
    week_start = sanitize_text(payload.get("week_start") or "monday", 20)
    if week_start != "monday":
        week_start = "monday"

    interval = bounded_int(
        payload.get("monitoring_interval_seconds"),
        "monitoring_interval_seconds",
        "Intervalo do monitoramento",
        minimum=30,
        maximum=120,
        default=60,
    )
    health_interval = bounded_int(
        payload.get("health_import_interval_hours"),
        "health_import_interval_hours",
        "Intervalo da importacao de saude",
        minimum=1,
        maximum=24,
        default=4,
    )
    ai_timeout = bounded_int(
        payload.get("ai_evaluation_timeout_seconds"),
        "ai_evaluation_timeout_seconds",
        "Timeout da avaliacao IA",
        minimum=1,
        maximum=30,
        default=8,
    )

    return {
        "app_name": sanitize_text(payload.get("app_name") or "Routine IA", 80) or "Routine IA",
        "theme": theme,
        "auto_open_browser": "true" if bool_to_int(payload.get("auto_open_browser", True)) else "false",
        "week_start": week_start,
        "desktop_mode": "true" if bool_to_int(payload.get("desktop_mode", True)) else "false",
        "low_friction_mode": "true" if bool_to_int(payload.get("low_friction_mode", False)) else "false",
        "today_simplified_view": "true" if bool_to_int(payload.get("today_simplified_view", False)) else "false",
        "start_with_windows": "true" if bool_to_int(payload.get("start_with_windows", False)) else "false",
        "start_minimized": "true" if bool_to_int(payload.get("start_minimized", False)) else "false",
        "run_in_background": "true" if bool_to_int(payload.get("run_in_background", True)) else "false",
        "background_worker_enabled": "true" if bool_to_int(payload.get("background_worker_enabled", True)) else "false",
        "auto_start_monitoring": "true" if bool_to_int(payload.get("auto_start_monitoring", False)) else "false",
        "monitoring_worker_state": _monitoring_worker_state(payload.get("monitoring_worker_state")),
        "monitoring_interval_seconds": str(interval),
        "health_sync_base_path": sanitize_text(payload.get("health_sync_base_path") or r"G:\Meu Drive", 500) or r"G:\Meu Drive",
        "health_auto_import_enabled": "true" if bool_to_int(payload.get("health_auto_import_enabled", True)) else "false",
        "health_import_interval_hours": str(health_interval),
        "ai_evaluation_enabled": "true" if bool_to_int(payload.get("ai_evaluation_enabled", True)) else "false",
        "ai_evaluation_model": sanitize_text(payload.get("ai_evaluation_model") or "gemma3:4b", 80) or "gemma3:4b",
        "ai_evaluation_url": sanitize_text(payload.get("ai_evaluation_url") or "http://127.0.0.1:11434", 500) or "http://127.0.0.1:11434",
        "ai_evaluation_timeout_seconds": str(ai_timeout),
    }


def _monitoring_worker_state(value) -> str:
    state = sanitize_text(value or "off", 20)
    if state not in {"active", "paused", "off"}:
        return "off"
    return state
