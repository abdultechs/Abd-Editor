"""
Job repository — CRUD for the jobs table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.database.connection import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobRepository:
    """All SQL for the jobs table lives here."""

    # ── Read ──────────────────────────────────────────────────────────────────

    def list_all(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_waiting(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status='waiting' ORDER BY created_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    def find_by_id(self, job_id: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None

    def count_by_status(self) -> dict[str, int]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
        ).fetchall()
        result = {"waiting": 0, "processing": 0, "completed": 0, "failed": 0, "cancelled": 0}
        for row in rows:
            result[row["status"]] = row["cnt"]
        return result

    def average_processing_time_ms(self) -> int:
        conn = get_connection()
        row = conn.execute(
            "SELECT AVG(processing_time_ms) as avg FROM jobs WHERE status='completed' AND processing_time_ms IS NOT NULL"
        ).fetchone()
        val = row["avg"] if row else None
        return int(val) if val else 0

    def last_completed_filename(self) -> Optional[str]:
        conn = get_connection()
        row = conn.execute(
            "SELECT file_name FROM jobs WHERE status='completed' ORDER BY completed_at DESC LIMIT 1"
        ).fetchone()
        return row["file_name"] if row else None

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(
        self,
        file_name: str,
        input_path: str,
        output_path: str,
        script_id: Optional[str] = None,
        script_name: Optional[str] = None,
    ) -> dict:
        conn = get_connection()
        job_id = str(uuid.uuid4())
        now = _now()
        conn.execute(
            """
            INSERT INTO jobs
              (id, script_id, script_name, file_name, input_path, output_path,
               status, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'waiting', 0, ?, ?)
            """,
            (job_id, script_id, script_name, file_name, input_path, output_path, now, now),
        )
        conn.commit()
        return self.find_by_id(job_id)  # type: ignore[return-value]

    def update_status(self, job_id: str, status: str) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE jobs SET status=?, updated_at=? WHERE id=?",
            (status, _now(), job_id),
        )
        conn.commit()

    def update_progress(self, job_id: str, progress: int) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE jobs SET progress=?, status='processing', updated_at=? WHERE id=?",
            (progress, _now(), job_id),
        )
        conn.commit()

    def mark_started(self, job_id: str) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE jobs SET status='processing', progress=0, started_at=?, updated_at=? WHERE id=?",
            (_now(), _now(), job_id),
        )
        conn.commit()

    def recover_stuck_jobs(self) -> int:
        """Reset any jobs left in 'processing' status back to 'waiting' with progress 0."""
        conn = get_connection()
        cur = conn.execute(
            "UPDATE jobs SET status='waiting', progress=0, updated_at=? WHERE status='processing'",
            (_now(),),
        )
        conn.commit()
        return cur.rowcount

    def mark_completed(
        self,
        job_id: str,
        processing_time_ms: int,
        duration_before: Optional[str],
        duration_after: Optional[str],
        resolution_before: Optional[str],
        resolution_after: Optional[str],
        ffmpeg_command: Optional[str] = None,
    ) -> Optional[dict]:
        conn = get_connection()
        now = _now()
        conn.execute(
            """
            UPDATE jobs SET
              status='completed', progress=100, completed_at=?,
              processing_time_ms=?, duration_before=?, duration_after=?,
              resolution_before=?, resolution_after=?, ffmpeg_command=?,
              error_message=NULL, updated_at=?
            WHERE id=?
            """,
            (
                now, processing_time_ms,
                duration_before, duration_after,
                resolution_before, resolution_after,
                ffmpeg_command, now, job_id,
            ),
        )
        conn.commit()
        return self.find_by_id(job_id)

    def mark_failed(self, job_id: str, error_message: str) -> Optional[dict]:
        conn = get_connection()
        now = _now()
        conn.execute(
            """
            UPDATE jobs SET status='failed', completed_at=?, error_message=?, updated_at=?
            WHERE id=?
            """,
            (now, error_message, now, job_id),
        )
        conn.commit()
        return self.find_by_id(job_id)

    def update_probe_info(
        self,
        job_id: str,
        duration_before: Optional[str],
        resolution_before: Optional[str],
    ) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE jobs SET duration_before=?, resolution_before=?, updated_at=? WHERE id=?",
            (duration_before, resolution_before, _now(), job_id),
        )
        conn.commit()

    def delete_all(self) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM jobs")
        conn.commit()

    def delete_waiting(self) -> None:
        """Remove only jobs in 'waiting' status (e.g. when rescanning folder for active queue)."""
        conn = get_connection()
        conn.execute("DELETE FROM jobs WHERE status='waiting'")
        conn.commit()

    def delete_by_id(self, job_id: str) -> None:
        """Remove a single job by ID."""
        conn = get_connection()
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()

    def delete_many(self, job_ids: list[str]) -> None:
        """Remove multiple jobs by ID."""
        if not job_ids:
            return
        conn = get_connection()
        placeholders = ",".join("?" for _ in job_ids)
        conn.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", job_ids)
        conn.commit()

    def clear_by_output_path(self, output_path: str) -> None:
        """Remove any existing job record for this output path (allows re-run)."""
        conn = get_connection()
        conn.execute("DELETE FROM jobs WHERE output_path=?", (output_path,))
        conn.commit()

    def find_by_input_and_output(self, input_path: str, output_path: str) -> Optional[dict]:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM jobs WHERE input_path=? AND output_path=?", (input_path, output_path)
        ).fetchone()
        return dict(row) if row else None

    def update_script(self, job_id: str, script_id: Optional[str], script_name: Optional[str]) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE jobs SET script_id=?, script_name=?, status='waiting', progress=0, updated_at=? WHERE id=?",
            (script_id, script_name, _now(), job_id),
        )
        conn.commit()
