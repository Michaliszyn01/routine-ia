from __future__ import annotations

from dataclasses import dataclass
import unicodedata


LABELS = (
    "Produtivo",
    "Estudo",
    "Projeto",
    "Neutro",
    "Comunicacao",
    "Lazer",
    "Distracao",
    "Risco",
)


@dataclass(frozen=True)
class AppRule:
    match: str
    app_name: str
    label: str


DEFAULT_RULES = (
    AppRule("chatgpt.exe", "ChatGPT", "Produtivo"),
    AppRule("code.exe", "VS Code", "Projeto"),
    AppRule("anki.exe", "Anki", "Estudo"),
    AppRule("minecraft", "Minecraft", "Risco"),
    AppRule("robloxplayerbeta.exe", "Roblox", "Risco"),
    AppRule("roblox", "Roblox", "Risco"),
    AppRule("chrome.exe", "Chrome", "Neutro"),
    AppRule("spotify.exe", "Spotify", "Neutro"),
    AppRule("discord.exe", "Discord", "Risco"),
    AppRule("steam.exe", "Steam", "Lazer"),
    AppRule("youtube", "YouTube", "Risco"),
)

BROWSER_PROCESSES = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}

CHATGPT_CONTEXT_RULES = (
    ("g-p-6a48173c443c8191b1bb3edb3f1bf47d-rotina", "ChatGPT - Rotina", "Produtivo"),
    ("g-p-6a0f0b77a22c819190f50b67efe79634-work", "ChatGPT - Work", "Projeto"),
    ("rotina", "ChatGPT - Rotina", "Produtivo"),
    ("routine", "ChatGPT - Rotina", "Produtivo"),
    ("work", "ChatGPT - Work", "Projeto"),
    ("projeto", "ChatGPT - Work", "Projeto"),
    ("estudos", "ChatGPT - Estudos", "Estudo"),
    ("estudo", "ChatGPT - Estudos", "Estudo"),
    ("ingles", "ChatGPT - Ingles", "Estudo"),
    ("english", "ChatGPT - Ingles", "Estudo"),
)

LABEL_SCORE = {
    "Produtivo": 1.0,
    "Estudo": 1.0,
    "Projeto": 1.0,
    "Neutro": 0.0,
    "Comunicacao": 0.0,
    "Lazer": -0.5,
    "Distracao": -1.0,
    "Risco": -1.0,
}


def classify_app(
    process_name: str | None,
    app_name: str | None = None,
    window_title: str | None = None,
    url: str | None = None,
) -> dict:
    process = (process_name or "").strip()
    display = (app_name or "").strip()
    browser_context = _classify_browser_context(process, window_title, url)
    if browser_context:
        return browser_context
    haystack = f"{process} {display}".lower()
    for rule in DEFAULT_RULES:
        if rule.match in haystack:
            return {"app_name": rule.app_name, "label": rule.label}
    return {"app_name": normalize_app_name(display or process), "label": "Neutro"}


def _classify_browser_context(process_name: str, window_title: str | None, url: str | None) -> dict | None:
    if process_name.lower() not in BROWSER_PROCESSES:
        return None
    context = _searchable_text(window_title, url)
    if "chatgpt" not in context and "chatgpt.com" not in context:
        return None
    for keyword, app_name, label in CHATGPT_CONTEXT_RULES:
        if keyword in context:
            return {"app_name": app_name, "label": label}
    return {"app_name": "ChatGPT", "label": "Neutro"}


def _searchable_text(*values: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", " ".join(str(value or "") for value in values).lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def normalize_app_name(value: str | None) -> str:
    name = (value or "").strip()
    if not name:
        return "Desconhecido"
    return name[:-4] if name.lower().endswith(".exe") else name


def score_for_label(label: str | None) -> float:
    return LABEL_SCORE.get(label or "Neutro", 0.0)


def normalize_category(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    aliases = {
        "programacao": "programacao",
        "estudo": "estudo",
        "produtividade": "produtividade",
        "comunicacao": "comunicacao",
        "entretenimento": "entretenimento",
        "jogo": "jogo",
        "musica": "musica",
        "navegador": "navegador",
        "outro": "outro",
    }
    return aliases.get(normalized, "outro")
