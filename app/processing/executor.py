"""
FFmpeg executor — runs FFmpeg plan via subprocess, streams stdout/stderr,
parses time= progress, renames output upon completion.

Ported from executePlan.ts.
"""

import os
import re
import time
import subprocess
from typing import Callable, Optional

from app.utils.ffmpeg_binary import resolve_ffmpeg
from app.processing.plan_builder import FfmpegPlan


def _parse_time_to_seconds(val: str) -> float:
    match = re.search(r"(\d+):(\d+):(\d+\.?\d*)", val)
    if not match:
        return 0.0
    h, m, s = float(match.group(1)), float(match.group(2)), float(match.group(3))
    return h * 3600 + m * 60 + s


def execute_ffmpeg_plan(
    plan: FfmpegPlan,
    duration_seconds: float,
    emit_log: Callable[[str], None],
    emit_output: Callable[[str], None],
    emit_progress: Callable[[int, str], None],
) -> dict:
    """
    Executes the given FfmpegPlan.
    Returns dict with processing_time_ms.
    """
    ffmpeg_binary = resolve_ffmpeg()
    started_at = time.time()

    emit_log(f"FFmpeg command: {plan.command}")

    # Remove temporary output file if it exists
    if os.path.exists(plan.temp_output_path):
        try:
            os.remove(plan.temp_output_path)
        except OSError:
            pass

    cmd = [ffmpeg_binary] + plan.args

    # Startup process with hidden window on Windows
    startupinfo = None
    creation_flags = 0
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    process = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        startupinfo=startupinfo,
        creationflags=creation_flags,
    )

    import threading

    stderr_lines = []

    def read_stderr():
        if process.stderr:
            for line in iter(process.stderr.readline, ""):
                line_str = line.strip()
                if not line_str:
                    continue
                emit_output(line_str)
                stderr_lines.append(line_str)
                if any(k in line_str.lower() for k in ("error", "invalid", "failed", "option not found", "unrecognized")) and "fontconfig" not in line_str.lower():
                    emit_log(line_str)

    stderr_thread = threading.Thread(target=read_stderr, daemon=True)
    stderr_thread.start()

    last_emitted_progress = -1

    if process.stdout:
        for line in iter(process.stdout.readline, ""):
            line_str = line.strip()
            if line_str.startswith("out_time="):
                t_val = line_str.split("=")[1]
                if duration_seconds > 0:
                    elapsed = _parse_time_to_seconds(t_val)
                    progress = min(99, max(0, int((elapsed / duration_seconds) * 100)))
                    if progress > last_emitted_progress:
                        last_emitted_progress = progress
                        emit_progress(progress, "ffmpeg")

    process.wait()
    stderr_thread.join()

    if process.returncode != 0:
        err_msg = "\n".join(stderr_lines[-10:]) or f"FFmpeg exited with code {process.returncode}."
        raise RuntimeError(err_msg)

    # Rename temp output to target output path
    if os.path.exists(plan.output_path):
        try:
            os.remove(plan.output_path)
        except OSError:
            pass

    os.rename(plan.temp_output_path, plan.output_path)
    processing_time_ms = int((time.time() - started_at) * 1000)

    return {"processing_time_ms": processing_time_ms}
