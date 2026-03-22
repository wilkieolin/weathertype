"""Regional pressure heatmap with isobar contours."""

from weathertype.api.models import RegionalGrid
from weathertype.calculations.regional import find_contours
from weathertype.utils.colors import (
    colors_on, colorize_256, bg_colorize_256, pressure_color,
    bold, dim, RESET,
)


class RegionalPressurePlotter:
    """Render a 2D pressure map with isobar contour lines."""

    CONTOUR_INTERVAL = 2.0  # hPa between isobars

    def __init__(self, width: int = 72, height: int = 35):
        self._width = width
        self._height = height

    def plot_pressure_map(self, grid: RegionalGrid) -> str:
        v_min, v_max = grid.value_range()
        lines = []

        # Title
        lines.append("=" * self._width)
        title = "REGIONAL PRESSURE MAP (MSL)"
        lines.append(title.center(self._width))
        lines.append("=" * self._width)

        margin = 7
        avail = self._width - margin
        cell_w = max(2, avail // grid.cols)

        # Longitude labels
        lon_line = " " * margin
        for c in range(grid.cols):
            if c % 3 == 0:
                label = f"{grid.longitudes[c]:.1f}"
                lon_line += label[:cell_w].ljust(cell_w)
            else:
                lon_line += " " * cell_w
        lines.append(lon_line)

        # Find contour cells
        contours = find_contours(
            grid.values, grid.rows, grid.cols, self.CONTOUR_INTERVAL
        )
        contour_cells = set()
        contour_labels = {}
        for level, cells in contours.items():
            for r, c in cells:
                contour_cells.add((r, c))
                # Label the first cell of each contour with the pressure value
                if (r, c) not in contour_labels:
                    contour_labels[(r, c)] = level

        center_r = grid.rows // 2
        center_c = grid.cols // 2

        # Grid rows
        for r in range(grid.rows):
            lat_label = f"{grid.latitudes[r]:6.1f} "
            row_str = lat_label

            for c in range(grid.cols):
                val = grid.get_value(r, c)
                is_contour = (r, c) in contour_cells

                if r == center_r and c == center_c:
                    if colors_on() and val is not None:
                        color_idx = pressure_color(val, v_min, v_max)
                        row_str += bg_colorize_256("+", 231, color_idx)
                        row_str += bg_colorize_256(" ", 231, color_idx)
                    else:
                        row_str += "+ "
                elif is_contour and val is not None:
                    if colors_on():
                        color_idx = pressure_color(val, v_min, v_max)
                        # Contour lines shown as dashes on colored background
                        row_str += bg_colorize_256("-", 231, color_idx)
                        row_str += bg_colorize_256("-", 231, color_idx)
                    else:
                        row_str += "--"
                elif val is not None:
                    if colors_on():
                        color_idx = pressure_color(val, v_min, v_max)
                        block = "\u2588" * cell_w
                        row_str += colorize_256(block, color_idx)
                    else:
                        num = f"{val:.0f}"
                        # Truncate to cell width
                        row_str += num[-cell_w:].rjust(cell_w)
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
                color_idx = pressure_color(val, v_min, v_max)
                legend += colorize_256("\u2588", color_idx)
            legend += f"  {v_min:.1f} - {v_max:.1f} {grid.unit}"
            lines.append(legend)
        else:
            lines.append(f"  Range: {v_min:.1f} - {v_max:.1f} {grid.unit}")

        lines.append(f"  Isobars: -- (every {self.CONTOUR_INTERVAL:.0f} {grid.unit})")
        if grid.time:
            lines.append(f"  Time: {grid.time}")
        lines.append(f"  Center: + ({grid.center_lat:.2f}, {grid.center_lon:.2f})")

        return "\n".join(lines)
