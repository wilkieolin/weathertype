"""Location lookup and validation utilities."""

import requests
from typing import Optional, Tuple


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def geocode_location(name: str) -> Optional[Tuple[float, float, str]]:
    """Look up coordinates for a location name.

    Args:
        name: City name, e.g. "Chicago, IL" or "London"

    Returns:
        Tuple of (latitude, longitude, display_name) or None if not found
    """
    try:
        response = requests.get(
            GEOCODING_URL,
            params={"name": name, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results")
        if not results:
            return None

        r = results[0]
        display = r.get("name", name)
        admin1 = r.get("admin1", "")
        country = r.get("country", "")
        if admin1:
            display = f"{display}, {admin1}"
        if country:
            display = f"{display}, {country}"

        return (r["latitude"], r["longitude"], display)
    except (requests.exceptions.RequestException, KeyError, ValueError):
        return None


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Check that lat/lon are within valid ranges."""
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def generate_grid_coordinates(
    center_lat: float,
    center_lon: float,
    radius_km: float = 200.0,
    grid_size: int = 15,
) -> tuple:
    """Generate a grid_size x grid_size grid of lat/lon coordinates.

    Returns (latitudes, longitudes) where latitudes are north-to-south
    and longitudes are west-to-east.
    """
    import math

    # 1 degree latitude ~ 111.32 km
    lat_delta = radius_km / 111.32
    # 1 degree longitude varies with latitude
    lon_delta = radius_km / (111.32 * math.cos(math.radians(center_lat)))

    lats = [
        center_lat + lat_delta - (2 * lat_delta * i / (grid_size - 1))
        for i in range(grid_size)
    ]
    lons = [
        center_lon - lon_delta + (2 * lon_delta * i / (grid_size - 1))
        for i in range(grid_size)
    ]
    return (lats, lons)
