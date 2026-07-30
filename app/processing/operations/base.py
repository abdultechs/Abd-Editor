"""
Base class and result dataclass for all FFmpeg operation modules.

Each operation translates its settings into FFmpeg filter fragments.
The plan_builder assembles these into a single FFmpeg invocation.
"""

from dataclasses import dataclass, field


@dataclass
class OperationResult:
    """
    Filter fragments produced by one operation.

    video_filters: list of video filter strings  e.g. ["hflip", "trim=start=3"]
    audio_filters: list of audio filter strings  e.g. ["atrim=start=3", "asetpts=PTS-STARTPTS"]
    extra_inputs:  additional -i paths needed    e.g. ["/path/to/music.mp3"]
    disable_audio: True if audio should be removed entirely
    """
    video_filters: list[str] = field(default_factory=list)
    audio_filters: list[str] = field(default_factory=list)
    extra_inputs: list[str] = field(default_factory=list)
    disable_audio: bool = False


@dataclass
class OperationContext:
    """Metadata about the input video, available to all operations."""
    duration_seconds: float
    video_width: int | None
    video_height: int | None
    input_path: str = ""

