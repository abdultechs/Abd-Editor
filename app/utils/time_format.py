"""Time formatting utilities."""


def seconds_to_hms(seconds: float | None) -> str:
    """Convert float seconds to HH:MM:SS string."""
    if seconds is None or seconds < 0:
        return "--:--:--"
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


def ms_to_hms(milliseconds: int | None) -> str:
    """Convert milliseconds to HH:MM:SS string."""
    if milliseconds is None:
        return "--:--:--"
    return seconds_to_hms(milliseconds / 1000.0)


def hms_to_seconds(hms: str) -> float:
    """Parse HH:MM:SS or MM:SS string to float seconds."""
    parts = hms.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(parts[0])
    except (ValueError, IndexError):
        return 0.0
