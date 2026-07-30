"""
Flip operation — ported from applyFlip() in operations/index.ts.
"""

from app.processing.operations.base import OperationResult, OperationContext


def apply_flip(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op keys:
      direction: "horizontal" | "vertical"
    """
    direction = op.get("direction", "horizontal")
    filter_name = "hflip" if direction == "horizontal" else "vflip"
    return OperationResult(video_filters=[filter_name])
