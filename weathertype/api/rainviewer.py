"""RainViewer API client for radar reflectivity data."""

import math
import requests
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from weathertype.api.models import RadarData, RadarDataResponse
from weathertype.api.png_decoder import decode_png


class RainViewerClient:
    """Client for fetching radar data from the RainViewer API."""

    MAPS_URL = "https://api.rainviewer.com/public/weather-maps.json"

    # RainViewer Universal Blue color scheme (scheme 2)
    # Approximate dBZ mapping based on pixel color intensity
    COLOR_SCHEME = 2
    TILE_SIZE = 256
    ZOOM = 6  # ~350-490km per tile at mid latitudes

    def get_radar_data(
        self,
        center_lat: float,
        center_lon: float,
        terminal_rows: int = 30,
        terminal_cols: int = 60,
    ) -> RadarDataResponse:
        try:
            # Get latest radar timestamp and tile paths
            maps = self._get_maps()
            if not maps:
                return RadarDataResponse(error="Could not fetch RainViewer map data")

            host = maps.get("host", "")
            radar = maps.get("radar", {})
            past = radar.get("past", [])
            if not past:
                return RadarDataResponse(error="No radar frames available")

            # Use the most recent frame
            frame = past[-1]
            path = frame["path"]
            timestamp = frame["time"]

            # Convert center to tile coordinates
            tile_x, tile_y = self._lat_lon_to_tile(center_lat, center_lon, self.ZOOM)

            # Determine tile bounds for the radar data extent
            lat_max, lat_min, lon_min, lon_max = self._tile_bounds(
                tile_x, tile_y, self.ZOOM
            )

            # Fetch the tile
            tile_url = f"{host}{path}/{self.TILE_SIZE}/{self.ZOOM}/{tile_x}/{tile_y}/{self.COLOR_SCHEME}/1_1.png"
            resp = requests.get(tile_url, timeout=30)
            resp.raise_for_status()

            # Decode PNG
            width, height, pixels = decode_png(resp.content)

            # Convert pixels to dBZ and downsample
            reflectivity = self._pixels_to_dbz_grid(
                pixels, width, height, terminal_rows, terminal_cols
            )

            time_str = datetime.fromtimestamp(
                timestamp, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M UTC")

            return RadarDataResponse(
                radar=RadarData(
                    center_lat=center_lat,
                    center_lon=center_lon,
                    rows=terminal_rows,
                    cols=terminal_cols,
                    reflectivity=reflectivity,
                    lat_min=lat_min,
                    lat_max=lat_max,
                    lon_min=lon_min,
                    lon_max=lon_max,
                    timestamp=timestamp,
                    time_str=time_str,
                ),
            )

        except Exception as e:
            return RadarDataResponse(error=str(e))

    def _get_maps(self) -> Optional[dict]:
        resp = requests.get(self.MAPS_URL, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _lat_lon_to_tile(
        self, lat: float, lon: float, zoom: int
    ) -> Tuple[int, int]:
        """Convert lat/lon to slippy map tile coordinates."""
        n = 2 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        lat_rad = math.radians(lat)
        y = int(
            (1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi)
            / 2.0
            * n
        )
        return (x, y)

    def _tile_bounds(
        self, x: int, y: int, zoom: int
    ) -> Tuple[float, float, float, float]:
        """Get geographic bounds of a tile. Returns (lat_max, lat_min, lon_min, lon_max)."""
        n = 2 ** zoom
        lon_min = x / n * 360.0 - 180.0
        lon_max = (x + 1) / n * 360.0 - 180.0

        lat_max = math.degrees(
            math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        )
        lat_min = math.degrees(
            math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
        )
        return (lat_max, lat_min, lon_min, lon_max)

    def _pixel_to_dbz(self, r: int, g: int, b: int, a: int) -> Optional[float]:
        """Convert an RGBA pixel to approximate dBZ value.

        RainViewer color scheme maps:
        - Transparent (a=0) → no return
        - Dark blues/cyans → light precipitation (~0-15 dBZ)
        - Greens → moderate (~15-30 dBZ)
        - Yellows → heavy (~30-40 dBZ)
        - Oranges/Reds → severe (~40-55 dBZ)
        - Magentas/White → extreme (~55-75 dBZ)
        """
        if a < 10:
            return None

        # Use a heuristic based on overall intensity and color channel balance
        intensity = (r + g + b) / 3.0

        # Approximate dBZ from color characteristics
        if r < 50 and g < 50 and b < 50:
            return 0.0  # Very dark, near-zero return
        elif b > r and b > g:
            # Blue/cyan dominant → light
            return 5.0 + (intensity / 255.0) * 15.0
        elif g > r and g > b:
            # Green dominant → moderate
            return 20.0 + (g / 255.0) * 15.0
        elif r > 200 and g > 200:
            # Yellow → heavy
            return 35.0 + min(r, g) / 255.0 * 10.0
        elif r > g and r > b:
            if g > 100:
                # Orange → severe
                return 40.0 + (r / 255.0) * 10.0
            else:
                # Red → very severe
                return 50.0 + (r / 255.0) * 10.0
        elif r > 150 and b > 150:
            # Magenta → extreme
            return 60.0 + intensity / 255.0 * 10.0
        elif intensity > 200:
            # White/bright → extreme
            return 65.0 + intensity / 255.0 * 10.0
        else:
            return 5.0 + intensity / 255.0 * 30.0

    def _pixels_to_dbz_grid(
        self,
        pixels: List[Tuple[int, int, int, int]],
        src_w: int,
        src_h: int,
        dst_rows: int,
        dst_cols: int,
    ) -> List[Optional[float]]:
        """Downsample pixel grid to terminal grid, converting to dBZ."""
        result = []
        for row in range(dst_rows):
            for col in range(dst_cols):
                # Map terminal cell to source pixel region
                src_y_start = int(row * src_h / dst_rows)
                src_y_end = int((row + 1) * src_h / dst_rows)
                src_x_start = int(col * src_w / dst_cols)
                src_x_end = int((col + 1) * src_w / dst_cols)

                # Average the dBZ values in this region
                dbz_sum = 0.0
                count = 0
                has_return = False

                for sy in range(src_y_start, src_y_end):
                    for sx in range(src_x_start, src_x_end):
                        pixel = pixels[sy * src_w + sx]
                        dbz = self._pixel_to_dbz(*pixel)
                        if dbz is not None:
                            dbz_sum += dbz
                            count += 1
                            has_return = True

                if has_return and count > 0:
                    result.append(dbz_sum / count)
                else:
                    result.append(None)

        return result
