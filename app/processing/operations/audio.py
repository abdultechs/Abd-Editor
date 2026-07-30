"""
Audio operation.

Modes:
  keep-original    — pass original audio with volume adjustment
  remove           — strip audio (-an)
  replace-audio    — replace audio with asset file (single file, random from folder, or merged folder)
  background-music — mix background audio asset with original video audio
"""

import os
import random
from app.processing.operations.base import OperationResult, OperationContext


def _resolve_audio_assets(asset_path: str, source_type: str = "file", folder_mode: str = "random") -> list[str]:
    """Resolve audio file paths from single file or folder (shuffling all folder tracks into a playlist)."""
    if not asset_path:
        return []

    audio_exts = {".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac"}

    target_dir = asset_path if os.path.isdir(asset_path) else os.path.dirname(asset_path)

    if target_dir and os.path.isdir(target_dir):
        files = [
            os.path.join(target_dir, f)
            for f in sorted(os.listdir(target_dir))
            if os.path.splitext(f)[1].lower() in audio_exts
        ]
        if files:
            # Only restrict to a single file if explicitly requested via folder_mode == 'single' with exact file
            if source_type == "file" and folder_mode == "single" and os.path.isfile(asset_path):
                return [asset_path]

            # Return a randomized playlist sequence of all songs in the folder
            shuffled_files = list(files)
            random.shuffle(shuffled_files)
            return shuffled_files

    if os.path.isfile(asset_path):
        return [asset_path]

    return [asset_path]


def apply_audio(op: dict, ctx: OperationContext) -> OperationResult:
    """
    op keys:
      mode:              "keep-original" | "remove" | "replace-audio" | "background-music"
      source_type:       "file" | "folder"
      folder_mode:       "random" | "merge"
      asset_path / assetPath: str
      original_volume:   float (default 1.0)
      volume / background_volume / bgVolume: float (default 0.35 for bg, 1.0 for replace)
      use_segment:       bool (default False)
      segment_start:     float (default 0.0)
      segment_end:       float (default 0.0)
    """
    mode = op.get("mode", "keep-original")

    if mode == "remove":
        return OperationResult(disable_audio=True)

    original_vol = float(op.get("original_volume", op.get("originalVolume", 1.0)))

    if mode == "keep-original":
        audio_filters: list[str] = []
        if original_vol != 1.0:
            audio_filters.append(f"volume={original_vol}")
        return OperationResult(audio_filters=audio_filters)

    # replace-audio or background-music
    asset_path = op.get("assetPath") or op.get("asset_path", "")
    source_type = op.get("source_type") or op.get("sourceType", "file")
    folder_mode = op.get("folder_mode") or op.get("folderMode", "random")

    if not asset_path:
        raise ValueError(f"Audio operation '{mode}' requires an asset file or folder path.")

    resolved_inputs = _resolve_audio_assets(asset_path, source_type, folder_mode)

    bg_vol = float(
        op.get("background_volume")
        or op.get("bgVolume")
        or op.get("volume", 0.35 if mode == "background-music" else 1.0)
    )

    use_segment = bool(op.get("use_segment", op.get("useSegment", False)))
    seg_start = float(op.get("segment_start", op.get("segmentStart", 0.0)))
    seg_end = float(op.get("segment_end", op.get("segmentEnd", 0.0)))

    asset_filters: list[str] = []

    # 1. Custom segment trimming if requested
    if use_segment and (seg_start > 0 or seg_end > 0):
        if seg_end > seg_start:
            asset_filters.append(f"atrim=start={seg_start}:end={seg_end}")
        elif seg_start > 0:
            asset_filters.append(f"atrim=start={seg_start}")
        asset_filters.append("asetpts=PTS-STARTPTS")

    # 2. Volume scaling
    if bg_vol != 1.0:
        asset_filters.append(f"volume={bg_vol}")

    # 3. Loop audio asset continuously and trim to match exact video duration
    if not use_segment and ctx and ctx.duration_seconds and ctx.duration_seconds > 0:
        asset_filters.append("aloop=loop=-1:size=2e9")
        asset_filters.append(f"atrim=0:{ctx.duration_seconds}")
        asset_filters.append("asetpts=PTS-STARTPTS")

    return OperationResult(
        audio_filters=asset_filters,
        extra_inputs=resolved_inputs,
    )
