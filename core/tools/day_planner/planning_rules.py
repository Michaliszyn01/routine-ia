from __future__ import annotations

from .planner_schemas import ENERGY_LEVELS, PLAN_MODES


MODE_LABELS = {
    "light": "Dia leve",
    "normal": "Dia normal",
    "strong": "Dia forte",
}


def normalize_energy(value: str | None) -> str:
    text = (value or "media").strip().lower()
    aliases = {"low": "baixa", "medium": "media", "mid": "media", "high": "alta"}
    text = aliases.get(text, text)
    return text if text in ENERGY_LEVELS else "media"


def normalize_mode(value: str | None) -> str:
    text = (value or "").strip().lower()
    aliases = {"leve": "light", "normal": "normal", "forte": "strong"}
    text = aliases.get(text, text)
    return text if text in PLAN_MODES else ""


def suggest_mode(*, energy_level: str, sleep_seconds: int, day_late: bool = False, requested_mode: str | None = None) -> tuple[str, str]:
    manual = normalize_mode(requested_mode)
    if manual:
        return manual, f"Modo escolhido manualmente: {MODE_LABELS[manual]}."
    sleep_hours = sleep_seconds / 3600 if sleep_seconds else 0
    if energy_level == "baixa":
        return "light", "Energia baixa. Vamos simplificar o dia."
    if sleep_hours and sleep_hours < 6:
        return "light", "Sono abaixo de 6h. O plano foi reduzido para ficar realista."
    if day_late:
        return "light", "O dia ja esta andando. Vamos salvar o essencial."
    if energy_level == "alta" and sleep_hours >= 7:
        return "strong", "Energia alta e sono bom. Dia forte liberado, sem forcar."
    if sleep_hours and sleep_hours < 7:
        return "normal", "Sono entre 6h e 7h. Dia normal com blocos moderados."
    return "normal", "Energia media. Dia normal com blocos claros."


def block_profile(mode: str) -> dict:
    if mode == "light":
        return {"main": 25, "short": 15, "break": 10, "max_blocks": 5}
    if mode == "strong":
        return {"main": 50, "short": 25, "break": 10, "max_blocks": 8}
    return {"main": 40, "short": 25, "break": 10, "max_blocks": 6}


def status_message(mode: str, *, replanned: bool = False) -> str:
    if replanned:
        return "Seu plano foi ajustado para ficar mais realista. Ainda da para salvar uma parte importante do dia."
    if mode == "light":
        return "Vamos simplificar o dia. Comece pelo menor passo."
    if mode == "strong":
        return "Dia forte sugerido. Comece pela tarefa mais importante."
    return "Plano do dia gerado. Comece pelo proximo passo claro."

