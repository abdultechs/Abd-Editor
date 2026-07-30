"""
Video Merge & Compilation Operation.

Supports merging multiple video files/folders:
- Intro video clip (before primary video)
- Outro video clip (after primary video)
- Folder video compilation (concatenating all videos in a folder into 1 output)
- Resolution normalization (scale & pad to fit, match primary video)
"""

import os
from app.processing.operations.base import OperationResult, OperationContext

SUPPORTED_VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".m4v")
EXCLUDE_DIR_NAMES = {"output", "temp", "tmp", ".git", "__pycache__"}


def resolve_merge_videos(asset_path: str) -> list[str]:
    """Resolve video file paths from file or directory path, excluding output and temp dirs."""
    if not asset_path or not os.path.exists(asset_path):
        return []

    if os.path.isdir(asset_path):
        files = []
        for root, dirs, filenames in os.walk(asset_path):
            # Prune excluded subdirectories in-place
            dirs[:] = [d for d in dirs if d.lower() not in EXCLUDE_DIR_NAMES]
            for fn in filenames:
                if fn.lower().endswith(SUPPORTED_VIDEO_EXTS):
                    if ".processing.tmp" not in fn.lower() and not fn.lower().endswith(".tmp"):
                        files.append(os.path.join(root, fn))
        files.sort()
        return files
    elif os.path.isfile(asset_path) and asset_path.lower().endswith(SUPPORTED_VIDEO_EXTS):
        return [asset_path]

    return []


def apply_merge(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op options:
      mode:            "intro_outro" | "folder_compilation"
      enable_intro:    bool
      intro_path:      str path to intro video
      enable_outro:    bool
      outro_path:      str path to outro video
      resolution_mode: "pad" | "crop" | "match_primary" (default "pad")
    """
    mode = str(op.get("mode", "intro_outro"))
    extra_inputs: list[str] = []

    if mode == "folder_compilation":
        compilation_videos = op.get("compilation_videos") or []
        if isinstance(compilation_videos, list) and len(compilation_videos) > 0:
            for path in compilation_videos:
                if os.path.exists(path) and path.lower().endswith(SUPPORTED_VIDEO_EXTS):
                    extra_inputs.append(path)
        else:
            # Fallback to assetPath, intro_path, or folder_path if compilation_videos not explicitly set in script
            asset_path = str(op.get("assetPath") or op.get("intro_path") or op.get("folder_path") or "")
            if asset_path and os.path.exists(asset_path):
                extra_inputs.extend(resolve_merge_videos(asset_path))
            elif ctx and hasattr(ctx, "input_path") and ctx.input_path and os.path.exists(ctx.input_path):
                extra_inputs.extend(resolve_merge_videos(os.path.dirname(ctx.input_path)))
    else:
        # Intro / Outro Mode
        enable_intro = bool(op.get("enable_intro", op.get("enableIntro", False)))
        intro_path = str(op.get("intro_path") or op.get("introPath") or op.get("assetPath") or "")

        enable_outro = bool(op.get("enable_outro", op.get("enableOutro", False)))
        outro_path = str(op.get("outro_path") or op.get("outroPath") or "")

        if enable_intro and intro_path:
            extra_inputs.extend(resolve_merge_videos(intro_path))

        if enable_outro and outro_path:
            extra_inputs.extend(resolve_merge_videos(outro_path))

    return OperationResult(
        extra_inputs=extra_inputs,
    )
