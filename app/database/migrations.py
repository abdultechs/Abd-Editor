"""
Database migrations.

Each migration is a numbered function that runs once and is tracked
in the schema_version PRAGMA. Adding new migrations never touches old tables.
"""

import sqlite3
from app.database.connection import get_connection


# ── Migration definitions ─────────────────────────────────────────────────────

def _migration_1(conn: sqlite3.Connection) -> None:
    """Initial schema: scripts, jobs, history, logs, settings."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS scripts (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT DEFAULT '',
            script_json TEXT NOT NULL,
            is_favorite INTEGER DEFAULT 0,
            version     INTEGER DEFAULT 1,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id                  TEXT PRIMARY KEY,
            script_id           TEXT,
            script_name         TEXT,
            file_name           TEXT NOT NULL,
            input_path          TEXT NOT NULL,
            output_path         TEXT NOT NULL,
            status              TEXT DEFAULT 'waiting',
            progress            INTEGER DEFAULT 0,
            duration_before     TEXT,
            duration_after      TEXT,
            resolution_before   TEXT,
            resolution_after    TEXT,
            processing_time_ms  INTEGER,
            error_message       TEXT,
            ffmpeg_command      TEXT,
            started_at          TEXT,
            completed_at        TEXT,
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_status      ON jobs(status);
        CREATE INDEX IF NOT EXISTS idx_jobs_created_at  ON jobs(created_at);
        CREATE INDEX IF NOT EXISTS idx_jobs_file_name   ON jobs(file_name);

        CREATE TABLE IF NOT EXISTS history (
            id           TEXT PRIMARY KEY,
            job_id       TEXT NOT NULL,
            script_id    TEXT,
            status       TEXT NOT NULL,
            summary_json TEXT,
            created_at   TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_history_job_id ON history(job_id);

        CREATE TABLE IF NOT EXISTS logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            level      TEXT NOT NULL,
            scope      TEXT NOT NULL,
            message    TEXT NOT NULL,
            job_id     TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_logs_level   ON logs(level);
        CREATE INDEX IF NOT EXISTS idx_logs_job_id  ON logs(job_id);

        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)


_MIGRATIONS = [
    _migration_1,
]


# ── Runner ────────────────────────────────────────────────────────────────────

def run_migrations() -> None:
    """Apply all pending migrations in order."""
    conn = get_connection()

    # SQLite user_version pragma is used as our schema version counter
    current_version: int = conn.execute("PRAGMA user_version;").fetchone()[0]

    for idx, migration_fn in enumerate(_MIGRATIONS):
        migration_version = idx + 1
        if migration_version > current_version:
            migration_fn(conn)
            conn.execute(f"PRAGMA user_version = {migration_version};")
            conn.commit()
