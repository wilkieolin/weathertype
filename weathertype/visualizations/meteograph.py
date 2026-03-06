"""Meteograph (vertical profile) visualization for the terminal."""

import math
from typing import List, Optional

from weathertype.utils.colors import red, blue, green, cyan, yellow, dim, bold, visible_char


STANDARD_LEVELS = [1000, 925, 850, 700, 500, 400, 300, 250, 200, 150]


class MeteographPlotter:
    """Create vertical-profile meteographs in the terminal."""

    def __init__(self, width: int = 72, height: int = 28):
        self.width = width
        self.height = height

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    def _y_frac(self, pressure: float, p_min: float, p_max: float) -> float:
        """Log-pressure fraction (0 = top, 1 = bottom)."""
        return (math.log(pressure) - math.log(p_min)) / (math.log(p_max) - math.log(p_min))

    def _render_profile(
        self,
        pressures: List[float],
        series: List[tuple],   # list of (values, char, label)
        title: str,
        x_label: str,
    ) -> str:
        margin = 6  # left margin for pressure labels
        plot_w = self.width - margin - 1

        p_min = min(pressures)
        p_max = max(pressures)

        # Combined value range across all series
        all_vals = []
        for vals, _, _ in series:
            all_vals.extend(v for v in vals if v is not None)
        v_min = min(all_vals)
        v_max = max(all_vals)
        if v_max == v_min:
            v_max = v_min + 1

        grid = [[' '] * self.width for _ in range(self.height)]

        # pressure labels (cyan) + guides (dimmed)
        for p in STANDARD_LEVELS:
            if p_min <= p <= p_max:
                yf = self._y_frac(p, p_min, p_max)
                row = int(yf * (self.height - 2))
                row = max(0, min(self.height - 2, row))
                label = f"{p:>4d} "
                for i, ch in enumerate(label):
                    if i < margin:
                        grid[row][i] = cyan(ch)
                for c in range(margin, self.width):
                    if visible_char(grid[row][c]) == ' ':
                        grid[row][c] = dim('·')

        # Plot each series
        for vals, char, _ in series:
            sorted_data = sorted(
                zip(pressures, vals), key=lambda x: x[0], reverse=True
            )
            prev_col, prev_row = None, None
            for p, v in sorted_data:
                if v is None:
                    prev_col, prev_row = None, None
                    continue
                yf = self._y_frac(p, p_min, p_max)
                row = int(yf * (self.height - 2))
                row = max(0, min(self.height - 2, row))
                xf = (v - v_min) / (v_max - v_min)
                col = margin + int(xf * (plot_w - 1))
                col = max(margin, min(self.width - 2, col))

                # interpolate line between points
                if prev_col is not None:
                    steps = max(abs(col - prev_col), abs(row - prev_row), 1)
                    for s in range(1, steps):
                        ic = prev_col + int((col - prev_col) * s / steps)
                        ir = prev_row + int((row - prev_row) * s / steps)
                        if margin < ic < self.width - 1 and 0 <= ir < self.height - 1:
                            vc = visible_char(grid[ir][ic])
                            if vc in (' ', '·'):
                                grid[ir][ic] = char
                if margin <= col < self.width and 0 <= row < self.height - 1:
                    grid[row][col] = char
                prev_col, prev_row = col, row

        # x-axis labels (yellow) at bottom
        bottom = self.height - 1
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            val = v_min + frac * (v_max - v_min)
            col = margin + int(frac * (plot_w - 1))
            label = f"{val:.0f}"
            start = max(margin, col - len(label) // 2)
            for i, ch in enumerate(label):
                if start + i < self.width:
                    grid[bottom][start + i] = yellow(ch)

        lines = []
        lines.append(bold(title))
        lines.append("-" * self.width)
        for row in grid:
            lines.append(''.join(row))
        legend = "  ".join(f"{char} {lbl}" for _, char, lbl in series)
        lines.append(f"  {legend}   ({x_label})")
        return '\n'.join(lines)

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #

    def plot_full_meteograph(
        self,
        temperatures: List[float],
        dew_points: List[float],
        wind_speeds: List[float],
        pressures: List[float],
    ) -> str:
        lines = []
        lines.append("=" * self.width)
        lines.append(bold("METEOGRAPH (Vertical Profiles)").center(self.width + 8))
        lines.append("=" * self.width)
        lines.append("")

        # Temperature + Dew Point on one chart (colored chars)
        lines.append(self._render_profile(
            pressures,
            [(temperatures, red('●'), 'Temp'), (dew_points, blue('○'), 'Dewpt')],
            "Temperature & Dew Point",
            "°C",
        ))
        lines.append("")

        # Wind speed (green)
        lines.append(self._render_profile(
            pressures,
            [(wind_speeds, green('▸'), 'Wind')],
            "Wind Speed",
            "km/h",
        ))

        return '\n'.join(lines)


def create_meteograph(
    temperatures: List[float],
    dew_points: List[float],
    wind_speeds: List[float],
    pressures: List[float],
) -> str:
    plotter = MeteographPlotter()
    return plotter.plot_full_meteograph(temperatures, dew_points, wind_speeds, pressures)
