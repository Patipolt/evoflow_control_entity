"""
Utility functions for the EvoFlow control entity.

Project: EvoFlow Innosuisse
Author: Patipol Thanuphol, Scientific Researcher at ZHAW — thau @zhaw.ch | patipol.thanu@gmail.com
Created: April 2026
"""

from pathlib import Path
import sys

def resource_path(*relative_parts: str) -> Path:
    """
    Resolve a resource path that works in both development and PyInstaller bundles.

    - In a frozen build, PyInstaller unpacks data files under `_MEIPASS/controlEntity` because
      we add data with targets like `controlEntity/assets`.
    - In development, resources live next to this module inside the `controlEntity` package.

    The function accepts one or more path segments (or a single string that can include
    separators). If callers pass a path that is already prefixed with `controlEntity/`, the
    prefix is stripped to avoid duplicating the folder name.
    """

    # Flatten path parts and strip a leading "controlEntity" if present to avoid double nesting
    parts = []
    for part in relative_parts:
        if part:
            parts.extend(Path(part).parts)

    if parts and parts[0] == "controlEntity":
        parts = parts[1:]

    relative_path = Path(*parts)

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS) / "controlEntity"
    else:
        base_path = Path(__file__).resolve().parent

    return base_path / relative_path

def colored_text(text: str, color: str) -> str:
    """
    Colorize the given text in the given color.
    """
    colors = {
        'Red': [255, 0, 0],
        'Green': [0, 255, 0],
        'Blue': [0, 200, 255],
        'Yellow': [255, 255, 0],
        'Orange': [255, 150, 0],
        'Pink': [255, 0, 150],
        'Violet': [200, 100, 200],
        'Pale': [255, 235, 200],
        'reset': '\033[0m'
    }
    if color not in colors:
        raise ValueError(f"Color '{color}' is not supported.")
    return f"\033[38;2;{colors[color][0]};{colors[color][1]};" \
           f"{colors[color][2]}m{text}{colors['reset']}"

HEX_COLOR_LIST = ["0072BD",
                  "D95319",
                  "EDB120",
                  "7E2F8E",
                  "77AC30",
                  "4DBEEE",
                  "A2142F",
                  "0072BD",
                  "D95319",
                  "EDB120",
                  "7E2F8E",
                  "77AC30",
                  "4DBEEE",
                  "A2142F",
                  "0072BD",
                  "D95319",
                  "EDB120",
                  "7E2F8E",
                  "77AC30",
                  "4DBEEE"]