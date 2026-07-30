"""
FFprobe wrapper.

Ported from src/ffmpeg/probe.ts — same logic, Python subprocess.
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from app.utils.ffmpeg_binary import resolve_ffprobe, resolve_ffmpeg


@dataclass
class MediaInfo:
    duration_seconds: float
    video_width: Optional[int]
    video_height: Optional[int]
    has_audio: bool
    has_video: bool

    def resolution_str(self) -> Optional[str]:
        if self.video_width and self.video_height:
            return f"{self.video_width}x{self.video_height}"
        return None


def probe_media(file_path: str) -> MediaInfo:
    """
    Run ffprobe (or ffmpeg fallback) on file_path and return MediaInfo.
    """
    binary = resolve_ffprobe()
    
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0

    if "ffprobe" in os.path.basename(binary).lower():
        args = [
            binary,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        try:
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
                creationflags=creation_flags,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ffprobe timed out on: {file_path}")
        except FileNotFoundError:
            raise RuntimeError("ffprobe binary not found.")

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout.decode(errors="replace"))
                streams = data.get("streams", [])
                fmt = data.get("format", {})
                video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
                has_audio = any(s.get("codec_type") == "audio" for s in streams)
                duration_seconds = float(fmt.get("duration", "0"))
                return MediaInfo(
                    duration_seconds=duration_seconds,
                    video_width=video_stream.get("width") if video_stream else None,
                    video_height=video_stream.get("height") if video_stream else None,
                    has_audio=has_audio,
                    has_video=video_stream is not None,
                )
            except Exception:
                pass

    # Fallback parsing ffmpeg -i stderr output
    ffmpeg_bin = resolve_ffmpeg()
    try:
        res = subprocess.run(
            [ffmpeg_bin, "-i", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            creationflags=creation_flags,
        )
        stderr_txt = res.stderr.decode(errors="replace")
        
        # Duration: 00:00:08.93, ...
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", stderr_txt)
        dur_sec = 0.0
        if dur_match:
            dur_sec = float(dur_match.group(1))*3600 + float(dur_match.group(2))*60 + float(dur_match.group(3))
            
        # Stream #0:0... Video: ... 1280x720 ...
        res_match = re.search(r"Video:.*?\b(\d{3,5})x(\d{3,5})\b", stderr_txt)
        w, h = None, None
        if res_match:
            w, h = int(res_match.group(1)), int(res_match.group(2))
            
        has_audio = "Audio:" in stderr_txt
        has_video = "Video:" in stderr_txt
        
        return MediaInfo(
            duration_seconds=dur_sec,
            video_width=w,
            video_height=h,
            has_audio=has_audio,
            has_video=has_video,
        )
    except Exception as exc:
        raise RuntimeError(f"Media probe failed for {file_path}: {exc}")

