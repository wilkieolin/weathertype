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
