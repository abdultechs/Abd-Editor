"""
FFmpeg plan builder.

Ported directly from plan.ts — builds execution plan, filter graph chains,
and argument lists for FFmpeg execution.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from app.processing.probe import MediaInfo
from app.processing.operations.base import OperationContext, OperationResult
from app.processing.operations.trim import apply_trim
from app.processing.operations.flip import apply_flip
from app.processing.operations.speed import apply_speed
from app.processing.operations.audio import apply_audio
from app.processing.operations.text_overlay import apply_text
from app.processing.operations.fade import apply_fade
from app.processing.operations.merge import apply_merge, resolve_merge_videos
from app.processing.operations.zoom import apply_zoom
from app.processing.operations.border import apply_border
from app.processing.operations.image_overlay import apply_image_overlay

MERGE_VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".m4v")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


@dataclass
class FfmpegPlan:
    input_path: str
    output_path: str
    temp_output_path: str
    command: str
    args: list[str]
    total_duration: float = 0.0
    extra_inputs: list[str] = field(default_factory=list)
    temp_files_to_clean: list[str] = field(default_factory=list)
    disable_audio: bool = False


def _quote(val: str) -> str:
    escaped = val.replace('"', '\\"')
    return f'"{escaped}"'


def build_ffmpeg_plan(
    input_path: str,
    output_path: str,
    script: Optional[dict],
    probe: MediaInfo,
) -> FfmpegPlan:
    """
    Build FfmpegPlan from script operations and probe metadata.
    """
    import json

    script_obj = {}
    if script:
        if "script_json" in script and isinstance(script["script_json"], str):
            try:
                script_obj = json.loads(script["script_json"])
            except Exception:
                script_obj = script
        else:
            script_obj = script

    operations = script_obj.get("operations", [])
    keep_original = script_obj.get("keepOriginal", script_obj.get("keep_original", True))

    merge_op = next((op for op in operations if op.get("type") == "merge"), None)
    total_duration = probe.duration_seconds

    if merge_op:
        mode = str(merge_op.get("mode", "intro_outro"))
        comp_vids = []
        if mode == "folder_compilation":
            compilation_videos = merge_op.get("compilation_videos") or []
            if isinstance(compilation_videos, list) and len(compilation_videos) > 0:
                comp_vids = compilation_videos
            else:
                asset_path = str(merge_op.get("assetPath") or merge_op.get("intro_path") or merge_op.get("folder_path") or "")
                if asset_path and os.path.exists(asset_path):
                    comp_vids = resolve_merge_videos(asset_path)
                elif input_path and os.path.exists(input_path):
                    comp_vids = resolve_merge_videos(os.path.dirname(input_path))
        else:
            enable_intro = bool(merge_op.get("enable_intro", merge_op.get("enableIntro", False)))
            intro_path = str(merge_op.get("intro_path") or merge_op.get("introPath") or "")
            enable_outro = bool(merge_op.get("enable_outro", merge_op.get("enableOutro", False)))
            outro_path = str(merge_op.get("outro_path") or merge_op.get("outroPath") or "")

            if enable_intro and intro_path:
                comp_vids.extend(resolve_merge_videos(intro_path))
            if enable_outro and outro_path:
                comp_vids.extend(resolve_merge_videos(outro_path))

        norm_input = os.path.normpath(input_path).lower()
        from app.processing.probe import probe_media
        for v in comp_vids:
            if os.path.exists(v) and os.path.normpath(v).lower() != norm_input:
                try:
                    p = probe_media(v)
                    total_duration += p.duration_seconds
                except Exception:
                    pass

    ctx = OperationContext(
        duration_seconds=total_duration,
        video_width=probe.video_width,
        video_height=probe.video_height,
        input_path=input_path,
    )

    all_video_filters: list[str] = []
    all_audio_filters: list[str] = []
    extra_inputs: list[str] = []
    disable_audio = False

    for op in operations:
        op_type = op.get("type")
        res = OperationResult()
        if op_type == "trim":
            res = apply_trim(op, ctx)
        elif op_type == "flip":
            res = apply_flip(op, ctx)
        elif op_type == "speed":
            res = apply_speed(op, ctx)
        elif op_type == "audio":
            res = apply_audio(op, ctx)
        elif op_type == "text":
            res = apply_text(op, ctx)
        elif op_type == "fade":
            res = apply_fade(op, ctx)
        elif op_type == "merge":
            res = apply_merge(op, ctx)
        elif op_type == "zoom":
            res = apply_zoom(op, ctx)
        elif op_type == "border":
            res = apply_border(op, ctx)
        elif op_type in ("image_overlay", "image"):
            res = apply_image_overlay(op, ctx)

        all_video_filters.extend(res.video_filters)
        all_audio_filters.extend(res.audio_filters)
        extra_inputs.extend(res.extra_inputs)

    audio_op = next((op for op in operations if op.get("type") == "audio"), None)
    audio_mode = audio_op.get("mode") if audio_op else None
    merge_op = next((op for op in operations if op.get("type") == "merge"), None)

    if not keep_original and not (audio_op and audio_mode in ("replace-audio", "background-music")):
        disable_audio = True

    ext = os.path.splitext(output_path)[1]
    temp_output_path = f"{output_path}.processing.tmp{ext}"

    merge_video_inputs = [x for x in extra_inputs if x.lower().endswith(MERGE_VIDEO_EXTS)]
    image_inputs = [x for x in extra_inputs if x.lower().endswith(IMAGE_EXTS)]

    # If folder_compilation, exclude input_path from extra merge_video_inputs to avoid duplicate -i flag
    if merge_op and str(merge_op.get("mode", "intro_outro")) == "folder_compilation":
        norm_input = os.path.normpath(input_path).lower()
        merge_video_inputs = [x for x in merge_video_inputs if os.path.normpath(x).lower() != norm_input]

    audio_inputs = [x for x in extra_inputs if x not in merge_video_inputs and x not in image_inputs and os.path.normpath(x).lower() != os.path.normpath(input_path).lower()]

    ordered_extra_inputs = merge_video_inputs + image_inputs + audio_inputs

    args: list[str] = ["-y", "-progress", "pipe:1", "-i", input_path]

    for extra in ordered_extra_inputs:
        args.extend(["-i", extra])

    filter_chains: list[str] = []
    has_video_filters = len(all_video_filters) > 0
    has_audio_filters = len(all_audio_filters) > 0

    video_base_tag = "[0:v]"
    audio_base_tag = "[0:a]"

    # If Video Merge operation is present with extra video inputs, concatenate video streams
    if merge_op and (merge_video_inputs or str(merge_op.get("mode", "intro_outro")) == "folder_compilation"):
        w = ctx.video_width or 1920
        h = ctx.video_height or 1080
        mode = str(merge_op.get("mode", "intro_outro"))

        if mode == "folder_compilation":
            # Primary video is 0, extra compilation videos are 1..M
            seq_indices = [0] + list(range(1, 1 + len(merge_video_inputs)))
        else:
            # Intro / Outro Mode
            enable_intro = bool(merge_op.get("enable_intro", merge_op.get("enableIntro", False)))
            intro_path = str(merge_op.get("intro_path") or merge_op.get("introPath") or "")
            intro_count = len(resolve_merge_videos(intro_path)) if enable_intro else 0

            enable_outro = bool(merge_op.get("enable_outro", merge_op.get("enableOutro", False)))
            outro_path = str(merge_op.get("outro_path") or merge_op.get("outroPath") or "")
            outro_count = len(resolve_merge_videos(outro_path)) if enable_outro else 0

            intro_indices = list(range(1, 1 + intro_count))
            outro_indices = list(range(1 + intro_count, 1 + intro_count + outro_count))
            seq_indices = intro_indices + [0] + outro_indices

        for idx in seq_indices:
            filter_chains.append(
                f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v_scale_{idx}]"
            )

        if not disable_audio and keep_original:
            concat_pairs = "".join(f"[v_scale_{idx}][{idx}:a]" for idx in seq_indices)
            filter_chains.append(
                f"{concat_pairs}concat=n={len(seq_indices)}:v=1:a=1[v_concat][a_concat]"
            )
            video_base_tag = "[v_concat]"
            audio_base_tag = "[a_concat]"
        else:
            concat_v_sources = "".join(f"[v_scale_{idx}]" for idx in seq_indices)
            filter_chains.append(f"{concat_v_sources}concat=n={len(seq_indices)}:v=1:a=0[v_concat]")
            video_base_tag = "[v_concat]"

    if has_video_filters:
        std_video_filters = [f for f in all_video_filters if not f.startswith("overlay=")]
        overlay_video_filters = [f for f in all_video_filters if f.startswith("overlay=")]

        img_offset = 1 + len(merge_video_inputs)

        img_ops = [op for op in operations if op.get("type") in ("image_overlay", "image")]
        if std_video_filters and overlay_video_filters:
            std_str = ",".join(std_video_filters)
            filter_chains.append(f"{video_base_tag}{std_str}[v_std]")
            curr_in = "[v_std]"
            for idx, ov in enumerate(overlay_video_filters, start=0):
                img_idx = img_offset + idx
                extra_file = image_inputs[idx] if idx < len(image_inputs) else ""
                is_full_canvas = ov == "overlay=0:0" or "emoji_overlay" in extra_file.lower() or "text_overlay" in extra_file.lower()

                prep_tag = f"[img_prep_{idx}]"
                if is_full_canvas:
                    filter_chains.append(f"[{img_idx}:v]setsar=1,format=rgba{prep_tag}")
                else:
                    img_op = img_ops[idx] if idx < len(img_ops) else {}
                    scale_pct = int(img_op.get("scale_pct", img_op.get("scale", 30)))
                    opacity = float(img_op.get("opacity", 1.0))
                    if opacity > 1.0: opacity /= 100.0
                    opacity = max(0.0, min(1.0, opacity))

                    vw = ctx.video_width or 1920
                    target_w = max(10, int(vw * (scale_pct / 100.0)))
                    filter_chains.append(f"[{img_idx}:v]scale={target_w}:-1:force_original_aspect_ratio=decrease,setsar=1,format=rgba,colorchannelmixer=aa={opacity:.2f}{prep_tag}")

                out_label = "[vout]" if idx == len(overlay_video_filters) - 1 else f"[v_ov{idx+1}]"
                filter_chains.append(f"{curr_in}{prep_tag}{ov}{out_label}")
                curr_in = f"[v_ov{idx+1}]"
        elif overlay_video_filters:
            curr_in = video_base_tag
            for idx, ov in enumerate(overlay_video_filters, start=0):
                img_idx = img_offset + idx
                extra_file = image_inputs[idx] if idx < len(image_inputs) else ""
                is_full_canvas = ov == "overlay=0:0" or "emoji_overlay" in extra_file.lower() or "text_overlay" in extra_file.lower()

                prep_tag = f"[img_prep_{idx}]"
                if is_full_canvas:
                    filter_chains.append(f"[{img_idx}:v]setsar=1,format=rgba{prep_tag}")
                else:
                    img_op = img_ops[idx] if idx < len(img_ops) else {}
                    scale_pct = int(img_op.get("scale_pct", img_op.get("scale", 30)))
                    opacity = float(img_op.get("opacity", 1.0))
                    if opacity > 1.0: opacity /= 100.0
                    opacity = max(0.0, min(1.0, opacity))

                    vw = ctx.video_width or 1920
                    target_w = max(10, int(vw * (scale_pct / 100.0)))
                    filter_chains.append(f"[{img_idx}:v]scale={target_w}:-1:force_original_aspect_ratio=decrease,setsar=1,format=rgba,colorchannelmixer=aa={opacity:.2f}{prep_tag}")

                out_label = "[vout]" if idx == len(overlay_video_filters) - 1 else f"[v_ov{idx+1}]"
                filter_chains.append(f"{curr_in}{prep_tag}{ov}{out_label}")
                curr_in = f"[v_ov{idx+1}]"
        else:
            std_str = ",".join(std_video_filters)
            filter_chains.append(f"{video_base_tag}{std_str}[vout]")
    elif video_base_tag != "[0:v]":
        filter_chains.append(f"{video_base_tag}null[vout]")

    if not disable_audio:
        if audio_mode in ("background-music", "replace-audio") and audio_inputs:
            audio_offset = len(merge_video_inputs) + len(image_inputs)
            asset_filter_str = ",".join(all_audio_filters) if has_audio_filters else "anull"

            if len(audio_inputs) > 1:
                concat_sources = "".join(f"[{i+1+audio_offset}:a]" for i in range(len(audio_inputs)))
                filter_chains.append(f"{concat_sources}concat=n={len(audio_inputs)}:v=0:a=1[a_merged]")
                filter_chains.append(f"[a_merged]{asset_filter_str}[a_asset]")
            else:
                filter_chains.append(f"[{1+audio_offset}:a]{asset_filter_str}[a_asset]")

            if audio_mode == "background-music" and keep_original:
                orig_vol = float(audio_op.get("original_volume", audio_op.get("originalVolume", 1.0)))
                filter_chains.append(f"{audio_base_tag}volume={orig_vol}[a_orig]")
                filter_chains.append("[a_orig][a_asset]amix=inputs=2:duration=first:dropout_transition=2[aout]")
            else:
                filter_chains.append("[a_asset]anull[aout]")

        elif keep_original:
            if has_audio_filters:
                audio_filter_str = ",".join(all_audio_filters)
                filter_chains.append(f"{audio_base_tag}{audio_filter_str}[aout]")
            elif audio_base_tag != "[0:a]":
                filter_chains.append(f"{audio_base_tag}anull[aout]")

    if filter_chains:
        args.extend(["-filter_complex", ";".join(filter_chains)])

    if has_video_filters or video_base_tag != "[0:v]":
        args.extend(["-map", "[vout]"])
    else:
        args.extend(["-map", "0:v:0"])

    has_audio_chain = any("[aout]" in chain for chain in filter_chains)

    if disable_audio:
        args.append("-an")
    elif has_audio_chain:
        args.extend(["-map", "[aout]"])
    elif keep_original and probe.has_audio:
        args.extend(["-map", "0:a?"])
    else:
        args.append("-an")

    args.extend(["-movflags", "+faststart", temp_output_path])

    command = f"ffmpeg {' '.join(_quote(a) for a in args)}"

    from app.utils.constants import TEMP_DIR
    temp_dir_norm = os.path.normpath(TEMP_DIR).lower()
    temp_files_to_clean = []
    for x in extra_inputs:
        x_norm = os.path.normpath(x).lower()
        if x_norm.startswith(temp_dir_norm) or "emoji_overlay" in os.path.basename(x_norm):
            temp_files_to_clean.append(x)

    return FfmpegPlan(
        input_path=input_path,
        output_path=output_path,
        temp_output_path=temp_output_path,
        command=command,
        args=args,
        total_duration=total_duration,
        extra_inputs=extra_inputs,
        temp_files_to_clean=temp_files_to_clean,
        disable_audio=disable_audio,
    )
