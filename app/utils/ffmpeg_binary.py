"""
FFmpeg and FFprobe binary resolution.

Resolution order:
  1. Environment variables FFMPEG_PATH / FFPROBE_PATH
  2. imageio-ffmpeg bundled binary (auto-downloaded on first use)
  3. System PATH (shutil.which)

Raises RuntimeError if no binary can be found.
"""

import os
import shutil


def resolve_ffmpeg() -> str:
    """Return the absolute path to the ffmpeg binary."""
    env = os.environ.get("FFMPEG_PATH", "").strip()
    if env and os.path.isfile(env):
        return env

    try:
        import imageio_ffmpeg  # type: ignore
        binary = imageio_ffmpeg.get_ffmpeg_exe()
        if binary and os.path.isfile(binary):
            return binary
    except Exception:
        pass

    system = shutil.which("ffmpeg")
    if system:
        return system

    raise RuntimeError(
        "FFmpeg binary not found.\n"
        "Install FFmpeg and add it to PATH, or set the FFMPEG_PATH environment variable."
    )


def resolve_ffprobe() -> str:
    """Return the absolute path to the ffprobe binary, or fallback to ffmpeg binary if ffprobe is absent."""
    env = os.environ.get("FFPROBE_PATH", "").strip()
    if env and os.path.isfile(env):
        return env

    try:
        import imageio_ffmpeg  # type: ignore
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        candidate = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe.exe")
        if os.path.isfile(candidate):
            return candidate
        candidate2 = os.path.join(os.path.dirname(ffmpeg_exe), "ffprobe")
        if os.path.isfile(candidate2):
            return candidate2
    except Exception:
        pass

    system = shutil.which("ffprobe")
    if system:
        return system

    # Fallback to ffmpeg binary if ffprobe is absent
    try:
        ffmpeg = resolve_ffmpeg()
        return ffmpeg
    except Exception:
        pass

    raise RuntimeError(
        "FFmpeg/FFprobe binary not found.\n"
        "Install FFmpeg and add it to PATH."
    )



def escape_for_filter(value: str) -> str:
    """Escape a string for use inside an FFmpeg filter graph value."""
    return (
        value
        .replace("\r\n", "\n")
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def to_forward_slashes(path: str) -> str:
    """Convert backslashes to forward slashes (required by FFmpeg filter paths)."""
    return path.replace("\\", "/")


def resolve_default_font() -> str | None:
    """Return a font file path suitable for FFmpeg drawtext on Windows."""
    env = os.environ.get("FFMPEG_FONT_FILE", "").strip()
    if env and os.path.isfile(env):
        return env
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    fonts_dir = os.path.join(system_root, "Fonts")
    candidates = [
        os.path.join(fonts_dir, "arial.ttf"),
        os.path.join(fonts_dir, "segoeui.ttf"),
        os.path.join(fonts_dir, "calibri.ttf"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None
