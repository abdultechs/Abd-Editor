"""
Trim operation — ported from operations/index.ts → applyTrim().
Supports both absolute seconds and percentage-based trim.
"""

from app.processing.operations.base import OperationResult, OperationContext


def _fmt(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:.3f}"


def apply_trim(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op keys (all optional):
      start            — start in seconds
      end              — end in seconds
      start_percentage — start as % of total duration
      end_percentage   — end as % of total duration
    """
    start = op.get("start")
    end = op.get("end")

    if op.get("startPercentage") is not None:
        start = ctx.duration_seconds * op["startPercentage"] / 100.0
    if op.get("endPercentage") is not None:
        end = ctx.duration_seconds * op["endPercentage"] / 100.0

    st_val = float(start) if start is not None else 0.0
    et_val = float(end) if end is not None else ctx.duration_seconds

    # Update context duration to reflected trimmed duration
    new_dur = max(0.0, et_val - st_val)
    if ctx and ctx.duration_seconds:
        ctx.duration_seconds = min(ctx.duration_seconds, new_dur)

    video: list[str] = []
    audio: list[str] = []

    if start is not None or end is not None:
        parts = []
        if start is not None:
            parts.append(f"start={_fmt(max(float(start), 0))}")
        if end is not None:
            parts.append(f"end={_fmt(max(float(end), 0))}")
        expr = ":".join(parts)
        video += [f"trim={expr}", "setpts=PTS-STARTPTS"]
        audio += [f"atrim={expr}", "asetpts=PTS-STARTPTS"]

    return OperationResult(video_filters=video, audio_filters=audio)
