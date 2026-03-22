"""Regional temperature heatmap renderer."""

from weathertype.api.models import RegionalGrid
from weathertype.utils.colors import (
    colors_on, colorize_256, bg_colorize_256, temperature_color,
    bold, dim, RESET,
)


class RegionalTempPlotter:
    """Render a 2D temperature heatmap in the terminal."""

    def __init__(self, width: int = 72, height: int = 35):
        self._width = width
        self._height = height

    def plot_temperature_map(self, grid: RegionalGrid) -> str:
        v_min, v_max = grid.value_range()
        lines = []

        # Title
        lines.append("=" * self._width)
        title = "REGIONAL TEMPERATURE MAP (2m)"
        lines.append(title.center(self._width))
        lines.append("=" * self._width)

        # Margin for latitude labels
        margin = 7

        # Longitude labels across top
        avail = self._width - margin
        # Each cell is 2 chars wide
        cell_w = max(2, avail // grid.cols)
        lon_line = " " * margin
        # Show every other longitude for readability
        for c in range(grid.cols):
            if c % 3 == 0 and c < grid.cols:
                label = f"{grid.longitudes[c]:.1f}"
                lon_line += label[:cell_w].ljust(cell_w)
            else:
                lon_line += " " * cell_w
        lines.append(lon_line)

        # Find center row/col
        center_r = grid.rows // 2
        center_c = grid.cols // 2

        # Grid rows
        for r in range(grid.rows):
            # Latitude label
            lat_label = f"{grid.latitudes[r]:6.1f} "
            row_str = lat_label

            for c in range(grid.cols):
                val = grid.get_value(r, c)

                if r == center_r and c == center_c:
                    # Center marker
                    if colors_on():
                        color_idx = temperature_color(val, v_min, v_max) if val is not None else 0
                        row_str += bg_colorize_256("+", 231, color_idx)
                        row_str += bg_colorize_256(" ", 231, color_idx)
                    else:
                        row_str += "+ "
                elif val is not None:
                    if colors_on():
                        color_idx = temperature_color(val, v_min, v_max)
                        block = "\u2588" * cell_w
                        row_str += colorize_256(block, color_idx)
                    else:
                        # No-color: show numeric value
                        num = f"{val:.0f}"
                        row_str += num[:cell_w].rjust(cell_w)
                else:
                    row_str += " " * cell_w

            lines.append(row_str)

        # Legend
        lines.append("")
        if colors_on():
            legend = "  Legend: "
            steps = 16
            for i in range(steps):
                t = i / (steps - 1)
                val = v_min + t * (v_max - v_min)
                color_idx = temperature_color(val, v_min, v_max)
                legend += colorize_256("\u2588", color_idx)
            legend += f"  {v_min:.1f} - {v_max:.1f} {grid.unit}"
            lines.append(legend)
        else:
            lines.append(f"  Range: {v_min:.1f} - {v_max:.1f} {grid.unit}")

        if grid.time:
            lines.append(f"  Time: {grid.time}")
        lines.append(f"  Center: + ({grid.center_lat:.2f}, {grid.center_lon:.2f})")
        lines.append(f"  Grid: {grid.rows}x{grid.cols} (~200km radius)")

        return "\n".join(lines)
