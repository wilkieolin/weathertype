"""Hodogram calculations for meteorological analysis."""

from typing import List, Optional, Tuple
import math

from weathertype.utils.units import (
    kmh_to_ms,
    ms_to_kmh,
    degrees_to_radians,
    radians_to_degrees,
    wind_components_to_speed,
    wind_components_to_direction,
    direction_to_components
)


def calculate_wind_components(
    wind_speed_kmh: float,
    wind_direction_deg: int
) -> Tuple[float, float]:
    """Calculate u and v wind components from speed and direction.
    
    Args:
        wind_speed_kmh: Wind speed in km/h
        wind_direction_deg: Wind direction in degrees (0-360, where 0 is north)
        
    Returns:
        Tuple of (u, v) components in m/s
        u = eastward component, v = northward component
    """
    speed_ms = kmh_to_ms(wind_speed_kmh)
    return direction_to_components(wind_direction_deg, speed_ms)


def calculate_shear_vector(
    u1: float,
    v1: float,
    u2: float,
    v2: float
) -> Tuple[float, float]:
    """Calculate the shear vector between two wind vectors.
    
    Args:
        u1, v1: First wind component (u, v) in m/s
        u2, v2: Second wind component (u, v) in m/s
        
    Returns:
        Tuple of (shear_u, shear_v) components
    """
    return (u2 - u1, v2 - v1)


def calculate_shear_magnitude(
    u1: float,
    v1: float,
    u2: float,
    v2: float
) -> float:
    """Calculate the magnitude of wind shear between two vectors.
    
    Args:
        u1, v1: First wind component (u, v) in m/s
        u2, v2: Second wind component (u, v) in m/s
        
    Returns:
        Shear magnitude in m/s
    """
    du = u2 - u1
    dv = v2 - v1
    return math.sqrt(du**2 + dv**2)


def calculate_bulk_shear(
    wind_speeds: List[float],
    wind_directions: List[int],
    pressure_levels: List[float],
    lower_level_hpa: float = 0.0,
    upper_level_hpa: float = 6000.0
) -> float:
    """Calculate bulk wind shear between two pressure levels.
    
    Args:
        wind_speeds: List of wind speeds in km/h
        wind_directions: List of wind directions in degrees
        pressure_levels: List of pressure levels in hPa
        lower_level_hpa: Lower level pressure in hPa (default: surface)
        upper_level_hpa: Upper level pressure in hPa (default: 6000 m height equivalent)
        
    Returns:
        Bulk shear magnitude in m/s
    """
    if len(wind_speeds) != len(wind_directions):
        raise ValueError("Wind speeds and directions must have same length")
    
    # Find closest indices for lower (high pressure) and upper (low pressure) levels
    lower_idx = None
    upper_idx = None

    for i, p in enumerate(pressure_levels):
        if lower_idx is None or abs(p - lower_level_hpa) < abs(pressure_levels[lower_idx] - lower_level_hpa):
            lower_idx = i
        if upper_idx is None or abs(p - upper_level_hpa) < abs(pressure_levels[upper_idx] - upper_level_hpa):
            upper_idx = i

    if lower_idx is None or upper_idx is None or lower_idx == upper_idx:
        return 0.0
    
    # Calculate components at both levels
    u_lower, v_lower = calculate_wind_components(
        wind_speeds[lower_idx], wind_directions[lower_idx]
    )
    u_upper, v_upper = calculate_wind_components(
        wind_speeds[upper_idx], wind_directions[upper_idx]
    )
    
    return calculate_shear_magnitude(u_lower, v_lower, u_upper, v_upper)


def calculate_storm_relative_hodograph(
    wind_speeds: List[float],
    wind_directions: List[int],
    mean_wind_u: float,
    mean_wind_v: float
) -> Tuple[List[float], List[float]]:
    """Calculate storm-relative hodograph.
    
    Args:
        wind_speeds: List of wind speeds in km/h
        wind_directions: List of wind directions in degrees
        mean_wind_u: Mean wind u component in m/s
        mean_wind_v: Mean wind v component in m/s
        
    Returns:
        Tuple of (u_sr, v_sr) storm-relative components
    """
    u_sr = []
    v_sr = []
    
    for speed, direction in zip(wind_speeds, wind_directions):
        u, v = calculate_wind_components(speed, direction)
        u_sr.append(u - mean_wind_u)
        v_sr.append(v - mean_wind_v)
    
    return (u_sr, v_sr)


def calculate_mean_wind(
    wind_speeds: List[float],
    wind_directions: List[int],
    weights: Optional[List[float]] = None
) -> Tuple[float, float]:
    """Calculate the weighted mean wind vector.
    
    Args:
        wind_speeds: List of wind speeds in km/h
        wind_directions: List of wind directions in degrees
        weights: Optional list of weights for each level
        
    Returns:
        Tuple of (mean_u, mean_v) in m/s
    """
    if len(wind_speeds) != len(wind_directions):
        raise ValueError("Wind speeds and directions must have same length")
    
    n = len(wind_speeds)
    if weights is None:
        weights = [1.0] * n
    
    total_weight = sum(weights)
    
    mean_u = 0.0
    mean_v = 0.0
    
    for speed, direction, weight in zip(wind_speeds, wind_directions, weights):
        u, v = calculate_wind_components(speed, direction)
        mean_u += u * weight
        mean_v += v * weight
    
    return (mean_u / total_weight, mean_v / total_weight)


def calculate_wind_speed_at_level(
    pressure_hpa: float,
    reference_pressure_hpa: float = 1000.0,
    reference_speed_kmh: float = 10.0,
    exponent: float = 1.0/7.0
) -> float:
    """Estimate wind speed at a given pressure level using power law.
    
    Args:
        pressure_hpa: Pressure level in hPa
        reference_pressure_hpa: Reference pressure (surface) in hPa
        reference_speed_kmh: Reference wind speed at surface in km/h
        exponent: Power law exponent (default: 1/7)
        
    Returns:
        Estimated wind speed in km/h
    """
    ratio = pressure_hpa / reference_pressure_hpa
    return reference_speed_kmh * (ratio ** exponent)


def calculate_circulation(
    u_components: List[float],
    v_components: List[float]
) -> float:
    """Calculate the circulation around a hodograph loop.
    
    Uses the trapezoidal rule to integrate around the closed curve.
    
    Args:
        u_components: List of u components
        v_components: List of v components
        
    Returns:
        Circulation in (m/s)²
    """
    if len(u_components) != len(v_components):
        raise ValueError("U and V components must have same length")
    
    n = len(u_components)
    circulation = 0.0
    
    for i in range(n):
        j = (i + 1) % n
        # Trapezoidal rule: (u_i * v_j - u_j * v_i) / 2
        circulation += u_components[i] * v_components[j] - u_components[j] * v_components[i]
    
    return circulation / 2.0
