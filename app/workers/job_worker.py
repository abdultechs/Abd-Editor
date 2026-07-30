"""
JobWorker — QThread worker that runs video pipeline processing for a single job.

Communicates with main UI thread via Qt Signals. Never blocks the UI.
"""

from PyQt5.QtCore import QThread, pyqtSignal

from app.processing.pipeline import process_video, ProcessVideoResult


class JobWorker(QThread):
    # Signals
    log_emitted = pyqtSignal(str, str, str)            # (level, scope, message)
    output_emitted = pyqtSignal(str, str)              # (job_id, line)
    progress_updated = pyqtSignal(str, int, str)       # (job_id, progress, operation)
    current_operation_changed = pyqtSignal(str, str)  # (job_id, operation)
    completed = pyqtSignal(str, object)                # (job_id, ProcessVideoResult)
    failed = pyqtSignal(str, str)                      # (job_id, error_message)

    def __init__(self, job: dict, script: dict | None, parent=None):
        super().__init__(parent)
        self.job = job
        self.script = script
        self.job_id = job["id"]

    def run(self):
        try:
            res = process_video(
                job=self.job,
                script=self.script,
                emit_log=lambda level, scope, msg: self.log_emitted.emit(level, scope, msg),
                emit_output=lambda line: self.output_emitted.emit(self.job_id, line),
                emit_progress=lambda prog, op: self.progress_updated.emit(self.job_id, prog, op),
                emit_current_operation=lambda op: self.current_operation_changed.emit(self.job_id, op),
            )
            self.completed.emit(self.job_id, res)
        except Exception as exc:
            self.failed.emit(self.job_id, str(exc))
