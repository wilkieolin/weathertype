"""Radar reflectivity terminal renderer."""

from weathertype.api.models import RadarData
from weathertype.utils.colors import (
    colors_on, colorize_256, dbz_color, dim, bold, RESET,
)


# dBZ intensity to character mapping for no-color mode
_DBZ_CHARS = [
    (5, " "),    # none
    (20, "\u2591"),  # light ░
    (35, "\u2592"),  # medium ▒
    (50, "\u2593"),  # heavy ▓
    (999, "\u2588"), # extreme █
]


class RadarPlotter:
    """Render radar reflectivity as a terminal heatmap."""

    def __init__(self, width: int = 72, height: int = 30):
        self._width = width
        self._height = height

    def plot_radar(self, radar: RadarData) -> str:
        lines = []

        # Title
        lines.append("=" * self._width)
        title = "RADAR REFLECTIVITY"
        lines.append(title.center(self._width))
        lines.append("=" * self._width)

        margin = 7
        cell_w = 2  # 2 chars per cell for aspect ratio

        # Longitude labels
        lon_span = radar.lon_max - radar.lon_min
        lon_line = " " * margin
        for c in range(0, radar.cols, max(1, radar.cols // 6)):
            lon = radar.lon_min + lon_span * c / radar.cols
            label = f"{lon:.1f}"
            lon_line += label[:cell_w * 2].ljust(cell_w * (radar.cols // 6 if radar.cols // 6 > 0 else 1))
        lines.append(lon_line[:self._width])

        # Find center pixel
        lat_span = radar.lat_max - radar.lat_min
        center_r = int((radar.lat_max - radar.center_lat) / lat_span * radar.rows) if lat_span > 0 else radar.rows // 2
        center_c = int((radar.center_lon - radar.lon_min) / lon_span * radar.cols) if lon_span > 0 else radar.cols // 2
        center_r = max(0, min(center_r, radar.rows - 1))
        center_c = max(0, min(center_c, radar.cols - 1))

        # Grid rows
        for r in range(radar.rows):
            lat = radar.lat_max - lat_span * r / radar.rows if lat_span > 0 else radar.center_lat
            lat_label = f"{lat:6.1f} "
            row_str = lat_label

            for c in range(radar.cols):
                dbz = radar.get_dbz(r, c)

                if r == center_r and c == center_c:
                    # Center marker
                    if colors_on():
                        row_str += f"\033[1;97m+\033[0m "
                    else:
                        row_str += "+ "
                elif dbz is not None and dbz >= 5:
                    if colors_on():
                        color_idx = dbz_color(dbz)
                        row_str += colorize_256("\u2588" * cell_w, color_idx)
                    else:
                        char = " "
                        for threshold, ch in _DBZ_CHARS:
                            if dbz < threshold:
                                char = ch
                                break
                        row_str += char * cell_w
                else:
                    # No return - show dim dot for radar coverage
                    if colors_on():
                        row_str += dim("\u00b7") + " "
                    else:
                        row_str += ". "

            lines.append(row_str)

        # Legend
        lines.append("")
        if colors_on():
            legend = "  "
            dbz_labels = [
                (5, "Light"), (20, "Mod"), (35, "Heavy"),
                (50, "Severe"), (65, "Extreme"),
            ]
            for dbz_val, label in dbz_labels:
                color_idx = dbz_color(dbz_val)
                legend += colorize_256("\u2588\u2588", color_idx)
                legend += f" {label}  "
            lines.append(legend)
        else:
            lines.append("  \u2591 Light  \u2592 Moderate  \u2593 Heavy  \u2588 Extreme")

        if radar.time_str:
            lines.append(f"  Scan: {radar.time_str}")
        lines.append(f"  Center: + ({radar.center_lat:.2f}, {radar.center_lon:.2f})")
        lines.append("  Source: RainViewer (rainviewer.com)")

        return "\n".join(lines)
