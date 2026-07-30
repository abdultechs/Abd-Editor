"""
Video Crop-Zoom Operation.

Crops and scales up the entire video frame (e.g. 105%, 110%, 115%, 120%, 125%, 150%)
to trim unwanted outer edges, side bars, or original watermarks.
"""

from app.processing.operations.base import OperationResult, OperationContext


def apply_zoom(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op keys:
      factor / zoom_factor: float (default 1.15 for 115% zoom)
      mode: "crop_top_bottom" (cuts top & bottom as video scales wider, default) | "proportional"
    """
    factor = float(op.get("zoom_factor", op.get("factor", 1.15)))
    if factor <= 1.0:
        return OperationResult()

    mode = str(op.get("mode", "crop_top_bottom")).lower()
    w = ctx.video_width or 1920
    h = ctx.video_height or 1080

    if "prop" in mode:
        crop_w = int(w / factor)
        crop_h = int(h / factor)
    else:
        # Crop Top & Bottom (makes video scale wider, cutting upper and lower parts)
        crop_w = w
        crop_h = int(h / factor)

    # Ensure even dimensions for H.264 / HEVC codecs
    if crop_w % 2 != 0:
        crop_w -= 1
    if crop_h % 2 != 0:
        crop_h -= 1

    vf = f"crop={crop_w}:{crop_h},scale={w}:{h}"
    return OperationResult(video_filters=[vf])
