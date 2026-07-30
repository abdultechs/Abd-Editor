"""
Script repository — CRUD for the scripts table.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.database.connection import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScriptRepository:
    """All SQL for the scripts table lives here."""

    # ── Read ──────────────────────────────────────────────────────────────────

    def list_all(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM scripts ORDER BY is_favorite DESC, name ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    def find_by_id(self, script_id: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM scripts WHERE id = ?", (script_id,)
        ).fetchone()
        return dict(row) if row else None

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(self, name: str, script_json: dict, description: str = "") -> dict:
        conn = get_connection()
        script_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            """
            INSERT INTO scripts (id, name, description, script_json, is_favorite, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, 1, ?, ?)
            """,
            (script_id, name, description, json.dumps(script_json), now, now),
        )
        conn.commit()
        return self.find_by_id(script_id)  # type: ignore[return-value]

    def update(self, script_id: str, name: str, script_json: dict, description: str = "") -> Optional[dict]:
        conn = get_connection()
        now = _now()
        conn.execute(
            """
            UPDATE scripts SET name=?, description=?, script_json=?, updated_at=? WHERE id=?
            """,
            (name, description, json.dumps(script_json), now, script_id),
        )
        conn.commit()
        return self.find_by_id(script_id)

    def rename(self, script_id: str, new_name: str) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE scripts SET name=?, updated_at=? WHERE id=?",
            (new_name, _now(), script_id),
        )
        conn.commit()

    def toggle_favorite(self, script_id: str) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE scripts SET is_favorite = NOT is_favorite, updated_at=? WHERE id=?",
            (_now(), script_id),
        )
        conn.commit()

    def delete(self, script_id: str) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM scripts WHERE id=?", (script_id,))
        conn.commit()

    def duplicate(self, script_id: str) -> Optional[dict]:
        original = self.find_by_id(script_id)
        if not original:
            return None
        script_data = json.loads(original["script_json"])
        return self.create(
            name=f"{original['name']} (Copy)",
            script_json=script_data,
            description=original.get("description", ""),
        )

    def import_from_json(self, data: dict) -> dict:
        """Import a script from a JSON dict (exported format)."""
        name = data.get("name", "Imported Script")
        description = data.get("description", "")
        # Store the whole dict as the json blob
        return self.create(name=name, script_json=data, description=description)
