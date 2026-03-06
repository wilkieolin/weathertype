"""Data models for weather profile data from Open-Meteo API."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WeatherProfile:
    """Represents a vertical weather profile at a specific location."""
    latitude: float
    longitude: float
    elevation: float
    
    # Pressure levels in hPa (ascending order from surface to upper atmosphere)
    pressure_levels: List[float] = field(default_factory=list)
    
    # Temperature in Celsius
    temperatures: List[float] = field(default_factory=list)
    
    # Dew point temperature in Celsius
    dew_points: List[float] = field(default_factory=list)
    
    # Wind speed in km/h
    wind_speeds: List[float] = field(default_factory=list)
    
    # Wind direction in degrees (0-360, where 0 is north)
    wind_directions: List[int] = field(default_factory=list)
    
    # Time of the profile
    time: Optional[str] = None
    
    def __post_init__(self):
        """Validate that all lists have the same length."""
        n_levels = len(self.pressure_levels)
        assert len(self.temperatures) == n_levels, "Temperature list length mismatch"
        assert len(self.dew_points) == n_levels, "Dew point list length mismatch"
        assert len(self.wind_speeds) == n_levels, "Wind speed list length mismatch"
        assert len(self.wind_directions) == n_levels, "Wind direction list length mismatch"
    
    @property
    def num_levels(self) -> int:
        """Return the number of pressure levels."""
        return len(self.pressure_levels)
    
    def get_level_index(self, pressure_hpa: float) -> Optional[int]:
        """Find the index of a specific pressure level.
        
        Args:
            pressure_hpa: Pressure in hPa
            
        Returns:
            Index of the pressure level, or None if not found
        """
        try:
            return self.pressure_levels.index(pressure_hpa)
        except ValueError:
            return None


@dataclass
class WeatherDataResponse:
    """Response from the weather API."""
    profile: Optional[WeatherProfile] = None
    error: Optional[str] = None
    api_metadata: dict = field(default_factory=dict)
