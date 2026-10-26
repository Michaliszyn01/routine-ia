"""Exporta, sem escrita no SQLite, os dados do Routine IA úteis para a UFPR.

Uso:
    py -3.14 scripts/export_ufpr_data.py
    py -3.14 scripts/export_ufpr_data.py --output C:\\caminho\\ufpr.json

O banco é aberto com ``mode=ro``. O único arquivo criado é o JSON de saída.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


# Ao executar ``py scripts/export_ufpr_data.py``, o Python usa ``scripts`` como
# primeiro caminho de importação. Incluímos a raiz do projeto para reutilizar
# somente o resolvedor oficial de caminhos persistentes.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCHEMA_VERSION = "1.0"
ACADEMIC_CATEGORIES = {"estudo", "study"}
PRODUCTIVE_LABELS = {"Estudo", "Produtivo", "Projeto"}
RISK_LABELS = {"Risco", "Distracao"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera a exportação acadêmica do Routine IA para a UFPR.")
    parser.add_argument("--database", type=Path, help="Caminho do routine.db. O padrão é o banco persistente do app.")
    parser.add_argument("--output", type=Path, help="Arquivo JSON de saída. O padrão é a pasta exports do app.")
    return parser.parse_args()


def default_paths() -> tuple[Path, Path]:
    # A importação só resolve os caminhos oficiais do aplicativo; não abre nem altera o banco.
    from backend.paths import get_database_path, get_exports_dir

    return get_database_path(), get_exports_dir() / "routine_ia_ufpr_export.json"


def connect_read_only(path: Path) -> sqlite3.Connection:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {resolved}")
    connection = sqlite3.connect(f"{resolved.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def rows(connection: sqlite3.Connection, query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(query, tuple(params)).fetchall()]


def normalize_timestamp(value: Any) -> str | None:
    """Padroniza a separação ISO sem criar fuso horário inexistente na fonte."""
    if value is None or value == "":
        return None
    text = str(value).strip()
    if len(text) >= 11 and text[10] == " ":
        return text[:10] + "T" + text[11:]
    return text


def number_or_none(value: Any, digits: int | None = None) -> float | int | None:
    if value is None or value == "":
        return None
    number = float(value)
    if digits is not None:
        return round(number, digits)
    return int(number) if number.is_integer() else number


def bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(int(value))


def hours_from_seconds(value: Any) -> float | None:
    seconds = number_or_none(value)
    return round(float(seconds) / 3600, 2) if seconds is not None else None


def minutes_from_seconds(value: Any) -> float | None:
    seconds = number_or_none(value)
    return round(float(seconds) / 60, 2) if seconds is not None else None


def accuracy(correct: Any, total: Any) -> float | None:
    denominator = number_or_none(total)
    numerator = number_or_none(correct)
    if denominator is None or denominator <= 0 or numerator is None:
        return None
    return round(float(numerator) * 100 / float(denominator), 2)


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone() is not None


def require_tables(connection: sqlite3.Connection, required: set[str]) -> None:
    missing = sorted(table for table in required if not table_exists(connection, table))
    if missing:
        raise RuntimeError("O banco não possui as tabelas esperadas: " + ", ".join(missing))


def source_coverage(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    tables = {
        "daily_records": "date",
        "health_data": "date",
        "health_sleep_daily": "date",
        "study_sessions": "date",
        "mock_exams": "date",
        "study_errors": "date",
        "study_review_queue": "created_at",
        "focus_sessions": "date",
        "focus_app_usage": "created_at",
        "monitoring_app_usage_daily": "date",
        "goals": None,
        "life_goals": "created_at",
        "weekly_plan_items": "date",
        "daily_plan_blocks": "created_at",
        "custom_habits": "created_at",
        "habit_logs": "date",
    }
    coverage: dict[str, dict[str, Any]] = {}
    for table, date_column in tables.items():
        count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        entry: dict[str, Any] = {"registros_na_fonte": int(count)}
        if date_column:
            first, last = connection.execute(
                f'SELECT MIN("{date_column}"), MAX("{date_column}") FROM "{table}"'
            ).fetchone()
            entry.update({"primeiro_registro": normalize_timestamp(first), "ultimo_registro": normalize_timestamp(last)})
        coverage[table] = entry
    return coverage


def read_source(connection: sqlite3.Connection) -> dict[str, list[dict[str, Any]]]:
    return {
        "daily_records": rows(connection, "SELECT * FROM daily_records ORDER BY date, id"),
        "health_data": rows(connection, "SELECT * FROM health_data ORDER BY date, id"),
        "health_sleep_daily": rows(connection, "SELECT * FROM health_sleep_daily ORDER BY date, id"),
        "study_sessions": rows(connection, "SELECT * FROM study_sessions ORDER BY date, id"),
        "mock_exams": rows(connection, "SELECT * FROM mock_exams ORDER BY date, id"),
        "study_errors": rows(connection, "SELECT * FROM study_errors ORDER BY date, id"),
        "study_review_queue": rows(connection, "SELECT * FROM study_review_queue ORDER BY study_error_id, id"),
        "focus_sessions": rows(connection, "SELECT * FROM focus_sessions ORDER BY date, id"),
        "focus_app_usage": rows(connection, "SELECT * FROM focus_app_usage ORDER BY session_id, id"),
        "monitoring_app_usage_daily": rows(
            connection, "SELECT * FROM monitoring_app_usage_daily ORDER BY date, label, app_name, id"
        ),
        "goals": rows(connection, "SELECT * FROM goals ORDER BY category, id"),
        "life_goals": rows(connection, "SELECT * FROM life_goals ORDER BY id"),
        "weekly_plan_items": rows(connection, "SELECT * FROM weekly_plan_items ORDER BY date, id"),
        "daily_plan_blocks": rows(connection, "SELECT * FROM daily_plan_blocks ORDER BY plan_id, id"),
        "daily_plans": rows(connection, "SELECT * FROM daily_plans ORDER BY date, id"),
        "custom_habits": rows(connection, "SELECT * FROM custom_habits ORDER BY id"),
        "habit_logs": rows(connection, "SELECT * FROM habit_logs ORDER BY date, id"),
    }


def build_daily_context(source: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    daily_by_date = {item["date"]: item for item in source["daily_records"]}
    health_by_date = {item["date"]: item for item in source["health_data"]}
    sleep_by_date = {item["date"]: item for item in source["health_sleep_daily"]}
    sessions_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in source["study_sessions"]:
        sessions_by_date[item["date"]].append(item)
    focus_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in source["focus_sessions"]:
        focus_by_date[item["date"]].append(item)
    usage_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in source["monitoring_app_usage_daily"]:
        usage_by_date[item["date"]].append(item)

    dates = set(daily_by_date) | set(health_by_date) | set(sleep_by_date) | set(sessions_by_date) | set(focus_by_date) | set(usage_by_date)
    context: list[dict[str, Any]] = []
    for date_value in sorted(dates):
        daily = daily_by_date.get(date_value)
        health = health_by_date.get(date_value)
        sleep = sleep_by_date.get(date_value)
        sessions = sessions_by_date.get(date_value, [])
        focus = focus_by_date.get(date_value, [])
        usage = usage_by_date.get(date_value, [])
        auto_sleep_seconds = number_or_none(sleep.get("total_sleep_seconds")) if sleep else None
        auto_sleep_hours = hours_from_seconds(auto_sleep_seconds) if auto_sleep_seconds is not None else None
        health_sleep_hours = number_or_none(health.get("sleep_hours_auto"), 2) if health else None
        manual_sleep_hours = number_or_none(daily.get("sleep_hours"), 2) if daily else None
        preferred_sleep = next(
            (
                (value, source_name)
                for value, source_name in (
                    (auto_sleep_hours, "health_sleep_daily"),
                    (health_sleep_hours, "health_data"),
                    (manual_sleep_hours, "daily_records"),
                )
                if value is not None and value > 0
            ),
            (None, None),
        )
        total_questions = sum(int(item.get("questions_done") or 0) for item in sessions)
        correct_answers = sum(int(item.get("correct_answers") or 0) for item in sessions)
        total_usage_seconds = sum(int(item.get("total_seconds") or 0) for item in usage)
        productive_usage_seconds = sum(
            int(item.get("total_seconds") or 0) for item in usage if item.get("label") in PRODUCTIVE_LABELS
        )
        risk_usage_seconds = sum(
            int(item.get("total_seconds") or 0) for item in usage if item.get("label") in RISK_LABELS
        )
        context.append(
            {
                "data": date_value,
                "rotina": None
                if daily is None
                else {
                    "source_id": daily["id"],
                    "pontuacao_diaria": number_or_none(daily.get("daily_score"), 2),
                    "estudo_marcado_como_feito": bool_or_none(daily.get("study_done")),
                    "horas_estudo_registro_diario": number_or_none(daily.get("study_hours"), 2),
                    "horas_leitura_registro_diario": number_or_none(daily.get("reading_hours"), 2),
                    "energia": number_or_none(daily.get("energy")),
                    "humor": number_or_none(daily.get("mood")),
                    "observacao": daily.get("observation") or None,
                },
                "sono": {
                    "horas_prioritarias": preferred_sleep[0],
                    "fonte_prioritaria": preferred_sleep[1],
                    "horas_automaticas_health_sleep_daily": auto_sleep_hours,
                    "horas_automaticas_health_data": health_sleep_hours,
                    "horas_manuais_daily_records": manual_sleep_hours,
                },
                "estudos_por_sessao": None
                if not sessions
                else {
                    "quantidade_sessoes": len(sessions),
                    "duracao_total_minutos": sum(int(item.get("duration_minutes") or 0) for item in sessions),
                    "questoes_resolvidas": total_questions,
                    "acertos": correct_answers,
                    "taxa_acerto_percentual": accuracy(correct_answers, total_questions),
                },
                "foco": None
                if not focus
                else {
                    "quantidade_sessoes": len(focus),
                    "segundos_focados": sum(int(item.get("focused_seconds") or 0) for item in focus),
                    "segundos_distraidos": sum(int(item.get("distracted_seconds") or 0) for item in focus),
                },
                "uso_pc": None
                if not usage
                else {
                    "segundos_total": total_usage_seconds,
                    "segundos_produtivos": productive_usage_seconds,
                    "segundos_risco_distração": risk_usage_seconds,
                },
            }
        )
    return context


def build_study_sessions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": item["id"],
            "data": item["date"],
            "materia": item.get("subject") or None,
            "topico": item.get("topic") or None,
            "duracao_minutos": number_or_none(item.get("duration_minutes")),
            "questoes_resolvidas": number_or_none(item.get("questions_done")),
            "acertos": number_or_none(item.get("correct_answers")),
            "erros": number_or_none(item.get("wrong_answers")),
            "taxa_acerto_percentual": accuracy(item.get("correct_answers"), item.get("questions_done")),
            "dificuldade": number_or_none(item.get("difficulty")),
            "observacao": item.get("note") or None,
            "criado_em": normalize_timestamp(item.get("created_at")),
        }
        for item in items
    ]


def build_mock_exams(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source_id": item["id"],
            "data": item["date"],
            "nome": item.get("exam_name") or None,
            "area": item.get("area") or None,
            "nota": number_or_none(item.get("score"), 2),
            "total_questoes": number_or_none(item.get("total_questions")),
            "acertos": number_or_none(item.get("correct_answers")),
            "erros": number_or_none(item.get("wrong_answers")),
            "taxa_acerto_percentual": accuracy(item.get("correct_answers"), item.get("total_questions")),
            "nota_redacao": number_or_none(item.get("essay_score"), 2),
            "observacao": item.get("note") or None,
            "criado_em": normalize_timestamp(item.get("created_at")),
        }
        for item in items
    ]


def build_study_errors(items: list[dict[str, Any]], queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue_by_error = {item["study_error_id"]: item for item in queue}
    result = []
    for item in items:
        review = queue_by_error.get(item["id"])
        result.append(
            {
                "source_id": item["id"],
                "data": item["date"],
                "materia": item.get("subject") or None,
                "topico": item.get("topic") or None,
                "tipo_erro": item.get("error_type") or None,
                "descricao": item.get("description") or None,
                "correcao": item.get("correction") or None,
                "revisado": bool_or_none(item.get("reviewed")),
                "fila_revisao": None
                if review is None
                else {
                    "source_id": review["id"],
                    "status": review.get("status") or None,
                    "proxima_revisao": review.get("next_review_date") or None,
                    "intervalo_dias": number_or_none(review.get("interval_days")),
                    "repeticoes": number_or_none(review.get("repetitions")),
                    "fator_facilidade": number_or_none(review.get("ease_factor"), 2),
                    "ultima_revisao_em": normalize_timestamp(review.get("last_reviewed_at")),
                },
            }
        )
    return result


def build_focus_sessions(items: list[dict[str, Any]], usage_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usage_by_session: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in usage_items:
        usage_by_session[int(item["session_id"])].append(item)
    result = []
    for item in items:
        session_usage = usage_by_session.get(int(item["id"]), [])
        result.append(
            {
                "source_id": item["id"],
                "data": item["date"],
                "titulo": item.get("title") or None,
                "tipo_foco": item.get("focus_type") or None,
                "categoria": item.get("category") or None,
                "classificada_como_estudo": str(item.get("focus_type") or "").casefold() in ACADEMIC_CATEGORIES
                or str(item.get("category") or "").casefold() in ACADEMIC_CATEGORIES,
                "status": item.get("status") or None,
                "concluida": bool_or_none(item.get("completed")),
                "inicio_em": normalize_timestamp(item.get("started_at")),
                "fim_em": normalize_timestamp(item.get("ended_at")),
                "planejado_minutos": number_or_none(item.get("planned_minutes")),
                "duracao_registrada_minutos": number_or_none(item.get("duration_minutes")),
                "segundos_reais": number_or_none(item.get("actual_seconds")),
                "segundos_focados": number_or_none(item.get("focused_seconds")),
                "segundos_distraidos": number_or_none(item.get("distracted_seconds")),
                "observacao": item.get("completion_note") or item.get("note") or None,
                "uso_aplicativos_na_sessao": [
                    {
                        "source_id": usage["id"],
                        "aplicativo": usage.get("app_name") or None,
                        "rotulo": usage.get("label") or None,
                        "status_correspondencia": usage.get("match_status") or None,
                        "segundos": number_or_none(usage.get("seconds")),
                    }
                    for usage in session_usage
                ],
            }
        )
    return result


def build_pc_usage(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_date[item["date"]].append(item)
    result = []
    for date_value, day_items in sorted(by_date.items()):
        labels: dict[str, int] = defaultdict(int)
        for item in day_items:
            labels[item.get("label") or "Sem rotulo"] += int(item.get("total_seconds") or 0)
        result.append(
            {
                "data": date_value,
                "segundos_total": sum(int(item.get("total_seconds") or 0) for item in day_items),
                "segundos_produtivos": sum(
                    int(item.get("total_seconds") or 0) for item in day_items if item.get("label") in PRODUCTIVE_LABELS
                ),
                "segundos_risco_distração": sum(
                    int(item.get("total_seconds") or 0) for item in day_items if item.get("label") in RISK_LABELS
                ),
                "por_rotulo": [
                    {"rotulo": label, "segundos": seconds, "minutos": round(seconds / 60, 2)}
                    for label, seconds in sorted(labels.items())
                ],
                "por_aplicativo": [
                    {
                        "source_id": item["id"],
                        "aplicativo": item.get("app_name") or None,
                        "rotulo": item.get("label") or None,
                        "segundos": number_or_none(item.get("total_seconds")),
                        "minutos": minutes_from_seconds(item.get("total_seconds")),
                    }
                    for item in day_items
                ],
            }
        )
    return result


def strict_academic(value: Any) -> bool:
    return str(value or "").strip().casefold() in ACADEMIC_CATEGORIES


def build_academic_goals(source: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    routine_goals = [
        {
            "source_id": item["id"],
            "categoria": item.get("category"),
            "rotulo": item.get("label") or None,
            "meta_horas_diarias": number_or_none(item.get("daily_hours_goal"), 2),
            "meta_horas_semanais": number_or_none(item.get("weekly_hours_goal"), 2),
            "peso_diario": number_or_none(item.get("daily_weight"), 2),
            "maximo_horas_diarias": number_or_none(item.get("max_daily_hours"), 2),
            "ativa": bool_or_none(item.get("active")),
            "atualizada_em": normalize_timestamp(item.get("updated_at")),
        }
        for item in source["goals"]
        if strict_academic(item.get("category"))
    ]
    life_goals = [
        {
            "source_id": item["id"],
            "titulo": item.get("title") or None,
            "descricao": item.get("description") or None,
            "categoria": item.get("category") or None,
            "area_vinculada": item.get("linked_area") or None,
            "prioridade": item.get("priority") or None,
            "status": item.get("status") or None,
            "data_alvo": item.get("target_date") or None,
            "progresso_percentual": number_or_none(item.get("progress_percent"), 2),
        }
        for item in source["life_goals"]
        if strict_academic(item.get("category")) or strict_academic(item.get("linked_area"))
    ]
    return {"metas_rotina": routine_goals, "objetivos_vida": life_goals}


def build_academic_planning(source: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    plan_dates = {item["id"]: item["date"] for item in source["daily_plans"]}
    weekly_items = [
        {
            "source_id": item["id"],
            "data": item.get("date"),
            "titulo": item.get("title") or None,
            "categoria": item.get("category") or None,
            "minutos_estimados": number_or_none(item.get("estimated_minutes")),
            "concluido": bool_or_none(item.get("completed")),
            "observacao": item.get("note") or None,
        }
        for item in source["weekly_plan_items"]
        if strict_academic(item.get("category"))
    ]
    daily_blocks = [
        {
            "source_id": item["id"],
            "data": plan_dates.get(item.get("plan_id")),
            "titulo": item.get("title") or None,
            "tipo": item.get("type") or None,
            "inicio": item.get("start_time") or None,
            "duracao_minutos": number_or_none(item.get("duration_minutes")),
            "prioridade": item.get("priority") or None,
            "status": item.get("status") or None,
        }
        for item in source["daily_plan_blocks"]
        if strict_academic(item.get("type"))
    ]
    return {"itens_semanais": weekly_items, "blocos_diarios": daily_blocks}


def build_academic_habits(source: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    habits = {item["id"]: item for item in source["custom_habits"] if strict_academic(item.get("category"))}
    return [
        {
            "source_id": item["id"],
            "source_habit_id": item.get("habit_id"),
            "data": item.get("date"),
            "concluido": bool_or_none(item.get("completed")),
            "valor": number_or_none(item.get("value"), 2),
            "observacao": item.get("note") or None,
            "habito": {
                "nome": habits[item["habit_id"]].get("name") or None,
                "frequencia": habits[item["habit_id"]].get("frequency") or None,
                "meta_semanal": number_or_none(habits[item["habit_id"]].get("target_per_week")),
            },
        }
        for item in source["habit_logs"]
        if item.get("habit_id") in habits
    ]


def build_export(connection: sqlite3.Connection) -> dict[str, Any]:
    required_tables = {
        "daily_records", "health_data", "health_sleep_daily", "study_sessions", "mock_exams",
        "study_errors", "study_review_queue", "focus_sessions", "focus_app_usage",
        "monitoring_app_usage_daily", "goals", "life_goals", "weekly_plan_items",
        "daily_plan_blocks", "daily_plans", "custom_habits", "habit_logs",
    }
    require_tables(connection, required_tables)
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"Falha na integridade do SQLite: {integrity}")
    source = read_source(connection)
    coverage = source_coverage(connection)
    payload = {
        "formato": "routine_ia_ufpr_export",
        "versao_esquema": SCHEMA_VERSION,
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "origem": {
            "aplicativo": "Routine IA",
            "modo_leitura_banco": "somente_leitura",
            "integridade_sqlite": integrity,
        },
        "metas_academicas": build_academic_goals(source),
        "contexto_diario": build_daily_context(source),
        "sessoes_estudo": build_study_sessions(source["study_sessions"]),
        "simulados": build_mock_exams(source["mock_exams"]),
        "erros_estudo_e_revisoes": build_study_errors(source["study_errors"], source["study_review_queue"]),
        "sessoes_foco": build_focus_sessions(source["focus_sessions"], source["focus_app_usage"]),
        "uso_pc_diario": build_pc_usage(source["monitoring_app_usage_daily"]),
        "planejamento_academico": build_academic_planning(source),
        "habitos_academicos": build_academic_habits(source),
        "cobertura_da_fonte": coverage,
    }
    validate_payload(payload, source)
    payload["validacao"] = {
        "resultado": "aprovado",
        "checagens": [
            "PRAGMA integrity_check retornou ok",
            "IDs das coleções detalhadas são únicos",
            "contagens das coleções detalhadas coincidem com as tabelas de origem",
            "IDs de uso do PC, apps no foco e metas acadêmicas coincidem com a origem",
            "contexto_diario possui uma única linha por data e cobre a união das fontes",
            "JSON gerado preserva nulos para valores ausentes",
        ],
    }
    return payload


def assert_unique_ids(items: list[dict[str, Any]], label: str) -> None:
    ids = [item["source_id"] for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicação detectada em {label}.")


def validate_payload(payload: dict[str, Any], source: dict[str, list[dict[str, Any]]]) -> None:
    assert_unique_ids(payload["sessoes_estudo"], "sessoes_estudo")
    assert_unique_ids(payload["simulados"], "simulados")
    assert_unique_ids(payload["erros_estudo_e_revisoes"], "erros_estudo_e_revisoes")
    assert_unique_ids(payload["sessoes_foco"], "sessoes_foco")
    if len(payload["sessoes_estudo"]) != len(source["study_sessions"]):
        raise ValueError("Perda de sessões de estudo durante a exportação.")
    if len(payload["simulados"]) != len(source["mock_exams"]):
        raise ValueError("Perda de simulados durante a exportação.")
    if len(payload["erros_estudo_e_revisoes"]) != len(source["study_errors"]):
        raise ValueError("Perda de erros de estudo durante a exportação.")
    if len(payload["sessoes_foco"]) != len(source["focus_sessions"]):
        raise ValueError("Perda de sessões de foco durante a exportação.")
    dates = [item["data"] for item in payload["contexto_diario"]]
    if len(dates) != len(set(dates)):
        raise ValueError("Duplicação de data no contexto diário.")
    expected_dates = set()
    for key in ("daily_records", "health_data", "health_sleep_daily", "study_sessions", "focus_sessions", "monitoring_app_usage_daily"):
        expected_dates.update(item["date"] for item in source[key])
    if set(dates) != expected_dates:
        raise ValueError("O contexto diário não cobre exatamente as datas das fontes selecionadas.")
    source_pc_ids = {item["id"] for item in source["monitoring_app_usage_daily"]}
    exported_pc_ids = {
        item["source_id"]
        for day in payload["uso_pc_diario"]
        for item in day["por_aplicativo"]
    }
    if exported_pc_ids != source_pc_ids:
        raise ValueError("Perda ou duplicação no uso diário do PC.")
    source_focus_usage_ids = {item["id"] for item in source["focus_app_usage"]}
    exported_focus_usage_ids = {
        item["source_id"]
        for session in payload["sessoes_foco"]
        for item in session["uso_aplicativos_na_sessao"]
    }
    if exported_focus_usage_ids != source_focus_usage_ids:
        raise ValueError("Perda ou duplicação no uso de aplicativos durante foco.")
    expected_goal_ids = {item["id"] for item in source["goals"] if strict_academic(item.get("category"))}
    exported_goal_ids = {item["source_id"] for item in payload["metas_academicas"]["metas_rotina"]}
    if exported_goal_ids != expected_goal_ids:
        raise ValueError("Perda ou duplicação nas metas acadêmicas de rotina.")


def main() -> int:
    args = parse_args()
    default_database, default_output = default_paths()
    database = args.database or default_database
    output = args.output or default_output
    try:
        with connect_read_only(database) as connection:
            payload = build_export(connection)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Confirma que o arquivo final continua um JSON legível e completo.
        parsed = json.loads(output.read_text(encoding="utf-8"))
        if parsed.get("formato") != "routine_ia_ufpr_export" or parsed.get("validacao", {}).get("resultado") != "aprovado":
            raise ValueError("O arquivo escrito não passou na validação final.")
    except Exception as error:  # Mantém a mensagem objetiva para uso manual no Windows.
        print(f"Falha na exportação UFPR: {error}", file=sys.stderr)
        return 1
    print(f"Exportação UFPR criada: {output}")
    print(f"Contextos diários: {len(payload['contexto_diario'])}")
    print(f"Sessões de estudo: {len(payload['sessoes_estudo'])}; simulados: {len(payload['simulados'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
