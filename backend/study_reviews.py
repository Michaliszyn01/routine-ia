from __future__ import annotations

from datetime import date, timedelta

from .database import get_connection
from .validators import validate_date


def schedule_review(study_error_id: int, start_date: str | None = None) -> dict:
    day = date.fromisoformat(validate_date(start_date or date.today().isoformat()))
    next_review = (day + timedelta(days=1)).isoformat()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO study_review_queue (study_error_id, next_review_date)
            VALUES (?, ?)
            ON CONFLICT(study_error_id) DO NOTHING
            """,
            (study_error_id, next_review),
        )
    return get_review(study_error_id) or {}


def get_review(study_error_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM study_review_queue WHERE study_error_id = ?",
            (study_error_id,),
        ).fetchone()
    return dict(row) if row else None


def list_due_reviews(reference_date: str | None = None, *, include_future: bool = False) -> list[dict]:
    day = validate_date(reference_date or date.today().isoformat())
    comparator = ">=" if include_future else "<="
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT q.*, e.subject, e.topic, e.error_type, e.description, e.correction, e.date AS error_date
            FROM study_review_queue q
            JOIN study_errors e ON e.id = q.study_error_id
            WHERE q.status = 'pending' AND q.next_review_date {comparator} ?
            ORDER BY q.next_review_date, e.subject, e.topic
            """,
            (day,),
        ).fetchall()
    return [dict(row) for row in rows]


def record_review(study_error_id: int, quality: int, reference_date: str | None = None) -> dict:
    if quality not in range(0, 6):
        raise ValueError("Qualidade da revisao precisa estar entre 0 e 5.")
    current = get_review(study_error_id)
    if not current:
        current = schedule_review(study_error_id, reference_date)
    repetitions = int(current.get("repetitions") or 0)
    interval = int(current.get("interval_days") or 1)
    ease = float(current.get("ease_factor") or 2.5)
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        repetitions += 1
        interval = 1 if repetitions == 1 else 6 if repetitions == 2 else max(1, round(interval * ease))
    ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    reviewed_on = date.fromisoformat(validate_date(reference_date or date.today().isoformat()))
    next_review = (reviewed_on + timedelta(days=interval)).isoformat()
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE study_review_queue
            SET next_review_date = ?, interval_days = ?, repetitions = ?, ease_factor = ?,
                last_quality = ?, last_reviewed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE study_error_id = ?
            """,
            (next_review, interval, repetitions, round(ease, 2), quality, study_error_id),
        )
        connection.execute(
            "UPDATE study_errors SET reviewed = ? WHERE id = ?",
            (1 if repetitions >= 3 else 0, study_error_id),
        )
    return get_review(study_error_id) or {}
