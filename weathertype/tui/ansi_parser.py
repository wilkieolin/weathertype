"""Parse ANSI-colored plotter output into curses attributes."""

import curses
import re

_ANSI_RE = re.compile(r"\033\[([0-9;]*)m")

# SGR code -> (curses_color_constant, needs_bold)
# Standard colors (30-37) use base color, bright (90-96) add A_BOLD
_SGR_COLOR_MAP = {
    31: (curses.COLOR_RED, False),
    32: (curses.COLOR_GREEN, False),
    33: (curses.COLOR_YELLOW, False),
    34: (curses.COLOR_BLUE, False),
    35: (curses.COLOR_MAGENTA, False),
    36: (curses.COLOR_CYAN, False),
    37: (curses.COLOR_WHITE, False),
    91: (curses.COLOR_RED, True),
    92: (curses.COLOR_GREEN, True),
    93: (curses.COLOR_YELLOW, True),
    94: (curses.COLOR_BLUE, True),
    95: (curses.COLOR_MAGENTA, True),
    96: (curses.COLOR_CYAN, True),
}

# Maps SGR code -> curses color pair number (assigned during init)
_pair_map: dict[int, int] = {}
_next_pair: int = 1
_256_pair_cache: dict[tuple[int, int], int] = {}  # (fg, bg) -> pair_num


def init_color_pairs() -> None:
    """Initialize curses color pairs for all ANSI SGR codes used by plotters.

    Must be called once after curses.initscr() and curses.start_color().
    """
    global _next_pair
    curses.start_color()
    curses.use_default_colors()

    for sgr, (color, _bright) in _SGR_COLOR_MAP.items():
        curses.init_pair(_next_pair, color, -1)
        _pair_map[sgr] = _next_pair
        _next_pair += 1


def _get_256_pair(fg: int, bg: int = -1) -> int:
    """Get or create a curses color pair for 256-color fg/bg."""
    global _next_pair
    key = (fg, bg)
    if key in _256_pair_cache:
        return _256_pair_cache[key]

    max_pairs = curses.COLOR_PAIRS if hasattr(curses, "COLOR_PAIRS") else 256
    if _next_pair >= max_pairs:
        # Fall back to closest standard color
        return 0

    curses.init_pair(_next_pair, fg, bg)
    _256_pair_cache[key] = _next_pair
    _next_pair += 1
    return _256_pair_cache[key]


def _sgr_to_attr(codes: list[int]) -> int:
    """Convert a list of SGR parameter codes to a curses attribute bitmask."""
    attr = 0
    i = 0
    while i < len(codes):
        code = codes[i]
        if code == 0:
            attr = 0
        elif code == 1:
            attr |= curses.A_BOLD
        elif code == 2:
            attr |= curses.A_DIM
        elif code == 38 and i + 2 < len(codes) and codes[i + 1] == 5:
            # 256-color foreground: 38;5;N
            color_idx = codes[i + 2]
            # Check if we also have a background coming
            bg = -1
            if i + 5 < len(codes) and codes[i + 3] == 48 and codes[i + 4] == 5:
                bg = codes[i + 5]
                i += 3  # skip bg codes
            pair_num = _get_256_pair(color_idx, bg)
            if pair_num:
                attr |= curses.color_pair(pair_num)
            i += 2  # skip 5;N
        elif code == 48 and i + 2 < len(codes) and codes[i + 1] == 5:
            # 256-color background only: 48;5;N
            bg_idx = codes[i + 2]
            pair_num = _get_256_pair(7, bg_idx)  # white fg on colored bg
            if pair_num:
                attr |= curses.color_pair(pair_num)
            i += 2
        elif code in _pair_map:
            pair_num = _pair_map[code]
            attr |= curses.color_pair(pair_num)
            if code in _SGR_COLOR_MAP and _SGR_COLOR_MAP[code][1]:
                attr |= curses.A_BOLD
        i += 1
    return attr


def parse_ansi_line(line: str) -> list[tuple[str, int]]:
    """Parse a single line with ANSI codes into (character, curses_attr) tuples."""
    result: list[tuple[str, int]] = []
    current_attr = 0
    pos = 0

    for match in _ANSI_RE.finditer(line):
        # Emit visible characters before this escape sequence
        start = match.start()
        for ch in line[pos:start]:
            result.append((ch, current_attr))

        # Parse SGR parameters
        params_str = match.group(1)
        if params_str == "" or params_str == "0":
            current_attr = 0
        else:
            codes = [int(c) for c in params_str.split(";") if c]
            current_attr = _sgr_to_attr(codes)

        pos = match.end()

    # Emit remaining visible characters after last escape
    for ch in line[pos:]:
        result.append((ch, current_attr))

    return result


def parse_ansi_block(text: str) -> list[list[tuple[str, int]]]:
    """Parse a multi-line ANSI string into rows of (char, attr) tuples."""
    return [parse_ansi_line(line) for line in text.split("\n")]


def render_to_pad(pad, text: str, start_row: int = 0, start_col: int = 0) -> int:
    """Parse ANSI text and render into a curses pad.

    Returns the number of rows written.
    """
    rows = parse_ansi_block(text)
    pad_height, pad_width = pad.getmaxyx()

    for r, row in enumerate(rows):
        y = start_row + r
        if y >= pad_height:
            break
        for c, (ch, attr) in enumerate(row):
            x = start_col + c
            if x >= pad_width:
                break
            try:
                pad.addstr(y, x, ch, attr)
            except curses.error:
                # Bottom-right corner write raises error in curses; ignore
                pass

    return len(rows)
