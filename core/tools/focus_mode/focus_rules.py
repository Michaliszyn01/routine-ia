from __future__ import annotations

from dataclasses import dataclass


FOCUS_TYPES = {"study", "project", "workout", "organization", "reading", "rest", "generic"}

EXPECTED_APPS = {
    "study": ["Chrome", "Anki", "PDF Reader", "Word", "Notion"],
    "project": ["VS Code", "Codex", "Chrome", "Terminal", "GitHub", "PowerShell", "CMD"],
    "workout": [],
    "organization": ["File Explorer", "Explorer", "Notion", "Excel"],
    "reading": ["Kindle", "PDF Reader", "Browser", "Chrome", "Edge"],
    "rest": ["Spotify"],
    "generic": [],
}

RISK_APPS = {"steam", "discord", "youtube", "roblox", "epic games", "instagram", "tiktok"}
WARNING_APPS = {"chrome", "edge", "browser", "spotify"}

BLOCK_TYPE_MAP = {
    "study": "study",
    "estudo": "study",
    "programming": "project",
    "programacao": "project",
    "project": "project",
    "trabalho": "project",
    "work": "project",
    "workout": "workout",
    "treino": "workout",
    "reading": "reading",
    "leitura": "reading",
    "organization": "organization",
    "organizacao": "organization",
    "admin": "organization",
    "break": "rest",
    "rest": "rest",
    "pausa": "rest",
    "minimum": "generic",
}

LEGACY_CATEGORY_MAP = {
    "study": "estudo",
    "project": "programacao",
    "reading": "leitura",
    "organization": "trabalho",
    "workout": "outro",
    "rest": "outro",
    "generic": "outro",
}


@dataclass(frozen=True)
class FocusRuleResult:
    app_name: str
    label: str
    focus_type: str
    match_status: str
    message: str
    expected_apps: list[str]


def normalize_focus_type(value: str | None) -> str:
    text = str(value or "generic").strip().lower()
    return BLOCK_TYPE_MAP.get(text, text if text in FOCUS_TYPES else "generic")


def focus_type_from_block(block: dict | None) -> str:
    if not block:
        return "generic"
    return normalize_focus_type(block.get("type") or block.get("category"))


def legacy_category_for_focus_type(focus_type: str | None) -> str:
    return LEGACY_CATEGORY_MAP.get(normalize_focus_type(focus_type), "outro")


def expected_apps_for(focus_type: str | None) -> list[str]:
    return list(EXPECTED_APPS.get(normalize_focus_type(focus_type), []))


def app_match_status(focus_type: str | None, app_name: str | None, label: str | None = None) -> FocusRuleResult:
    clean_type = normalize_focus_type(focus_type)
    clean_app = (app_name or "Desconhecido").strip() or "Desconhecido"
    clean_label = (label or "Neutro").strip() or "Neutro"
    haystack = f"{clean_app} {clean_label}".lower()
    expected = expected_apps_for(clean_type)

    if clean_type == "generic":
        status = "match"
        message = "App neutro para este bloco."
    elif clean_type == "rest":
        status = "match" if not app_name or _contains_any(haystack, expected) or clean_label in {"Neutro", "Lazer"} else "warning"
        message = "Combina com descanso." if status == "match" else "Pode estar puxando sua atencao."
    elif _contains_any(haystack, expected):
        status = "match"
        message = "Combina com este bloco."
    elif _contains_any(haystack, RISK_APPS) or clean_label in {"Risco", "Distracao", "Lazer"}:
        status = "mismatch"
        message = "Voce saiu um pouco do bloco."
    elif _contains_any(haystack, WARNING_APPS):
        status = "warning"
        message = "Pode combinar, mas vale conferir se ainda e parte do bloco."
    else:
        status = "mismatch"
        message = "Fora do bloco planejado."

    return FocusRuleResult(
        app_name=clean_app,
        label=clean_label,
        focus_type=clean_type,
        match_status=status,
        message=message,
        expected_apps=expected,
    )


def _contains_any(haystack: str, needles) -> bool:
    return any(str(needle).lower() in haystack for needle in needles if needle)
