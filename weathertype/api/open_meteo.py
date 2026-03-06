"""Open-Meteo API client for fetching weather profile data."""

import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

from weathertype.api.models import WeatherProfile, WeatherDataResponse


class OpenMeteoClient:
    """Client for interacting with the Open-Meteo API."""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    # Pressure levels available from Open-Meteo (hPa)
    DEFAULT_PRESSURE_LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150]

    def __init__(self, cache_responses: bool = True):
        self.cache_responses = cache_responses
        self._cache: Dict[str, Any] = {}

    def get_weather_profile(
        self,
        latitude: float,
        longitude: float,
        pressure_levels: Optional[List[int]] = None,
        forecast_hour: Optional[int] = None,
    ) -> WeatherDataResponse:
        """Fetch weather profile data from Open-Meteo.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            pressure_levels: Custom pressure levels (default: DEFAULT_PRESSURE_LEVELS)
            forecast_hour: Which forecast hour to use (default: closest to now)

        Returns:
            WeatherDataResponse containing the profile or error
        """
        levels = pressure_levels or self.DEFAULT_PRESSURE_LEVELS
        cache_key = f"{latitude},{longitude}"

        if self.cache_responses and cache_key in self._cache:
            cached = self._cache[cache_key]
            return WeatherDataResponse(
                profile=self._parse_profile(cached, latitude, longitude, levels, forecast_hour),
                api_metadata={"cached": True},
            )

        try:
            # Build hourly variable list for pressure levels
            hourly_vars = []
            for level in levels:
                hourly_vars.append(f"temperature_{level}hPa")
                hourly_vars.append(f"dewpoint_{level}hPa")
                hourly_vars.append(f"windspeed_{level}hPa")
                hourly_vars.append(f"winddirection_{level}hPa")

            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join(hourly_vars),
                "forecast_days": 1,
                "timezone": "auto",
            }

            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if self.cache_responses:
                self._cache[cache_key] = data

            return WeatherDataResponse(
                profile=self._parse_profile(data, latitude, longitude, levels, forecast_hour),
                api_metadata={
                    "timestamp": datetime.now().isoformat(),
                    "cached": False,
                    "elevation": data.get("elevation"),
                    "timezone": data.get("timezone"),
                },
            )

        except requests.exceptions.RequestException as e:
            return WeatherDataResponse(error=str(e))

    def _parse_profile(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        levels: List[int],
        forecast_hour: Optional[int] = None,
    ) -> WeatherProfile:
        """Parse Open-Meteo API response into a WeatherProfile."""
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])

        # Pick which time index to use
        if forecast_hour is not None and forecast_hour < len(times):
            idx = forecast_hour
        else:
            # Use closest hour to current time
            now = datetime.now()
            idx = min(now.hour, len(times) - 1) if times else 0

        time_str = times[idx] if idx < len(times) else None

        pressure_levels: List[float] = []
        temperatures: List[float] = []
        dew_points: List[float] = []
        wind_speeds: List[float] = []
        wind_directions: List[int] = []

        for level in levels:
            temp_vals = hourly.get(f"temperature_{level}hPa", [])
            dp_vals = hourly.get(f"dewpoint_{level}hPa", [])
            ws_vals = hourly.get(f"windspeed_{level}hPa", [])
            wd_vals = hourly.get(f"winddirection_{level}hPa", [])

            # Only include level if we have temperature data for it
            if temp_vals and idx < len(temp_vals) and temp_vals[idx] is not None:
                pressure_levels.append(float(level))
                temperatures.append(temp_vals[idx])  # Already in °C
                dew_points.append(
                    dp_vals[idx]
                    if dp_vals and idx < len(dp_vals) and dp_vals[idx] is not None
                    else temp_vals[idx]
                )
                wind_speeds.append(
                    ws_vals[idx]
                    if ws_vals and idx < len(ws_vals) and ws_vals[idx] is not None
                    else 0.0
                )
                wind_directions.append(
                    int(wd_vals[idx])
                    if wd_vals and idx < len(wd_vals) and wd_vals[idx] is not None
                    else 0
                )

        elevation = data.get("elevation", 0.0)

        return WeatherProfile(
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            pressure_levels=pressure_levels,
            temperatures=temperatures,
            dew_points=dew_points,
            wind_speeds=wind_speeds,
            wind_directions=wind_directions,
            time=time_str,
        )

    def clear_cache(self) -> None:
        """Clear the API response cache."""
        self._cache.clear()
