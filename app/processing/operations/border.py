"""
Border Frame Operation.

Adds customizable solid colored borders/frames around the video.
Supports rich solid color presets (Black, White, Deep Purple, Electric Blue, Emerald Green, Gold, etc.)
and custom hex codes.
"""

from app.processing.operations.base import OperationResult, OperationContext

COLOR_MAP = {
    "violet": "0x8B5CF6",
    "magenta": "0xD946EF",
    "teal": "0x0D9488",
    "fuchsia": "0xE11D48",
    "deep purple": "0x7C3AED",
    "purple": "0x7C3AED",
    "bright cyan": "0x06B6D4",
    "cyan": "0x06B6D4",
    "coral": "0xF97316",
    "mustard yellow": "0xEAB308",
    "tangerine": "0xFF6B00",
    "mint green": "0x10B981",
    "emerald green": "0x10B981",
    "green": "0x10B981",
    "electric blue": "0x2563EB",
    "blue": "0x2563EB",
    "lavender": "0xA855F7",
    "navy blue": "0x1E3A8A",
    "navy": "0x1E3A8A",
    "forest green": "0x15803D",
    "black": "black",
    "white": "white",
    "red": "red",
    "yellow": "0xEAB308",
    "orange": "0xFF6B00",
}


def _resolve_color(color_name: str) -> str:
    if not color_name:
        return "black"
    color_str = color_name.strip().lower()
    if color_str.startswith("solid "):
        color_str = color_str[6:].strip()
    elif color_str.startswith("solid_"):
        color_str = color_str[6:].strip()

    if color_str.startswith("#"):
        hex_val = color_str.lstrip("#")
        return f"0x{hex_val}"
    return COLOR_MAP.get(color_str, color_str)


def apply_border(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op keys:
      thickness: int (default 20px outer border)
      color: str (color preset name or hex code)
      mode: "sides_only" (Left & Right only, default) | "all_sides"
      enable_inner_border / enableInnerBorder: bool (default True)
      inner_thickness / innerThickness: int (default 4px)
      inner_color / innerColor: str (default "white")
    """
    thickness = int(op.get("thickness", 20))
    if thickness <= 0:
        return OperationResult()

    color_val = _resolve_color(str(op.get("color", "black")))
    mode = str(op.get("mode", "sides_only")).lower()
    w = ctx.video_width or 1920
    h = ctx.video_height or 1080

    enable_inner = bool(op.get("enable_inner_border", op.get("enableInnerBorder", True)))
    inner_thick = int(op.get("inner_thickness", op.get("innerThickness", 4)))
    inner_color_val = _resolve_color(str(op.get("inner_color", op.get("innerColor", "white"))))

    vf_list = []

    # 1. Inner Border Line (e.g. white line adjacent to video)
    if enable_inner and inner_thick > 0:
        if "all" in mode:
            vf_list.append(f"pad=w=iw+{2 * inner_thick}:h=ih+{2 * inner_thick}:x={inner_thick}:y={inner_thick}:color={inner_color_val}")
        else:
            vf_list.append(f"pad=w=iw+{2 * inner_thick}:h=ih:x={inner_thick}:y=0:color={inner_color_val}")

    # 2. Main Outer Colored Border
    if "all" in mode:
        vf_list.append(f"pad=w=iw+{2 * thickness}:h=ih+{2 * thickness}:x={thickness}:y={thickness}:color={color_val},scale={w}:{h}")
    else:
        vf_list.append(f"pad=w=iw+{2 * thickness}:h=ih:x={thickness}:y=0:color={color_val},scale={w}:{h}")

    return OperationResult(video_filters=[",".join(vf_list)])
