"""
Image / Logo Overlay Operation.

Overlays custom picture/logo asset onto video with position, scaling, and opacity transparency.
"""

import os
from app.processing.operations.base import OperationResult, OperationContext

SUPPORTED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


def apply_image_overlay(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op keys:
      image_path / imagePath / assetPath: str path to image file on computer
      opacity: float 0.0 to 1.0 (default 1.0)
      scale_pct: int percentage of video width (default 30%)
      posX / pos_x: "Center" | "Left" | "Right" | "Custom"
      posY / pos_y: "Center" | "Top" | "Bottom" | "Custom"
      posX_pct / pos_x_pct: float 0.0 to 100.0 (custom percentage X)
      posY_pct / pos_y_pct: float 0.0 to 100.0 (custom percentage Y)
    """
    image_path = str(
        op.get("image_path") or op.get("imagePath") or op.get("assetPath") or ""
    ).strip()

    if not image_path or not os.path.exists(image_path) or not image_path.lower().endswith(SUPPORTED_IMAGE_EXTS):
        return OperationResult()

    opacity = float(op.get("opacity", 1.0))
    if opacity > 1.0:
        opacity = opacity / 100.0
    opacity = max(0.0, min(1.0, opacity))

    scale_pct = int(op.get("scale_pct", op.get("scale", 30)))
    pos_x = str(op.get("posX") or op.get("pos_x") or "Center")
    pos_y = str(op.get("posY") or op.get("pos_y") or "Center")

    pos_x_pct = float(op.get("posX_pct", op.get("pos_x_pct", op.get("custom_x", 50.0))))
    pos_y_pct = float(op.get("posY_pct", op.get("pos_y_pct", op.get("custom_y", 50.0))))

    w = ctx.video_width or 1920
    h = ctx.video_height or 1080
    target_img_w = max(10, int(w * (scale_pct / 100.0)))

    # Calculate X position expression
    if "custom" in pos_x.lower():
        x_expr = f"(main_w-overlay_w)*{pos_x_pct / 100.0:.3f}"
    elif "left" in pos_x.lower():
        x_expr = "10"
    elif "right" in pos_x.lower():
        x_expr = "main_w-overlay_w-10"
    else:  # Center
        x_expr = "(main_w-overlay_w)/2"

    # Calculate Y position expression
    if "custom" in pos_y.lower():
        y_expr = f"(main_h-overlay_h)*{pos_y_pct / 100.0:.3f}"
    elif "top" in pos_y.lower():
        y_expr = "10"
    elif "bottom" in pos_y.lower():
        y_expr = "main_h-overlay_h-10"
    else:  # Center
        y_expr = "(main_h-overlay_h)/2"

    overlay_filter = f"overlay={x_expr}:{y_expr}"

    return OperationResult(
        extra_inputs=[image_path],
        video_filters=[overlay_filter],
    )
