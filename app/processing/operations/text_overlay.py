"""
Upgraded Text Overlay Operation using FFmpeg drawtext filter.

Supports:
- Multiline content
- Font family and weight (Impact, Arial, etc.)
- Font size & color
- Outline / Border (color and thickness)
- Shadow (color and blur offset)
- Text alignment (Left, Center, Right)
- Position X & Y (Percentages / Center)
- Auto word wrapping based on maximum width percentage
"""

import os
import textwrap
from app.processing.operations.base import OperationResult, OperationContext
from app.utils.ffmpeg_binary import escape_for_filter, to_forward_slashes, resolve_default_font


def resolve_font_file(font_family: str = "Impact", font_weight: str = "Bold") -> str | None:
    """Find matching .ttf font file in Windows Fonts directory."""
    fonts_dir = r"C:\Windows\Fonts"
    if not os.path.exists(fonts_dir):
        return resolve_default_font()

    is_bold = "bold" in font_weight.lower()

    font_map = {
        "impact": ("impact.ttf", "impact.ttf"),
        "arial": ("arialbd.ttf" if is_bold else "arial.ttf", "arial.ttf"),
        "comic sans ms": ("comicbd.ttf" if is_bold else "comic.ttf", "comic.ttf"),
        "courier new": ("courbd.ttf" if is_bold else "cour.ttf", "cour.ttf"),
        "times new roman": ("timesbd.ttf" if is_bold else "times.ttf", "times.ttf"),
        "verdana": ("verdanab.ttf" if is_bold else "verdana.ttf", "verdana.ttf"),
        "segoe ui": ("segoeuib.ttf" if is_bold else "segoeui.ttf", "segoeui.ttf"),
        "segoe ui emoji": ("seguiemj.ttf", "seguiemj.ttf"),
        "calibri": ("calibrib.ttf" if is_bold else "calibri.ttf", "calibri.ttf"),
        "trebuchet ms": ("trebucbd.ttf" if is_bold else "trebuc.ttf", "trebuc.ttf"),
        "georgia": ("georgiab.ttf" if is_bold else "georgia.ttf", "georgia.ttf"),
    }

    fam_lower = font_family.lower()
    if fam_lower in font_map:
        target_file = font_map[fam_lower][0]
        full_path = os.path.join(fonts_dir, target_file)
        if os.path.isfile(full_path):
            return full_path
        fallback_file = font_map[fam_lower][1]
        full_path_fb = os.path.join(fonts_dir, fallback_file)
        if os.path.isfile(full_path_fb):
            return full_path_fb

    return resolve_default_font()


def has_emoji(text: str) -> bool:
    """Return True if text contains emoji unicode characters."""
    for char in text:
        code = ord(char)
        if (0x1F600 <= code <= 0x1F64F) or \
           (0x1F300 <= code <= 0x1F5FF) or \
           (0x1F680 <= code <= 0x1F6FF) or \
           (0x1F1E6 <= code <= 0x1F1FF) or \
           (0x2600 <= code <= 0x27BF) or \
           (0x1F900 <= code <= 0x1F9FF) or \
           (0x1FA70 <= code <= 0x1FAFF):
            return True
    return False


def _split_text_and_emojis(text: str):
    chunks = []
    curr = ""
    is_emoji_curr = False
    for char in text:
        is_e = ord(char) > 0x2600
        if is_e == is_emoji_curr:
            curr += char
        else:
            if curr:
                chunks.append((curr, is_emoji_curr))
            curr = char
            is_emoji_curr = is_e
    if curr:
        chunks.append((curr, is_emoji_curr))
    return chunks


def _safe_get_bbox(draw, xy, text, font):
    try:
        return draw.textbbox(xy, text, font=font, embedded_color=True)
    except Exception:
        try:
            return draw.textbbox(xy, text, font=font)
        except Exception:
            return (0, 0, len(text) * 20, 30)


def _safe_draw_text(draw, xy, text, font, fill=None, stroke_width=0, stroke_fill=None):
    try:
        draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill, embedded_color=True)
    except Exception:
        try:
            draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        except Exception:
            pass


def _render_emoji_text_overlay_png(
    text: str,
    font_family: str,
    font_size: int,
    color_name: str,
    enable_outline: bool,
    outline_color_name: str,
    outline_thickness: int,
    enable_shadow: bool,
    shadow_color_name: str,
    shadow_blur: int,
    align: str,
    pos_x: str,
    pos_y: str,
    canvas_w: int,
    canvas_h: int,
    opacity: float = 1.0,
) -> str | None:
    try:
        from PIL import Image, ImageDraw, ImageFont
        import hashlib
    except ImportError:
        return None

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_path = resolve_font_file(font_family, "Bold") or r"C:\Windows\Fonts\impact.ttf"
    emoji_font_path = r"C:\Windows\Fonts\seguiemj.ttf"

    text_font = None
    if font_path and os.path.isfile(font_path):
        try:
            text_font = ImageFont.truetype(font_path, font_size)
        except Exception:
            pass

    if text_font is None:
        fallbacks = [r"C:\Windows\Fonts\impact.ttf", r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeuib.ttf"]
        for fb in fallbacks:
            if os.path.isfile(fb):
                try:
                    text_font = ImageFont.truetype(fb, font_size)
                    break
                except Exception:
                    pass

    if text_font is None:
        try:
            text_font = ImageFont.load_default(size=font_size)
        except Exception:
            text_font = ImageFont.load_default()

    try:
        if os.path.isfile(emoji_font_path):
            emoji_font = ImageFont.truetype(emoji_font_path, font_size)
        else:
            emoji_font = text_font
    except Exception:
        emoji_font = text_font

    color_rgb_map = {
        "yellow": (255, 255, 0, 255),
        "white": (255, 255, 255, 255),
        "black": (0, 0, 0, 255),
        "red": (255, 0, 0, 255),
        "green": (0, 255, 0, 255),
        "blue": (0, 0, 255, 255),
        "cyan": (0, 255, 255, 255),
        "magenta": (255, 0, 255, 255),
        "orange": (255, 165, 0, 255),
        "purple": (128, 0, 128, 255),
    }

    fill_rgba = color_rgb_map.get(color_name.lower(), (255, 255, 0, 255))
    outline_rgba = color_rgb_map.get(outline_color_name.lower(), (0, 0, 0, 255))
    shadow_rgba = color_rgb_map.get(shadow_color_name.lower(), (0, 0, 0, 255))

    lines = text.split("\n")
    line_chunks_list = [_split_text_and_emojis(line) for line in lines]

    line_widths = []
    line_heights = []

    for chunks in line_chunks_list:
        lw = 0
        lh = 0
        for chunk_text, is_e in chunks:
            f = emoji_font if is_e else text_font
            b = _safe_get_bbox(draw, (0, 0), chunk_text, font=f)
            lw += (b[2] - b[0])
            lh = max(lh, b[3] - b[1])
        line_widths.append(lw)
        line_heights.append(max(lh, font_size))

    max_line_w = max(line_widths) if line_widths else 100
    total_h = sum(line_heights) + (len(lines) - 1) * 8

    pos_y_lower = pos_y.lower()
    if "top 5%" in pos_y_lower: start_y = int(canvas_h * 0.05)
    elif "top 10%" in pos_y_lower: start_y = int(canvas_h * 0.10)
    elif "top 20%" in pos_y_lower: start_y = int(canvas_h * 0.20)
    elif "bottom 5%" in pos_y_lower: start_y = int(canvas_h * 0.95 - total_h)
    elif "bottom 10%" in pos_y_lower: start_y = int(canvas_h * 0.90 - total_h)
    elif "bottom 20%" in pos_y_lower: start_y = int(canvas_h * 0.80 - total_h)
    else: start_y = (canvas_h - total_h) // 2

    pos_x_lower = pos_x.lower()
    if "5%" in pos_x_lower:
        margin_pct = 0.05
    elif "10%" in pos_x_lower:
        margin_pct = 0.10
    elif "20%" in pos_x_lower:
        margin_pct = 0.20
    else:
        margin_pct = 0.05

    avail_w = int(canvas_w * (1.0 - 2 * margin_pct))
    base_x = int(canvas_w * margin_pct)

    curr_y = start_y
    for i, chunks in enumerate(line_chunks_list):
        lw = line_widths[i]
        if align.lower() == "center":
            line_x = max(base_x, base_x + (avail_w - lw) // 2)
        elif align.lower() == "right":
            line_x = max(base_x, base_x + (avail_w - lw))
        else:
            line_x = base_x

        curr_x = line_x
        for chunk_text, is_e in chunks:
            f = emoji_font if is_e else text_font
            b = _safe_get_bbox(draw, (0, 0), chunk_text, font=f)
            cw = b[2] - b[0]
            ch_h = b[3] - b[1]
            ch_top = b[1]
            chunk_y = curr_y + (line_heights[i] - ch_h) // 2 - ch_top

            if enable_shadow and shadow_blur > 0:
                _safe_draw_text(draw, (curr_x + shadow_blur, chunk_y + shadow_blur), chunk_text, font=f, fill=shadow_rgba)

            stroke_w = outline_thickness if (enable_outline and outline_thickness > 0) else 0

            _safe_draw_text(
                draw,
                (curr_x, chunk_y),
                chunk_text,
                font=f,
                fill=fill_rgba,
                stroke_width=stroke_w,
                stroke_fill=outline_rgba if stroke_w > 0 else None,
            )

            curr_x += cw

        curr_y += line_heights[i] + 8

    if opacity < 1.0:
        r, g, b, a = img.split()
        a = a.point(lambda p: int(p * opacity))
        img = Image.merge("RGBA", (r, g, b, a))

    temp_dir = r"e:\Abd Editor V1.0\app\temp"
    os.makedirs(temp_dir, exist_ok=True)
    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
    out_path = os.path.join(temp_dir, f"emoji_overlay_{text_hash}.png")
    img.save(out_path)
    return out_path


def apply_text(op: dict, ctx: OperationContext) -> OperationResult:
    """Apply text overlay using FFmpeg drawtext or PIL PNG emoji overlay."""
    raw_text = op.get("text", "")
    if not raw_text:
        return OperationResult()

    font_family = op.get("font", op.get("fontFamily", "Impact"))
    font_size = int(op.get("fontSize", op.get("font_size", 40)))
    font_weight = op.get("fontWeight", op.get("font_weight", "Bold"))
    color = op.get("color", "Yellow")

    enable_outline = bool(op.get("enableOutline", op.get("enable_outline", True)))
    outline_color = op.get("outlineColor", op.get("outline_color", "Black"))
    outline_thickness = int(op.get("outlineThickness", op.get("outline_thickness", 3)))

    enable_shadow = bool(op.get("enableShadow", op.get("enable_shadow", True)))
    shadow_color = op.get("shadowColor", op.get("shadow_color", "Black"))
    shadow_blur = int(op.get("shadowBlur", op.get("shadow_blur", 2)))

    align = op.get("align", "Center")
    pos_x = op.get("posX", op.get("pos_x", "Center"))
    pos_y = op.get("posY", op.get("pos_y", "Top 10%"))

    auto_wrap = bool(op.get("autoWrap", op.get("auto_wrap", True)))
    pos_x_lower = str(pos_x).lower()
    if "5%" in pos_x_lower:
        max_w_pct = 90
    elif "10%" in pos_x_lower:
        max_w_pct = 80
    elif "20%" in pos_x_lower:
        max_w_pct = 60
    else:
        max_w_pct = int(op.get("maxWidth", op.get("max_width", 90)))

    vw = ctx.video_width or 1280
    wrapped_text = _wrap_text(raw_text, auto_wrap, max_w_pct, font_size, vw)
    aligned_text = _align_multiline_text(wrapped_text, align)

    dmode_raw = op.get("display_mode") or op.get("displayMode")
    start_dur = float(op.get("start_duration", op.get("startDuration", 3.0)))
    end_dur = float(op.get("end_duration", op.get("endDuration", 3.0)))

    st = float(op.get("startTime", op.get("start_time", op.get("start", 0.0))))
    et = float(op.get("endTime", op.get("end_time", op.get("end", 0.0))))
    duration_legacy = op.get("duration")

    if not dmode_raw:
        if st > 0 or et > 0:
            display_mode = "custom"
        else:
            display_mode = "always"
    else:
        display_mode = str(dmode_raw)

    media_dur = ctx.duration_seconds if ctx and ctx.duration_seconds else 0.0

    enable_expr = None

    if display_mode == "start":
        if start_dur > 0:
            enable_expr = f"between(t\\,0\\,{start_dur})"
    elif display_mode == "end":
        if end_dur > 0:
            end_st = max(0.0, media_dur - end_dur)
            enable_expr = f"gte(t\\,{end_st})"
    elif display_mode == "both":
        conds = []
        if start_dur > 0:
            conds.append(f"between(t\\,0\\,{start_dur})")
        if end_dur > 0:
            end_st = max(0.0, media_dur - end_dur)
            conds.append(f"gte(t\\,{end_st})")
        if conds:
            enable_expr = "+".join(conds)
    elif display_mode == "custom":
        if et > st and st >= 0:
            enable_expr = f"between(t\\,{st}\\,{et})"
        elif duration_legacy is not None and float(duration_legacy) > 0:
            dur_val = float(duration_legacy)
            enable_expr = f"between(t\\,{st}\\,{st + dur_val})"
        elif st > 0:
            enable_expr = f"gte(t\\,{st})"
    elif display_mode == "always":
        enable_expr = None
    else:
        if et > st and st >= 0:
            enable_expr = f"between(t\\,{st}\\,{et})"
        elif st > 0:
            enable_expr = f"gte(t\\,{st})"

    # Handle Emojis via PIL PNG Overlay
    opacity = float(op.get("opacity", 1.0))
    if opacity > 1.0:
        opacity = opacity / 100.0
    opacity = max(0.0, min(1.0, opacity))

    cw = ctx.video_width or 720
    ch = ctx.video_height or 1280
    png_path = _render_emoji_text_overlay_png(
        text=wrapped_text,
        font_family=font_family,
        font_size=font_size,
        color_name=color,
        enable_outline=enable_outline,
        outline_color_name=outline_color,
        outline_thickness=outline_thickness,
        enable_shadow=enable_shadow,
        shadow_color_name=shadow_color,
        shadow_blur=shadow_blur,
        align=align,
        pos_x=pos_x,
        pos_y=pos_y,
        canvas_w=cw,
        canvas_h=ch,
        opacity=opacity,
    )
    if png_path:
        overlay_filter = f"overlay=0:0" + (f":enable='{enable_expr}'" if enable_expr else "")
        return OperationResult(video_filters=[overlay_filter], extra_inputs=[png_path])

    # Standard FFmpeg drawtext fallback for plain text
    font_file = resolve_font_file(font_family, font_weight)
    x_expr, y_expr = _position_to_xy(pos_x, pos_y, op.get("position", ""))
    escaped_text = escape_for_filter(aligned_text)

    font_color_str = f"{color}@{opacity:.2f}" if opacity < 1.0 else color

    parts = [
        f"text='{escaped_text}'",
        "expansion=none",
        f"x={x_expr}",
        f"y={y_expr}",
        f"fontsize={font_size}",
        f"fontcolor={font_color_str}",
    ]

    if font_file:
        escaped_font_file = to_forward_slashes(font_file).replace(":", "\\:")
        parts.append(f"fontfile='{escaped_font_file}'")

    if enable_outline and outline_thickness > 0:
        outline_color_str = f"{outline_color}@{opacity:.2f}" if opacity < 1.0 else outline_color
        parts.append(f"bordercolor={outline_color_str}")
        parts.append(f"borderw={outline_thickness}")

    if enable_shadow and shadow_blur > 0:
        shadow_color_str = f"{shadow_color}@{opacity:.2f}" if opacity < 1.0 else shadow_color
        parts.append(f"shadowcolor={shadow_color_str}")
        parts.append(f"shadowx={shadow_blur}")
        parts.append(f"shadowy={shadow_blur}")

    if enable_expr:
        parts.append(f"enable='{enable_expr}'")

    drawtext = "drawtext=" + ":".join(parts)
    return OperationResult(video_filters=[drawtext])


def _position_to_xy(pos_x: str, pos_y: str, position_legacy: str = "") -> tuple[str, str]:
    """Map X and Y position descriptors or legacy position string to FFmpeg expressions."""
    if position_legacy and not pos_x and not pos_y:
        legacy_map = {
            "top-left":     ("w*0.05", "h*0.05"),
            "top-right":    ("w-text_w-w*0.05", "h*0.05"),
            "center":       ("(w-text_w)/2", "(h-text_h)/2"),
            "bottom-left":  ("w*0.05", "h*0.95-text_h"),
            "bottom-right": ("w-text_w-w*0.05", "h*0.95-text_h"),
        }
        return legacy_map.get(position_legacy, ("(w-text_w)/2", "(h-text_h)/2"))

    # X mapping
    x_map = {
        "center": "(w-text_w)/2",
        "left (5%)": "w*0.05",
        "left": "w*0.05",
        "left 10%": "w*0.10",
        "left 20%": "w*0.20",
        "right (5%)": "w-text_w-w*0.05",
        "right": "w-text_w-w*0.05",
        "right 10%": "w-text_w-w*0.10",
        "right 20%": "w-text_w-w*0.20",
    }
    x_expr = x_map.get(str(pos_x).lower(), "(w-text_w)/2")

    # Y mapping
    y_map = {
        "top 10%": "h*0.10",
        "top 20%": "h*0.20",
        "top 5%": "h*0.05",
        "center": "(h-text_h)/2",
        "bottom 10%": "h*0.90-text_h",
        "bottom 20%": "h*0.80-text_h",
        "bottom 5%": "h*0.95-text_h",
    }
    y_expr = y_map.get(str(pos_y).lower(), "h*0.10")

    return x_expr, y_expr


def _wrap_text(text: str, auto_wrap: bool, max_width_pct: float, font_size: int, video_width: int | None) -> str:
    """Wrap text lines to fit within specified video width percentage."""
    if not auto_wrap or not text:
        return text

    v_width = video_width or 1920
    max_w_px = v_width * (max_width_pct / 100.0)
    # Estimate average character width based on proportional font size
    avg_char_w = font_size * 0.44
    max_chars_per_line = max(10, int(max_w_px / avg_char_w))

    wrapped_lines = []
    for line in text.splitlines():
        if line.strip():
            wrapped_lines.append(textwrap.fill(line, width=max_chars_per_line))
        else:
            wrapped_lines.append("")
    return "\n".join(wrapped_lines)


def _align_multiline_text(text: str, align: str) -> str:
    """Align individual multiline text lines relative to each other."""
    if not text or "\n" not in text:
        return text

    lines = text.splitlines()
    if len(lines) <= 1:
        return text

    max_len = max(len(line) for line in lines)
    aligned_lines = []

    for line in lines:
        if not line:
            aligned_lines.append(line)
            continue

        diff = max_len - len(line)
        if diff <= 0:
            aligned_lines.append(line)
        elif align == "Center":
            pad = diff // 2
            aligned_lines.append(" " * pad + line)
        elif align == "Right":
            aligned_lines.append(" " * diff + line)
        else:  # Left
            aligned_lines.append(line)

    return "\n".join(aligned_lines)



