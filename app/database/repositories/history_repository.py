"""
History repository — stores completed/failed job snapshots.
"""

import json
import uuid
from datetime import datetime, timezone

from app.database.connection import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HistoryRepository:
    def create(self, **kwargs) -> None:
        conn = get_connection()
        job_id = kwargs.get("job_id", str(uuid.uuid4()))
        script_id = kwargs.get("script_id")
        status = kwargs.get("status", "completed")
        summary_json = json.dumps(kwargs)
        conn.execute(
            """
            INSERT INTO history (id, job_id, script_id, status, summary_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                job_id,
                script_id,
                status,
                summary_json,
                _now(),
            ),
        )
        conn.commit()

    def add_from_job(self, job: dict, extra: dict) -> None:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO history (id, job_id, script_id, status, summary_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                job["id"],
                job.get("script_id"),
                job["status"],
                json.dumps({**job, **extra}),
                _now(),
            ),
        )
        conn.commit()

    def list_all(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM history ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def clear_all(self) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM history")
        conn.commit()
