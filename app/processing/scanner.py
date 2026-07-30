"""
Video folder scanner utility.
Discovers valid video files in a folder recursively.
"""

import os
from app.utils.constants import ACCEPTED_VIDEO_EXTENSIONS


def scan_video_files(root_folder: str, exclude_folder: str | None = None) -> list[str]:
    """Walk root_folder recursively and return list of full paths to video files, excluding output folders."""
    results: list[str] = []
    if not os.path.exists(root_folder):
        return results

    norm_root = os.path.normpath(root_folder).lower()
    norm_exclude = os.path.normpath(exclude_folder).lower() if exclude_folder else None

    for root, dirs, files in os.walk(root_folder):
        norm_current = os.path.normpath(root).lower()

        # Exclude output folder and sub-output folders
        if norm_exclude and (norm_current == norm_exclude or norm_current.startswith(norm_exclude + os.sep)):
            dirs.clear()  # Don't descend into excluded output folder
            continue

        # Also skip any subfolder explicitly named 'output' inside the root
        dirs_to_remove = []
        for d in dirs:
            if d.lower() == "output" or (norm_exclude and os.path.normpath(os.path.join(root, d)).lower() == norm_exclude):
                dirs_to_remove.append(d)
        for d in dirs_to_remove:
            dirs.remove(d)

        for file in files:
            # Skip temp processing files
            if ".processing.tmp" in file.lower() or file.lower().endswith(".tmp"):
                continue
            ext = os.path.splitext(file)[1].lower()
            if ext in ACCEPTED_VIDEO_EXTENSIONS:
                results.append(os.path.join(root, file))

    return sorted(results)
