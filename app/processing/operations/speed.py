"""
Speed operation — ported from applySpeed() in operations/index.ts.

FFmpeg atempo is limited to [0.5, 2.0], so we chain multiple atempo
filters for values outside that range (same strategy as the original).
"""

from app.processing.operations.base import OperationResult, OperationContext


def _build_atempo_chain(speed: float) -> str:
    """Build a chained atempo filter string for any speed value."""
    factors: list[float] = []
    remaining = speed

    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0

    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5

    factors.append(round(remaining, 6))
    return ",".join(f"atempo={f}" for f in factors)


def apply_speed(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op keys:
      value: float — speed multiplier (e.g. 1.25 = 25% faster, 0.5 = half speed)
    """
    value = float(op.get("value", 1.0))
    if value <= 0:
        value = 1.0

    video = [f"setpts=(PTS-STARTPTS)/{value}"]
    audio = [_build_atempo_chain(value)]
    return OperationResult(video_filters=video, audio_filters=audio)
