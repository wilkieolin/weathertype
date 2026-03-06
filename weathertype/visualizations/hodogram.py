"""Hodogram visualization for the terminal."""

import math
from typing import List, Optional, Tuple

from weathertype.utils.units import kmh_to_ms, direction_to_components
from weathertype.utils.colors import (
    red, green, cyan, yellow, dim, bold, visible_char, colorize,
    BRIGHT_RED, BRIGHT_YELLOW, BRIGHT_GREEN, BRIGHT_CYAN, BRIGHT_BLUE,
)


def _altitude_color(p: float) -> str:
    """Return ANSI color code for a pressure level."""
    if p >= 850:
        return BRIGHT_RED
    if p >= 700:
        return BRIGHT_YELLOW
    if p >= 500:
        return BRIGHT_GREEN
    if p >= 300:
        return BRIGHT_CYAN
    return BRIGHT_BLUE


class HodogramPlotter:
    """Create wind hodograms in the terminal."""

    def __init__(self, size: int = 31):
        self.size = size | 1

    def plot_hodogram(
        self,
        wind_speeds: List[float],
        wind_directions: List[int],
        pressure_levels: Optional[List[float]] = None,
    ) -> str:
        if len(wind_speeds) != len(wind_directions):
            raise ValueError("Wind speeds and directions must have same length")

        levels = pressure_levels or [0.0] * len(wind_speeds)
        data = sorted(
            zip(levels, wind_speeds, wind_directions),
            key=lambda x: x[0], reverse=True,
        )

        uv_points = []
        for p, spd, dirn in data:
            u, v = direction_to_components(float(dirn), kmh_to_ms(spd))
            uv_points.append((u, v, p, spd, dirn))

        all_uv = [(abs(u), abs(v)) for u, v, *_ in uv_points]
        max_extent = max(max(a, b) for a, b in all_uv) if all_uv else 1.0
        max_extent = max(max_extent, 1.0)

        half = self.size // 2
        scale = (half - 1) / max_extent

        grid = [[' '] * self.size for _ in range(self.size)]
        cx, cy = half, half

        # Draw axes (dimmed)
        for i in range(self.size):
            grid[cy][i] = dim('·') if grid[cy][i] == ' ' else grid[cy][i]
            grid[i][cx] = dim('·') if grid[i][cx] == ' ' else grid[i][cx]
        grid[cy][cx] = dim('+')

        # Speed rings (dimmed)
        ring_interval = 10  # m/s
        for r_ms in range(ring_interval, int(max_extent) + ring_interval, ring_interval):
            r_px = int(r_ms * scale)
            for angle in range(0, 360, 3):
                rad = math.radians(angle)
                col = cx + int(r_px * math.cos(rad))
                row = cy - int(r_px * math.sin(rad))
                if 0 <= col < self.size and 0 <= row < self.size:
                    vc = visible_char(grid[row][col])
                    if vc in (' ', '·'):
                        grid[row][col] = dim('·')

        # Cardinal direction labels (colored)
        grid[0][cx] = cyan('N')
        grid[self.size - 1][cx] = red('S')
        grid[cy][0] = green('W')
        grid[cy][self.size - 1] = yellow('E')

        # Plot connected hodogram curve with altitude coloring
        prev_col, prev_row = None, None
        for i, (u, v, p, spd, dirn) in enumerate(uv_points):
            col = cx + int(u * scale)
            row = cy - int(v * scale)
            color = _altitude_color(p)

            if prev_col is not None:
                steps = max(abs(col - prev_col), abs(row - prev_row), 1)
                for s in range(1, steps):
                    ic = prev_col + int((col - prev_col) * s / steps)
                    ir = prev_row + int((row - prev_row) * s / steps)
                    if 0 <= ic < self.size and 0 <= ir < self.size:
                        vc = visible_char(grid[ir][ic])
                        if vc in (' ', '·'):
                            grid[ir][ic] = colorize('-', color)

            if 0 <= col < self.size and 0 <= row < self.size:
                grid[row][col] = colorize('*', color)

            prev_col, prev_row = col, row

        # Output
        lines = []
        lines.append("=" * self.size)
        lines.append(bold("HODOGRAM").center(self.size + 8))
        lines.append("=" * self.size)
        for row in grid:
            lines.append(''.join(row))

        # Legend
        lines.append("")
        lines.append(
            f"  {colorize('*', BRIGHT_RED)} Sfc-850  "
            f"{colorize('*', BRIGHT_YELLOW)} 850-700  "
            f"{colorize('*', BRIGHT_GREEN)} 700-500  "
            f"{colorize('*', BRIGHT_CYAN)} 500-300  "
            f"{colorize('*', BRIGHT_BLUE)} 300+"
        )
        lines.append(f"  Ring spacing: {ring_interval} m/s   Max: {max_extent:.0f} m/s")
        if pressure_levels:
            lines.append("")
            lines.append("  Level (hPa)  Speed (km/h)  Dir")
            for u, v, p, spd, dirn in uv_points:
                color = _altitude_color(p)
                lines.append(colorize(f"    {p:>7.0f}     {spd:>6.0f}       {dirn:03d}°", color))

        return '\n'.join(lines)


def create_hodogram(
    wind_speeds: List[float],
    wind_directions: List[int],
    pressure_levels: Optional[List[float]] = None,
) -> str:
    plotter = HodogramPlotter()
    return plotter.plot_hodogram(wind_speeds, wind_directions, pressure_levels)
