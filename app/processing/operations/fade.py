"""
Fade operation for Video and Audio.

Modes/Fade Types:
  in    — Fade In at start
  out   — Fade Out at end
  both  — Fade In at start and Fade Out at end

Targets:
  both  — Apply to Video and Audio
  video — Apply to Video only
  audio — Apply to Audio only
"""

from app.processing.operations.base import OperationResult, OperationContext


def apply_fade(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op options:
      fade_type:         "in" | "out" | "both" (default "both")
      target:            "both" | "video" | "audio" (default "both")
      fade_in_duration:  float in seconds (default 1.0)
      fade_out_duration: float in seconds (default 1.0)
      fade_in_start:     float in seconds (default 0.0)
      fade_out_start:    float in seconds (optional, 0.0 for auto calculation)
      color:             str video fade color (default "black")
    """
    fade_type = op.get("fade_type") or op.get("fadeType") or op.get("mode", "both")
    target = op.get("target", "both")

    fade_in_dur = float(op.get("fade_in_duration") or op.get("fadeInDuration") or op.get("fade_in_dur", 1.0))
    fade_out_dur = float(op.get("fade_out_duration") or op.get("fadeOutDuration") or op.get("fade_out_dur", 1.0))

    fade_in_st = float(op.get("fade_in_start") or op.get("fadeInStart", 0.0))
    
    # Fade out start timestamp auto calculation based on effective video duration
    media_dur = ctx.duration_seconds if ctx and ctx.duration_seconds else 0.0
    custom_out_st = op.get("fade_out_start") if op.get("fade_out_start") is not None else op.get("fadeOutStart")
    if custom_out_st is not None and float(custom_out_st) > 0 and float(custom_out_st) < media_dur:
        fade_out_st = float(custom_out_st)
    else:
        fade_out_st = max(0.0, media_dur - fade_out_dur)

    color = op.get("color", "black")

    video_filters: list[str] = []
    audio_filters: list[str] = []

    apply_video = target in ("both", "video")
    apply_audio = target in ("both", "audio")

    # Fade In
    if fade_type in ("in", "both"):
        if apply_video:
            video_filters.append(f"fade=t=in:st={fade_in_st}:d={fade_in_dur}:color={color}")
        if apply_audio:
            audio_filters.append(f"afade=t=in:st={fade_in_st}:d={fade_in_dur}")

    # Fade Out
    if fade_type in ("out", "both"):
        if apply_video:
            video_filters.append(f"fade=t=out:st={fade_out_st}:d={fade_out_dur}:color={color}")
        if apply_audio:
            audio_filters.append(f"afade=t=out:st={fade_out_st}:d={fade_out_dur}")

    return OperationResult(
        video_filters=video_filters,
        audio_filters=audio_filters,
    )
