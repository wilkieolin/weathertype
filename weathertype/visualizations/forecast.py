"""36-hour forecast time-series visualization for the terminal."""

import math
from typing import List, Optional

from weathertype.api.models import ForecastData
from weathertype.utils.colors import (
    red, blue, green, cyan, yellow, magenta, dim, bold, visible_char, colorize,
    BRIGHT_RED, BRIGHT_BLUE, BRIGHT_GREEN, BRIGHT_CYAN, BRIGHT_YELLOW, BRIGHT_MAGENTA,
    DIM, WHITE,
)


# WMO weather codes → short descriptions + precip type
_WMO_CODES = {
    0: ("Clear", ""),
    1: ("Mostly Clear", ""),
    2: ("Partly Cloudy", ""),
    3: ("Overcast", ""),
    45: ("Fog", ""),
    48: ("Rime Fog", ""),
    51: ("Lt Drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Hvy Drizzle", "rain"),
    56: ("Fzg Drizzle", "freezing"),
    57: ("Hvy Fzg Drzl", "freezing"),
    61: ("Lt Rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy Rain", "rain"),
    66: ("Fzg Rain", "freezing"),
    67: ("Hvy Fzg Rain", "freezing"),
    71: ("Lt Snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy Snow", "snow"),
    77: ("Snow Grains", "snow"),
    80: ("Lt Showers", "rain"),
    81: ("Showers", "rain"),
    82: ("Hvy Showers", "rain"),
    85: ("Lt Snow Shwr", "snow"),
    86: ("Hvy Snow Shwr", "snow"),
    95: ("Thunderstorm", "rain"),
    96: ("T-storm+Hail", "rain"),
    99: ("Hvy T-storm", "rain"),
}


def _precip_char(code: Optional[int]) -> str:
    """Return a colored character representing precipitation type."""
    if code is None:
        return " "
    _, ptype = _WMO_CODES.get(code, ("?", ""))
    if ptype == "rain":
        return blue("▌")
    if ptype == "snow":
        return cyan("▌")
    if ptype == "freezing":
        return magenta("▌")
    return " "


def _cloud_bar(low: Optional[int], mid: Optional[int], high: Optional[int]) -> str:
    """Return a 3-char cloud layer representation."""
    def _shade(pct: Optional[int]) -> str:
        if pct is None or pct < 10:
            return dim("·")
        if pct < 40:
            return dim("░")
        if pct < 70:
            return "▒"
        return "▓"
    return _shade(low) + _shade(mid) + _shade(high)


def _wind_arrow(direction: Optional[int]) -> str:
    """Return a unicode arrow for the wind direction."""
    if direction is None:
        return " "
    arrows = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]
    idx = int((direction + 22.5) / 45) % 8
    return arrows[idx]


class ForecastPlotter:
    """Render a multi-panel 36-hour forecast in the terminal."""

    def __init__(self, width: int = 80):
        self.width = width

    def _time_axis(self, indices, forecast, margin):
        """Generate a two-row time axis aligned 1:1 with plot columns.

        Returns two lines: tens digit row and ones digit row.
        Hours divisible by 6 are highlighted in yellow; others are dimmed.
        """
        tens = " " * margin
        ones = " " * margin
        for idx in indices:
            t = forecast.times[idx] if idx < len(forecast.times) else ""
            if "T" in t:
                hour = int(t.split("T")[1][:2])
                highlight = hour % 6 == 0
                color_fn = yellow if highlight else dim
                tens += color_fn(str(hour // 10))
                ones += color_fn(str(hour % 10))
            else:
                tens += " "
                ones += " "
        return tens + "\n" + ones

    def _data_row(self, label, indices, build_char_fn):
        """Build a single data row: a fixed-width label followed by one char per column.

        label: visible label string (will be padded/truncated to margin width)
        build_char_fn: callable(idx) -> str returning one (possibly ANSI-colored) char
        """
        margin = 12
        padded = f"  {label}"[:margin].ljust(margin)
        row = padded
        for idx in indices:
            row += build_char_fn(idx)
        return row

    def plot_forecast(self, forecast: ForecastData) -> str:
        n = forecast.num_hours
        if n == 0:
            return "No forecast data available."

        margin = 12  # left label area
        plot_w = self.width - margin
        # One column per hour, but compress if too wide
        step = max(1, math.ceil(n / plot_w))
        indices = list(range(0, n, step))
        cols = len(indices)

        lines = []
        lines.append("=" * self.width)
        lines.append(bold("36-HOUR FORECAST").center(self.width + 8))
        lines.append("=" * self.width)

        time_axis = self._time_axis(indices, forecast, margin)

        # --- Panel 1: Temperature + Dew Point sparkline ---
        
        lines.append(self._sparkline_panel(
            "Temp/Dp °C",
            indices, cols,
            [(forecast.temperature_2m, BRIGHT_RED, "●"),
             (forecast.dew_point_2m, BRIGHT_BLUE, "○")],
            margin, height=8,
        ))
        lines.append(dim("  Hour:     "))
        lines.append(time_axis)
        lines.append(f"  {red('●')} Temperature   {blue('○')} Dew Point")
        lines.append("")

        # --- Panel 2: Wind speed + gusts ---
        lines.append(self._sparkline_panel(
            "Wind km/h",
            indices, cols,
            [(forecast.wind_speed_10m, BRIGHT_GREEN, "▸"),
             (forecast.wind_gusts_10m, BRIGHT_YELLOW, "×")],
            margin, height=6,
        ))
        # Wind direction arrows below — aligned with plot columns
        lines.append(self._data_row("Wind dir:", indices, lambda idx:
            green(_wind_arrow(
                forecast.wind_direction_10m[idx]
                if idx < len(forecast.wind_direction_10m) else None
            ))
        ))
        lines.append(dim("  Hour:     "))
        lines.append(time_axis)
        lines.append(f"  {green('▸')} Sustained   {yellow('×')} Gusts   Arrows show direction")
        lines.append("")

        # --- Panel 3: Precipitation ---
        lines.append(bold("  Precip mm"))
        lines.append("  " + "-" * (self.width - 2))
        precip_vals = [forecast.precipitation[i] if i < len(forecast.precipitation) else None
                       for i in indices]
        max_precip = max((v for v in precip_vals if v is not None), default=0.1) or 0.1
        bar_h = 4
        for row in range(bar_h):
            threshold = max_precip * (bar_h - row) / bar_h
            line = " " * margin
            for v in precip_vals:
                if v is not None and v >= threshold:
                    line += blue("█")
                else:
                    line += " "
            lines.append(line)

        # Precip type row — aligned with plot columns
        lines.append(self._data_row("Type:", indices, lambda idx:
            _precip_char(
                forecast.weather_code[idx]
                if idx < len(forecast.weather_code) else None
            )
        ))

        # Probability row — aligned with plot columns
        def _prob_char(idx):
            p = forecast.precipitation_probability[idx] if idx < len(forecast.precipitation_probability) else None
            if p is not None and p > 0:
                d = str(min(p, 99) // 10)
                return cyan(d) if p >= 50 else dim(d)
            return dim("·")
        lines.append(self._data_row("Prob(%):", indices, _prob_char))
        lines.append(dim("  Hour:     "))
        lines.append(time_axis)

        lines.append(f"  {blue('█')} Rain   {cyan('▌')} Snow   {magenta('▌')} Freezing   Prob: digit=tens of %")
        lines.append("")

        # --- Panel 4: Cloud cover (low/mid/high) ---
        lines.append(bold("  Cloud Cover"))
        lines.append("  " + "-" * (self.width - 2))
        for layer_name, layer_data, color in [
            ("High:", forecast.cloud_cover_high, DIM),
            ("Mid: ", forecast.cloud_cover_mid, WHITE),
            ("Low: ", forecast.cloud_cover_low, BRIGHT_CYAN),
        ]:
            def _cloud_char(idx, ld=layer_data, c=color):
                v = ld[idx] if idx < len(ld) else None
                if v is None or v < 10:
                    return dim("·")
                if v < 30:
                    return colorize("░", c)
                if v < 60:
                    return colorize("▒", c)
                if v < 85:
                    return colorize("▓", c)
                return colorize("█", c)
            lines.append(self._data_row(layer_name, indices, _cloud_char))
        lines.append(dim("  Hour:     "))
        lines.append(time_axis)
        lines.append(f"  {dim('·')} Clear  {dim('░')} Few  ▒ Sct  ▓ Bkn  █ Ovc")
        lines.append("")

        # --- Panel 5: Pressure (MSL) ---
        lines.append(self._sparkline_panel(
            "PMSL hPa",
            indices, cols,
            [(forecast.pressure_msl, BRIGHT_MAGENTA, "─")],
            margin, height=5,
        ))
        lines.append(dim("  Hour:     "))
        lines.append(time_axis)
        lines.append(f"  {magenta('─')} Mean Sea-Level Pressure")
        lines.append("")

        # --- Weather description timeline ---
        lines.append(bold("  Weather Summary"))
        lines.append("  " + "-" * (self.width - 2))
        desc_row = " " * margin
        prev_desc = ""
        for idx in indices:
            wc = forecast.weather_code[idx] if idx < len(forecast.weather_code) else None
            desc, _ = _WMO_CODES.get(wc, ("?", "")) if wc is not None else ("", "")
            if desc != prev_desc:
                desc_row += bold(desc[0]) if desc else " "
                prev_desc = desc
            else:
                desc_row += dim("─")
        lines.append(desc_row)
        lines.append(dim("  Hour:     "))
        lines.append(time_axis)

        # Legend of weather codes present
        seen_codes = set()
        for idx in indices:
            wc = forecast.weather_code[idx] if idx < len(forecast.weather_code) else None
            if wc is not None:
                seen_codes.add(wc)
        if seen_codes:
            legend_parts = []
            for code in sorted(seen_codes):
                desc, _ = _WMO_CODES.get(code, (f"WMO{code}", ""))
                legend_parts.append(f"{bold(desc[0])}={desc}")
            line = "  "
            for part in legend_parts:
                if len(visible_char(line)) + len(visible_char(part)) + 3 > self.width:
                    lines.append(line)
                    line = "  "
                line += part + "  "
            if line.strip():
                lines.append(line)

        return "\n".join(lines)

    def _sparkline_panel(
        self,
        label: str,
        indices: List[int],
        cols: int,
        series: List[tuple],  # (values_list, color_code, char)
        margin: int,
        height: int = 8,
    ) -> str:
        """Render a mini sparkline chart for one or more series."""
        # Gather all values for range
        all_vals = []
        for vals, _, _ in series:
            for idx in indices:
                v = vals[idx] if idx < len(vals) else None
                if v is not None:
                    all_vals.append(v)

        if not all_vals:
            return f"  {label}: no data"

        v_min = min(all_vals)
        v_max = max(all_vals)
        if v_max == v_min:
            v_max = v_min + 1

        grid = [[" "] * (margin + cols) for _ in range(height)]

        # Y-axis labels
        for r in [0, height // 2, height - 1]:
            val = v_max - (v_max - v_min) * r / (height - 1)
            lbl = f"{val:>6.0f}  "
            for i, ch in enumerate(lbl[:margin]):
                grid[r][i] = cyan(ch)

        # Label
        lbl_str = f"  {label}"
        # Place in first row before the value label
        # Actually put it as a separate header line

        # Plot series
        for vals, color, char in series:
            prev_col, prev_row = None, None
            for ci, idx in enumerate(indices):
                v = vals[idx] if idx < len(vals) else None
                if v is None:
                    prev_col, prev_row = None, None
                    continue
                frac = (v - v_min) / (v_max - v_min)
                row = int((1.0 - frac) * (height - 1))
                row = max(0, min(height - 1, row))
                col = margin + ci

                # Interpolate between points
                if prev_col is not None:
                    steps = max(abs(col - prev_col), abs(row - prev_row), 1)
                    for s in range(1, steps):
                        ic = prev_col + int((col - prev_col) * s / steps)
                        ir = prev_row + int((row - prev_row) * s / steps)
                        if margin <= ic < margin + cols and 0 <= ir < height:
                            vc = visible_char(grid[ir][ic])
                            if vc in (" ", "·"):
                                grid[ir][ic] = colorize(char, color)

                if margin <= col < margin + cols and 0 <= row < height:
                    grid[row][col] = colorize(char, color)
                prev_col, prev_row = col, row

        result_lines = []
        result_lines.append(bold(f"  {label}"))
        result_lines.append("  " + "-" * (self.width - 2))
        for row in grid:
            result_lines.append("".join(row))

        return "\n".join(result_lines)


def create_forecast(forecast: ForecastData) -> str:
    plotter = ForecastPlotter()
    return plotter.plot_forecast(forecast)
