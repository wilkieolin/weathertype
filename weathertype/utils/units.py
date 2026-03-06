"""Unit conversion utilities for meteorological calculations."""

from typing import Union


def hpa_to_pa(pressure_hpa: float) -> float:
    """Convert pressure from hectopascals (hPa) to pascals (Pa).
    
    Args:
        pressure_hpa: Pressure in hPa
        
    Returns:
        Pressure in Pa
    """
    return pressure_hpa * 100


def pa_to_hpa(pressure_pa: float) -> float:
    """Convert pressure from pascals (Pa) to hectopascals (hPa).
    
    Args:
        pressure_pa: Pressure in Pa
        
    Returns:
        Pressure in hPa
    """
    return pressure_pa / 100


def celsius_to_kelvin(temp_c: float) -> float:
    """Convert temperature from Celsius to Kelvin.
    
    Args:
        temp_c: Temperature in Celsius
        
    Returns:
        Temperature in Kelvin
    """
    return temp_c + 273.15


def kelvin_to_celsius(temp_k: float) -> float:
    """Convert temperature from Kelvin to Celsius.
    
    Args:
        temp_k: Temperature in Kelvin
        
    Returns:
        Temperature in Celsius
    """
    return temp_k - 273.15


def kmh_to_ms(speed_kmh: float) -> float:
    """Convert speed from kilometers per hour (km/h) to meters per second (m/s).
    
    Args:
        speed_kmh: Speed in km/h
        
    Returns:
        Speed in m/s
    """
    return speed_kmh / 3.6


def ms_to_kmh(speed_ms: float) -> float:
    """Convert speed from meters per second (m/s) to kilometers per hour (km/h).
    
    Args:
        speed_ms: Speed in m/s
        
    Returns:
        Speed in km/h
    """
    return speed_ms * 3.6


def degrees_to_radians(angle_deg: float) -> float:
    """Convert angle from degrees to radians.
    
    Args:
        angle_deg: Angle in degrees
        
    Returns:
        Angle in radians
    """
    import math
    return angle_deg * (math.pi / 180)


def radians_to_degrees(angle_rad: float) -> float:
    """Convert angle from radians to degrees.
    
    Args:
        angle_rad: Angle in radians
        
    Returns:
        Angle in degrees
    """
    import math
    return angle_rad * (180 / math.pi)


def wind_components_to_direction(u: float, v: float) -> float:
    """Calculate wind direction from u and v components.
    
    Args:
        u: Eastward wind component (m/s)
        v: Northward wind component (m/s)
        
    Returns:
        Wind direction in degrees (0-360, where 0 is north)
    """
    import math
    direction = math.degrees(math.atan2(u, v))
    return (direction + 360) % 360


def wind_components_to_speed(u: float, v: float) -> float:
    """Calculate wind speed from u and v components.
    
    Args:
        u: Eastward wind component (m/s)
        v: Northward wind component (m/s)
        
    Returns:
        Wind speed in m/s
    """
    import math
    return math.sqrt(u**2 + v**2)


def direction_to_components(direction_deg: float, speed_ms: float) -> tuple:
    """Calculate u and v wind components from direction and speed.
    
    Args:
        direction_deg: Wind direction in degrees (0-360, where 0 is north)
        speed_ms: Wind speed in m/s
        
    Returns:
        Tuple of (u, v) components in m/s
    """
    import math
    # Meteorological convention: direction is where wind comes FROM
    # u = east component, v = north component
    angle_rad = degrees_to_radians(direction_deg)
    u = -speed_ms * math.sin(angle_rad)
    v = -speed_ms * math.cos(angle_rad)
    return (u, v)


def mixing_ratio_to_dew_point(mixing_ratio: float, pressure_pa: float) -> float:
    """Calculate dew point temperature from mixing ratio and pressure.
    
    Args:
        mixing_ratio: Mixing ratio in kg/kg
        pressure_pa: Pressure in Pa
        
    Returns:
        Dew point temperature in Celsius
    """
    import math
    
    # Magnus formula constants
    A = 611.21  # Pa
    B = 17.368
    C = 238.3   # K
    
    # Calculate vapor pressure from mixing ratio
    e = (mixing_ratio * pressure_pa) / (0.622 + mixing_ratio)
    
    # Calculate dew point temperature
    dew_point_k = C / (B / math.log(e / A) - 1)
    
    return kelvin_to_celsius(dew_point_k)


def dew_point_to_mixing_ratio(dew_point_c: float, pressure_pa: float) -> float:
    """Calculate mixing ratio from dew point temperature and pressure.
    
    Args:
        dew_point_c: Dew point temperature in Celsius
        pressure_pa: Pressure in Pa
        
    Returns:
        Mixing ratio in kg/kg
    """
    import math
    
    # Magnus formula constants
    A = 611.21  # Pa
    B = 17.368
    C = 238.3   # K
    
    # Calculate vapor pressure from dew point
    dew_point_k = celsius_to_kelvin(dew_point_c)
    e = A * math.exp(B * dew_point_k / (dew_point_k + C))
    
    # Calculate mixing ratio
    return (0.622 * e) / (pressure_pa - e)


def geopotential_to_height(z: float) -> float:
    """Convert geopotential to geometric height.
    
    Args:
        z: Geopotential in m²/s²
        
    Returns:
        Height in meters
    """
    g = 9.80665  # Standard gravity in m/s²
    return z / g


def height_to_geopotential(height_m: float) -> float:
    """Convert geometric height to geopotential.
    
    Args:
        height_m: Height in meters
        
    Returns:
        Geopotential in m²/s²
    """
    g = 9.80665  # Standard gravity in m/s²
    return height_m * g
