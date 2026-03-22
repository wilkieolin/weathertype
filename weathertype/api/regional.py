"""Regional grid data fetching from Open-Meteo using multi-location batching."""

import requests
from datetime import datetime
from typing import List, Optional

from weathertype.api.models import RegionalGrid, RegionalGridResponse
from weathertype.utils.coordinates import generate_grid_coordinates


class RegionalGridClient:
    """Fetch 2D grid weather data from Open-Meteo."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    CHUNK_SIZE = 50  # locations per request

    def __init__(self):
        self._cache = {}

    def get_regional_temperature(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float = 200.0,
        grid_size: int = 15,
    ) -> RegionalGridResponse:
        return self._fetch_variable(
            center_lat, center_lon, radius_km, grid_size,
            variable="temperature_2m", unit="C",
        )

    def get_regional_pressure(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float = 200.0,
        grid_size: int = 15,
    ) -> RegionalGridResponse:
        return self._fetch_variable(
            center_lat, center_lon, radius_km, grid_size,
            variable="pressure_msl", unit="hPa",
        )

    def _fetch_variable(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float,
        grid_size: int,
        variable: str,
        unit: str,
    ) -> RegionalGridResponse:
        cache_key = f"regional_{variable}_{center_lat},{center_lon},{radius_km},{grid_size}"
        if cache_key in self._cache:
            return RegionalGridResponse(
                grid=self._cache[cache_key],
                api_metadata={"cached": True},
            )

        try:
            lats, lons = generate_grid_coordinates(
                center_lat, center_lon, radius_km, grid_size
            )

            # Build flat list of all (lat, lon) pairs with their grid position
            points = []
            for r, lat in enumerate(lats):
                for c, lon in enumerate(lons):
                    points.append((r, c, lat, lon))

            # Fetch in chunks with small delay to avoid rate limits
            import time
            values = [None] * (grid_size * grid_size)
            for i in range(0, len(points), self.CHUNK_SIZE):
                if i > 0:
                    time.sleep(0.3)
                chunk = points[i : i + self.CHUNK_SIZE]
                chunk_lats = [p[2] for p in chunk]
                chunk_lons = [p[3] for p in chunk]

                chunk_values = self._fetch_chunk(chunk_lats, chunk_lons, variable)

                for j, (r, c, _, _) in enumerate(chunk):
                    if j < len(chunk_values):
                        values[r * grid_size + c] = chunk_values[j]

            # Determine time from current hour
            now = datetime.now()
            time_str = now.strftime("%Y-%m-%dT%H:00")

            grid = RegionalGrid(
                center_lat=center_lat,
                center_lon=center_lon,
                rows=grid_size,
                cols=grid_size,
                latitudes=lats,
                longitudes=lons,
                values=values,
                variable_name=variable,
                unit=unit,
                time=time_str,
            )

            self._cache[cache_key] = grid
            return RegionalGridResponse(
                grid=grid,
                api_metadata={"cached": False},
            )

        except Exception as e:
            return RegionalGridResponse(error=str(e))

    def _fetch_chunk(
        self,
        lats: List[float],
        lons: List[float],
        variable: str,
    ) -> List[Optional[float]]:
        """Fetch a single variable for multiple locations in one request."""
        params = {
            "latitude": ",".join(f"{lat:.4f}" for lat in lats),
            "longitude": ",".join(f"{lon:.4f}" for lon in lons),
            "hourly": variable,
            "forecast_days": 1,
            "timezone": "auto",
        }

        response = requests.get(self.BASE_URL, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        now = datetime.now()
        results = []

        if isinstance(data, list):
            # Multi-location response: list of location objects
            for loc_data in data:
                hourly = loc_data.get("hourly", {})
                vals = hourly.get(variable, [])
                times = hourly.get("time", [])
                idx = min(now.hour, len(times) - 1) if times else 0
                if vals and idx < len(vals):
                    results.append(vals[idx])
                else:
                    results.append(None)
        else:
            # Single location response (only 1 point in chunk)
            hourly = data.get("hourly", {})
            vals = hourly.get(variable, [])
            times = hourly.get("time", [])
            idx = min(now.hour, len(times) - 1) if times else 0
            if vals and idx < len(vals):
                results.append(vals[idx])
            else:
                results.append(None)

        return results

    def clear_cache(self) -> None:
        self._cache.clear()
