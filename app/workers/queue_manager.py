"""
QueueManager — manages queue execution and thread pool of JobWorkers.

Ported from jobQueueService.ts.
Controls starting, stopping, concurrency limits, scanning folders, and emitting state updates to UI.
"""

import os
import json
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal

from app.database.repositories.job_repository import JobRepository
from app.database.repositories.script_repository import ScriptRepository
from app.database.repositories.history_repository import HistoryRepository
from app.database.repositories.log_repository import LogRepository
from app.database.repositories.settings_repository import SettingsRepository
from app.processing.scanner import scan_video_files
from app.workers.job_worker import JobWorker
from app.utils.constants import DEFAULT_WORKER_COUNT


class QueueManager(QObject):
    # Signals to UI
    queue_snapshot_updated = pyqtSignal(dict, list)     # (summary, jobs)
    log_emitted = pyqtSignal(str, str, str)            # (level, scope, message)
    ffmpeg_output_emitted = pyqtSignal(str, str)       # (job_id, line)
    progress_updated = pyqtSignal(str, int, str)       # (job_id, progress, operation)
    current_job_changed = pyqtSignal(dict, object)     # (job, script)
    queue_idle = pyqtSignal(dict)                      # (summary)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.job_repo = JobRepository()
        self.script_repo = ScriptRepository()
        self.history_repo = HistoryRepository()
        self.log_repo = LogRepository()
        self.settings_repo = SettingsRepository()

        self.running = False
        self.active_workers: dict[str, JobWorker] = {}

        self.recover_interrupted_session()

    def recover_interrupted_session(self) -> int:
        """Reset any jobs left in 'processing' status back to 'waiting' and log recovery."""
        count = self.job_repo.recover_stuck_jobs()
        if count > 0:
            self._emit_log("info", "queue", f"Startup Recovery: Restored {count} interrupted job(s) from 'processing' to 'waiting'.")
        return count

    def scan_folder(self, input_folder: str, output_folder: str, script_id: Optional[str]) -> dict:
        """Scan input folder for video files and create job records."""
        script_name = None
        script = None
        is_compilation = False

        if script_id:
            script = self.script_repo.find_by_id(script_id)
            if script:
                script_name = script["name"]
                script_data = script
                if "script_json" in script and isinstance(script["script_json"], str):
                    try:
                        script_data = json.loads(script["script_json"])
                    except Exception:
                        pass

                ops = script_data.get("operations", [])
                for op in ops:
                    if op.get("type") == "merge" and op.get("mode") == "folder_compilation":
                        is_compilation = True
                        break

        os.makedirs(output_folder, exist_ok=True)
        discovered = scan_video_files(input_folder, exclude_folder=output_folder)

        # Clear existing waiting jobs when re-scanning (preserve completed history in jobs table)
        self.job_repo.delete_waiting()

        created_jobs = []

        if is_compilation and len(discovered) > 0:
            folder_basename = os.path.basename(os.path.normpath(input_folder)) or "Compilation"
            file_name = f"Compilation_{folder_basename}.mp4"
            target_out = os.path.join(output_folder, file_name)

            job = self.job_repo.create(
                file_name=file_name,
                input_path=discovered[0],
                output_path=target_out,
                script_id=script_id,
                script_name=script_name,
            )
            if job:
                created_jobs.append(job)

            self._emit_log("info", "queue", f"Compilation Mode: Grouped {len(discovered)} videos into 1 single output job: {file_name}")
        else:
            for file_path in discovered:
                rel_path = os.path.relpath(file_path, input_folder)
                target_out = os.path.join(output_folder, rel_path)
                os.makedirs(os.path.dirname(target_out), exist_ok=True)
                file_name = os.path.basename(file_path)

                job = self.job_repo.create(
                    file_name=file_name,
                    input_path=file_path,
                    output_path=target_out,
                    script_id=script_id,
                    script_name=script_name,
                )
                if job:
                    created_jobs.append(job)

            self._emit_log("info", "queue", f"Scanned {len(created_jobs)} videos from {input_folder}.")

        self.emit_snapshot()

        return {
            "created": len(created_jobs),
            "skipped": 0,
            "jobs": created_jobs,
        }

    def delete_jobs(self, job_ids: list[str]) -> None:
        """Delete specific jobs from queue and database, then update snapshot."""
        if not job_ids:
            return
        self.job_repo.delete_many(job_ids)
        self._emit_log("info", "queue", f"Removed {len(job_ids)} job(s) from queue.")
        self.emit_snapshot()

    def start(self):
        if self.running:
            return
        self.running = True
        self._emit_log("info", "queue", "Queue started.")
        self._process_next()

    def stop(self):
        self.running = False
        self._emit_log("warn", "queue", "Queue stopped.")

        for job_id, worker in list(self.active_workers.items()):
            worker.terminate()
            worker.wait()

    def emit_snapshot(self):
        summary = self.job_repo.count_by_status()
        summary["totalVideos"] = sum(summary.values())
        summary["averageTimeMs"] = self.job_repo.average_processing_time_ms()
        summary["lastJob"] = self.job_repo.last_completed_filename()
        summary["running"] = self.running

        jobs = self.job_repo.list_all()
        self.queue_snapshot_updated.emit(summary, jobs)

    def _process_next(self):
        if not self.running:
            return

        concurrency = self.settings_repo.get_concurrency_limit(DEFAULT_WORKER_COUNT)
        if len(self.active_workers) >= concurrency:
            return

        waiting_jobs = self.job_repo.list_waiting()
        if not waiting_jobs:
            if len(self.active_workers) == 0:
                self.running = False
                summary = self.job_repo.count_by_status()
                summary["totalVideos"] = sum(summary.values())
                summary["averageTimeMs"] = self.job_repo.average_processing_time_ms()
                summary["lastJob"] = self.job_repo.last_completed_filename()
                summary["running"] = False
                self._emit_log("info", "queue", "Queue idle (all jobs processed).")
                self.queue_idle.emit(summary)
            return

        job_to_run = waiting_jobs[0]
        job_id = job_to_run["id"]

        script = None
        if job_to_run.get("script_id"):
            script = self.script_repo.find_by_id(job_to_run["script_id"])

        self.job_repo.mark_started(job_id)
        self.current_job_changed.emit(job_to_run, script)
        self.emit_snapshot()

        worker = JobWorker(job_to_run, script)
        worker.log_emitted.connect(self._on_worker_log)
        worker.output_emitted.connect(self._on_worker_ffmpeg_output)
        worker.progress_updated.connect(self._on_worker_progress)
        worker.completed.connect(self._on_worker_completed)
        worker.failed.connect(self._on_worker_failed)

        self.active_workers[job_id] = worker
        worker.start()

        # Try to launch another if below concurrency limit
        if len(self.active_workers) < concurrency:
            self._process_next()

    def _on_worker_log(self, level: str, scope: str, message: str):
        self._emit_log(level, scope, message)
        self.log_repo.create(level=level, scope=scope, message=message)

    def _on_worker_ffmpeg_output(self, job_id: str, line: str):
        self.ffmpeg_output_emitted.emit(job_id, line)

    def _on_worker_progress(self, job_id: str, progress: int, operation: str):
        self.job_repo.update_progress(job_id, progress)
        self.progress_updated.emit(job_id, progress, operation)

    def _on_worker_completed(self, job_id: str, result):
        if job_id in self.active_workers:
            del self.active_workers[job_id]

        self.job_repo.update_progress(job_id, 100)
        self.progress_updated.emit(job_id, 100, "Completed")

        self.job_repo.mark_completed(
            job_id=job_id,
            processing_time_ms=result.processing_time_ms,
            duration_before=f"{result.duration_before:.2f}s" if result.duration_before else None,
            duration_after=f"{result.duration_after:.2f}s" if result.duration_after else None,
            resolution_before=result.resolution_before,
            resolution_after=result.resolution_after,
            ffmpeg_command=result.command,
        )

        job = self.job_repo.find_by_id(job_id)
        if job:
            self.history_repo.create(
                file_name=job["file_name"],
                input_path=job["input_path"],
                output_path=job["output_path"],
                script_name=job.get("script_name"),
                status="completed",
                processing_time_ms=result.processing_time_ms,
                resolution_before=result.resolution_before,
                resolution_after=result.resolution_after,
            )

        self.emit_snapshot()
        self._process_next()

    def _on_worker_failed(self, job_id: str, error_message: str):
        if job_id in self.active_workers:
            del self.active_workers[job_id]

        self._emit_log("error", "worker", f"Job failed: {error_message}")
        self.progress_updated.emit(job_id, 0, "Failed")
        self.job_repo.mark_failed(job_id, error_message)
        job = self.job_repo.find_by_id(job_id)
        if job:
            self.history_repo.create(
                file_name=job["file_name"],
                input_path=job["input_path"],
                output_path=job["output_path"],
                script_name=job.get("script_name"),
                status="failed",
                error_message=error_message,
            )

        self.emit_snapshot()
        self._process_next()

    def _emit_log(self, level: str, scope: str, message: str):
        self.log_emitted.emit(level, scope, message)
