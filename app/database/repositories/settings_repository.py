"""
Settings repository — key-value store for app preferences.
"""

from datetime import datetime, timezone
from app.database.connection import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SettingsRepository:
    def get(self, key: str, default: str = "") -> str:
        conn = get_connection()
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, value, _now()),
        )
        conn.commit()

    def get_all(self) -> dict[str, str]:
        conn = get_connection()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def get_concurrency_limit(self, default: int = 1) -> int:
        val = self.get("workerCount", self.get("concurrency_limit", str(default)))
        try:
            return max(1, int(val))
        except (ValueError, TypeError):
            return default
