"""Open-Meteo API client for fetching weather profile data."""

import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

from weathertype.api.models import WeatherProfile, WeatherDataResponse, ForecastData, ForecastDataResponse


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

    def get_forecast_data(
        self,
        latitude: float,
        longitude: float,
        hours: int = 36,
    ) -> ForecastDataResponse:
        """Fetch hourly surface forecast data for a time-series plot.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            hours: Number of forecast hours (default 36)
        """
        cache_key = f"forecast_{latitude},{longitude},{hours}"
        if self.cache_responses and cache_key in self._cache:
            return ForecastDataResponse(
                forecast=self._parse_forecast(self._cache[cache_key], latitude, longitude, hours),
                api_metadata={"cached": True},
            )

        try:
            hourly_vars = [
                "temperature_2m",
                "dewpoint_2m",
                "windspeed_10m",
                "winddirection_10m",
                "windgusts_10m",
                "precipitation",
                "precipitation_probability",
                "weathercode",
                "cloudcover",
                "cloudcover_low",
                "cloudcover_mid",
                "cloudcover_high",
                "pressure_msl",
            ]

            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join(hourly_vars),
                "forecast_days": 3,
                "timezone": "auto",
            }

            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if self.cache_responses:
                self._cache[cache_key] = data

            return ForecastDataResponse(
                forecast=self._parse_forecast(data, latitude, longitude, hours),
                api_metadata={
                    "timestamp": datetime.now().isoformat(),
                    "cached": False,
                    "elevation": data.get("elevation"),
                    "timezone": data.get("timezone"),
                },
            )

        except requests.exceptions.RequestException as e:
            return ForecastDataResponse(error=str(e))

    def _parse_forecast(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float,
        hours: int,
    ) -> ForecastData:
        """Parse Open-Meteo response into ForecastData."""
        hourly = data.get("hourly", {})
        all_times = hourly.get("time", [])

        # Start from the current hour
        now = datetime.now()
        start_idx = min(now.hour, len(all_times) - 1) if all_times else 0
        end_idx = min(start_idx + hours, len(all_times))
        times = all_times[start_idx:end_idx]

        def _get(key: str) -> list:
            vals = hourly.get(key, [])
            return vals[start_idx:end_idx] if vals else [None] * len(times)

        return ForecastData(
            latitude=latitude,
            longitude=longitude,
            elevation=data.get("elevation", 0.0),
            times=times,
            temperature_2m=_get("temperature_2m"),
            dew_point_2m=_get("dewpoint_2m"),
            wind_speed_10m=_get("windspeed_10m"),
            wind_direction_10m=[int(v) if v is not None else None for v in _get("winddirection_10m")],
            wind_gusts_10m=_get("windgusts_10m"),
            precipitation=_get("precipitation"),
            precipitation_probability=[int(v) if v is not None else None for v in _get("precipitation_probability")],
            weather_code=[int(v) if v is not None else None for v in _get("weathercode")],
            cloud_cover=[int(v) if v is not None else None for v in _get("cloudcover")],
            cloud_cover_low=[int(v) if v is not None else None for v in _get("cloudcover_low")],
            cloud_cover_mid=[int(v) if v is not None else None for v in _get("cloudcover_mid")],
            cloud_cover_high=[int(v) if v is not None else None for v in _get("cloudcover_high")],
            pressure_msl=_get("pressure_msl"),
        )

    def clear_cache(self) -> None:
        """Clear the API response cache."""
        self._cache.clear()
