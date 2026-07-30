"""
Single video processing pipeline orchestrator.

Ported directly from processVideo.ts.
Runs: probe input -> build plan -> execute FFmpeg -> probe output -> assemble stats.
"""

import os
from dataclasses import dataclass
from typing import Callable, Optional

from app.processing.probe import probe_media
from app.processing.plan_builder import build_ffmpeg_plan, FfmpegPlan
from app.processing.executor import execute_ffmpeg_plan


@dataclass
class ProcessVideoResult:
    processing_time_ms: int
    duration_before: float
    duration_after: float
    resolution_before: Optional[str]
    resolution_after: Optional[str]
    command: str


def process_video(
    job: dict,
    script: Optional[dict],
    emit_log: Callable[[str, str, str], None],  # (level, scope, message)
    emit_output: Callable[[str], None],
    emit_progress: Callable[[int, str], None],
    emit_current_operation: Callable[[str], None],
) -> ProcessVideoResult:
    """
    Process a single video job through the pipeline.
    """
    emit_current_operation("Probing input")
    emit_log("info", "worker", f"Probing {job['file_name']}")

    input_probe = probe_media(job["input_path"])
    resolution_before = input_probe.resolution_str()

    emit_log(
        "info",
        "worker",
        f"Input duration {input_probe.duration_seconds:.2f}s, resolution {resolution_before or 'unknown'}",
    )

    emit_progress(5, "probe")
    emit_current_operation("Building FFmpeg plan")

    plan: Optional[FfmpegPlan] = None
    try:
        plan = build_ffmpeg_plan(
            input_path=job["input_path"],
            output_path=job["output_path"],
            script=script,
            probe=input_probe,
        )

        emit_log("info", "ffmpeg", plan.command)
        emit_current_operation("Executing FFmpeg")

        exec_res = execute_ffmpeg_plan(
            plan=plan,
            duration_seconds=plan.total_duration if plan.total_duration > 0 else input_probe.duration_seconds,
            emit_log=lambda msg: emit_log("info", "ffmpeg", msg),
            emit_output=emit_output,
            emit_progress=emit_progress,
        )

        emit_current_operation("Probing output")
        output_probe = probe_media(job["output_path"])
        resolution_after = output_probe.resolution_str()

        emit_log("info", "worker", f"Completed {job['file_name']}")

        return ProcessVideoResult(
            processing_time_ms=exec_res["processing_time_ms"],
            duration_before=input_probe.duration_seconds,
            duration_after=output_probe.duration_seconds,
            resolution_before=resolution_before,
            resolution_after=resolution_after,
            command=plan.command,
        )
    finally:
        if plan and plan.temp_files_to_clean:
            for tmp_file in plan.temp_files_to_clean:
                if os.path.exists(tmp_file):
                    try:
                        os.remove(tmp_file)
                    except OSError:
                        pass
