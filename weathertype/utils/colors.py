"""ANSI terminal color utilities for visualization rendering."""

import os
import re

# Check NO_COLOR convention (https://no-color.org/)
_COLORS_ON = os.environ.get("NO_COLOR") is None

# ANSI escape codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def colors_on() -> bool:
    """Return whether color output is currently enabled."""
    return _COLORS_ON


def colorize(char: str, color: str) -> str:
    if not _COLORS_ON:
        return char
    return f"{color}{char}{RESET}"


def red(c: str) -> str:
    return colorize(c, BRIGHT_RED)


def blue(c: str) -> str:
    return colorize(c, BRIGHT_BLUE)


def green(c: str) -> str:
    return colorize(c, BRIGHT_GREEN)


def yellow(c: str) -> str:
    return colorize(c, BRIGHT_YELLOW)


def cyan(c: str) -> str:
    return colorize(c, BRIGHT_CYAN)


def magenta(c: str) -> str:
    return colorize(c, BRIGHT_MAGENTA)


def dim(c: str) -> str:
    return colorize(c, DIM)


def bold(c: str) -> str:
    return colorize(c, BOLD)


def visible_char(cell: str) -> str:
    """Strip ANSI codes to get the raw visible character(s)."""
    return _ANSI_RE.sub("", cell)


# --- 256-color support for heatmaps ---

def colorize_256(char: str, color_index: int) -> str:
    """Colorize using 256-color ANSI foreground palette."""
    if not _COLORS_ON:
        return char
    return f"\033[38;5;{color_index}m{char}{RESET}"


def bg_colorize_256(char: str, fg_index: int, bg_index: int) -> str:
    """Colorize with both 256-color foreground and background."""
    if not _COLORS_ON:
        return char
    return f"\033[38;5;{fg_index};48;5;{bg_index}m{char}{RESET}"


def _lerp_color(t: float, colors: list) -> int:
    """Linearly interpolate through a list of 256-color indices."""
    t = max(0.0, min(1.0, t))
    if t >= 1.0:
        return colors[-1]
    pos = t * (len(colors) - 1)
    idx = int(pos)
    return colors[min(idx, len(colors) - 1)]


# Blue (21) -> Cyan (51) -> Green (46) -> Yellow (226) -> Red (196) -> Magenta (201)
_TEMP_GRADIENT = [21, 27, 33, 39, 45, 51, 50, 49, 48, 47, 46,
                  82, 118, 154, 190, 226, 220, 214, 208, 202, 196]

# Purple (53) -> Blue (27) -> Cyan (44) -> Green (34) -> Yellow (226)
_PRESSURE_GRADIENT = [53, 54, 55, 56, 57, 27, 33, 39, 44, 37, 34,
                      35, 71, 107, 143, 179, 215, 221, 226]

# NWS-style radar dBZ color scale
_RADAR_COLORS = {
    # (min_dbz, max_dbz): 256-color index
    5: 71,     # light green
    10: 72,
    15: 34,    # green
    20: 40,    # bright green
    25: 226,   # yellow
    30: 220,   # gold
    35: 214,   # orange
    40: 208,   # dark orange
    45: 202,   # red-orange
    50: 196,   # red
    55: 160,   # dark red
    60: 125,   # magenta
    65: 201,   # bright magenta
    70: 231,   # white
}


def temperature_color(value: float, v_min: float, v_max: float) -> int:
    """Map temperature to a 256-color index (blue=cold through red=hot)."""
    if v_max == v_min:
        return _TEMP_GRADIENT[len(_TEMP_GRADIENT) // 2]
    t = (value - v_min) / (v_max - v_min)
    return _lerp_color(t, _TEMP_GRADIENT)


def pressure_color(value: float, v_min: float, v_max: float) -> int:
    """Map pressure to a 256-color index (purple=low through yellow=high)."""
    if v_max == v_min:
        return _PRESSURE_GRADIENT[len(_PRESSURE_GRADIENT) // 2]
    t = (value - v_min) / (v_max - v_min)
    return _lerp_color(t, _PRESSURE_GRADIENT)


def dbz_color(dbz: float) -> int:
    """Map radar reflectivity (dBZ) to NWS-standard color."""
    for threshold in sorted(_RADAR_COLORS.keys()):
        if dbz < threshold:
            return _RADAR_COLORS.get(threshold - 5, 71)
    return 231  # white for extreme values
