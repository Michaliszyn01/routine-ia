from __future__ import annotations


DEFAULT_INTERVAL_SECONDS = 60


class UsageTracker:
    def __init__(self, interval_seconds: int = DEFAULT_INTERVAL_SECONDS) -> None:
        self.interval_seconds = normalize_interval(interval_seconds)

    def calculate_focus_increment(self, focused_app: dict | None, interval_seconds: int | None = None) -> list[dict]:
        if not focused_app:
            return []
        seconds = normalize_interval(interval_seconds or self.interval_seconds)
        return [
            {
                "app_name": str(focused_app.get("app_name") or focused_app.get("process_name") or "Desconhecido"),
                "label": str(focused_app.get("label") or "Neutro"),
                "seconds": seconds,
            }
        ]

    def calculate_increment(self, apps: list[dict], interval_seconds: int | None = None) -> list[dict]:
        seconds = normalize_interval(interval_seconds or self.interval_seconds)
        seen: set[str] = set()
        increments: list[dict] = []
        for app in apps:
            app_name = str(app.get("app_name") or app.get("process_name") or "Desconhecido")
            key = app_name.lower()
            if key in seen:
                continue
            seen.add(key)
            increments.append(
                {
                    "app_name": app_name,
                    "label": str(app.get("label") or "Neutro"),
                    "seconds": seconds,
                }
            )
        return increments


def normalize_interval(value: int | float | str | None) -> int:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        parsed = DEFAULT_INTERVAL_SECONDS
    return max(30, min(parsed, 120))
