from __future__ import annotations

import backend.ai_evaluator as ai_evaluator


def test_day_evaluation_uses_gemma_when_available(client, monkeypatch):
    monkeypatch.setattr(ai_evaluator, "_call_ollama", lambda *args: "Leitura: dia avaliado pelo Gemma.")

    payload = client.post("/api/ai/day-evaluation", json={"date": "2026-07-20"}).get_json()

    assert payload["ok"] is True
    assert payload["source"] == "gemma"
    assert payload["model"] == "gemma3:4b"
    assert "Gemma" in payload["evaluation"]


def test_week_evaluation_falls_back_when_ollama_is_unavailable(client, monkeypatch):
    def fail(*args):
        raise RuntimeError("Ollama indisponivel.")

    monkeypatch.setattr(ai_evaluator, "_call_ollama", fail)

    payload = client.post(
        "/api/ai/week-evaluation",
        json={"week_start": "2026-07-20", "week_end": "2026-07-26"},
    ).get_json()

    assert payload["ok"] is True
    assert payload["source"] == "local-fallback"
    assert "Leitura:" in payload["evaluation"]
    assert payload["error"] == "Ollama indisponivel."


def test_settings_include_ai_evaluation_controls(client):
    payload = client.get("/api/settings").get_json()
    settings = payload["settings"]

    assert settings["ai_evaluation_enabled"] == "true"
    assert settings["ai_evaluation_model"] == "gemma3:4b"
    assert settings["ai_evaluation_url"] == "http://127.0.0.1:11434"
