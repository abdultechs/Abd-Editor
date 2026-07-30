"""
Log repository — stores structured log records for UI display.
"""

from datetime import datetime, timezone
from app.database.connection import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LogRepository:
    def add(self, level: str, scope: str, message: str, job_id: str | None = None) -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO logs (level, scope, message, job_id, created_at) VALUES (?,?,?,?,?)",
            (level, scope, message, job_id, _now()),
        )
        conn.commit()

    def create(self, level: str, scope: str, message: str, job_id: str | None = None) -> None:
        self.add(level=level, scope=scope, message=message, job_id=job_id)

    def list_recent(self, limit: int = 200) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def list_errors(self, limit: int = 200) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM logs WHERE level='error' ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def clear_all(self) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM logs")
        conn.commit()
