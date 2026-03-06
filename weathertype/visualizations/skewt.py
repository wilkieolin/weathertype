"""Skew-T Log-P diagram visualization for the terminal."""

import math
from typing import List, Tuple, Optional

import numpy as np

from weathertype.utils.colors import red, blue, cyan, yellow, dim, bold, visible_char


# Standard pressure labels for y-axis
STANDARD_LEVELS = [1000, 925, 850, 700, 500, 400, 300, 250, 200, 150]


class SkewTPlotter:
    """Create combined Skew-T diagrams in the terminal."""

    def __init__(self, width: int = 72, height: int = 35):
        self.width = width
        self.height = height
        self.pressure_min = 100   # hPa (top)
        self.pressure_max = 1050  # hPa (bottom)
        self.temp_min = -80       # °C  (will be auto-scaled)
        self.temp_max = 50        # °C  (will be auto-scaled)

    # ------------------------------------------------------------------ #
    # coordinate transforms
    # ------------------------------------------------------------------ #

    def _y(self, pressure: float) -> float:
        """Map pressure (hPa) to a y-fraction (0 = top, 1 = bottom)."""
        log_p = math.log(pressure)
        log_min = math.log(self.pressure_min)
        log_max = math.log(self.pressure_max)
        return (log_p - log_min) / (log_max - log_min)

    def _x(self, temperature: float, pressure: float) -> float:
        """Map temperature to x-fraction with skew applied."""
        y_frac = self._y(pressure)
        # Scale the skew proportionally to the temperature range
        t_range = self.temp_max - self.temp_min
        skew = (t_range * 0.3) * (1.0 - y_frac)
        t_skewed = temperature + skew
        return (t_skewed - self.temp_min) / t_range

    def _to_grid(self, x_frac: float, y_frac: float) -> Tuple[int, int]:
        """Convert fractions to grid column, row."""
        margin_left = 6   # room for pressure labels
        plot_w = self.width - margin_left - 1
        col = margin_left + int(x_frac * (plot_w - 1))
        row = int(y_frac * (self.height - 2))  # leave bottom row for axis
        return (max(margin_left, min(self.width - 2, col)),
                max(0, min(self.height - 2, row)))

    # ------------------------------------------------------------------ #
    # rendering
    # ------------------------------------------------------------------ #

    def plot_full_skewt(
        self,
        temperatures: List[float],
        dew_points: List[float],
        pressures: List[float],
    ) -> str:
        if len(temperatures) != len(pressures):
            raise ValueError("temperatures and pressures must have same length")

        # --- auto-scale x-axis to data range ---
        all_temps = temperatures + dew_points
        data_min = min(all_temps)
        data_max = max(all_temps)
        self.temp_min = math.floor((data_min - 15) / 10) * 10
        self.temp_max = math.ceil((data_max + 15) / 10) * 10
        if self.temp_max - self.temp_min < 40:
            mid = (self.temp_max + self.temp_min) / 2
            self.temp_min = mid - 20
            self.temp_max = mid + 20

        margin_left = 6
        plot_w = self.width - margin_left - 1

        # blank grid
        grid = [[' '] * self.width for _ in range(self.height)]

        # y-axis: pressure labels + ticks
        for p in STANDARD_LEVELS:
            if self.pressure_min <= p <= self.pressure_max:
                _, row = self._to_grid(0, self._y(p))
                label = f"{p:>4d} "
                for i, ch in enumerate(label):
                    if i < margin_left:
                        grid[row][i] = cyan(ch)
                grid[row][margin_left] = dim('+')
                for c in range(margin_left + 1, self.width):
                    if visible_char(grid[row][c]) == ' ':
                        grid[row][c] = dim('·')

        # x-axis: temperature labels at bottom
        bottom = self.height - 1
        for t in range(int(self.temp_min), int(self.temp_max) + 1, 10):
            x_frac = self._x(t, max(pressures))
            col = margin_left + int(x_frac * (plot_w - 1))
            label = f"{t}"
            start = max(margin_left, col - len(label) // 2)
            for i, ch in enumerate(label):
                if start + i < self.width:
                    grid[bottom][start + i] = yellow(ch)

        # ---- isotherms (skewed vertical reference lines, every 20°) ----
        for t_iso in range(int(self.temp_min), int(self.temp_max) + 1, 20):
            for p in np.linspace(self.pressure_max, self.pressure_min, 80):
                xf = self._x(t_iso, p)
                yf = self._y(p)
                col, row = self._to_grid(xf, yf)
                if margin_left < col < self.width - 1 and 0 <= row < self.height - 1:
                    vc = visible_char(grid[row][col])
                    if vc in (' ', '·'):
                        grid[row][col] = dim('│')

        # ---- plot dry adiabats (light background reference, every 20°) ----
        for theta_c in range(-20, 60, 20):
            for p in np.linspace(self.pressure_max, self.pressure_min, 60):
                t = (theta_c + 273.15) * (p / 1000.0) ** 0.286 - 273.15
                xf = self._x(t, p)
                yf = self._y(p)
                col, row = self._to_grid(xf, yf)
                if margin_left < col < self.width - 1 and 0 <= row < self.height - 1:
                    vc = visible_char(grid[row][col])
                    if vc in (' ', '·', '│'):
                        grid[row][col] = dim('.')

        # ---- helper to interpolate a curve onto the grid ----
        def _plot_curve(values, presses, char):
            sorted_data = sorted(zip(presses, values), key=lambda x: x[0], reverse=True)
            prev_col, prev_row = None, None
            for p, v in sorted_data:
                xf = self._x(v, p)
                yf = self._y(p)
                col, row = self._to_grid(xf, yf)
                if prev_col is not None:
                    steps = max(abs(col - prev_col), abs(row - prev_row), 1)
                    for s in range(1, steps + 1):
                        ic = prev_col + int((col - prev_col) * s / steps)
                        ir = prev_row + int((row - prev_row) * s / steps)
                        if margin_left < ic < self.width - 1 and 0 <= ir < self.height - 1:
                            grid[ir][ic] = char
                else:
                    if margin_left < col < self.width - 1 and 0 <= row < self.height - 1:
                        grid[row][col] = char
                prev_col, prev_row = col, row

        # dew point first (so temperature overdraws on overlap)
        _plot_curve(dew_points, pressures, blue('○'))
        _plot_curve(temperatures, pressures, red('●'))

        # assemble output
        lines = []
        lines.append("=" * self.width)
        lines.append(bold("LOG-P SKEW-T DIAGRAM").center(self.width + 8))  # +8 for ANSI codes in centering
        lines.append("=" * self.width)
        for row in grid:
            lines.append(''.join(row))
        lines.append(f"  {red('●')} Temperature   {blue('○')} Dew Point   {dim('.')} Dry Adiabat   {dim('│')} Isotherm")
        lines.append(f"  Pressure: {max(pressures):.0f} – {min(pressures):.0f} hPa")

        return '\n'.join(lines)


def create_skewt_diagram(
    temperatures: List[float],
    dew_points: List[float],
    pressures: List[float],
) -> str:
    plotter = SkewTPlotter()
    return plotter.plot_full_skewt(temperatures, dew_points, pressures)
