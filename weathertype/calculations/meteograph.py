"""Meteograph data processing and calculations."""

from typing import List, Tuple, Optional

from weathertype.utils.units import kmh_to_ms


def calculate_temperature_profile(
    temperatures: List[float],
    pressure_levels: List[float]
) -> Tuple[List[float], List[float]]:
    """Prepare temperature profile data for meteograph display.
    
    Args:
        temperatures: Temperature values in Celsius
        pressure_levels: Corresponding pressure levels in hPa
        
    Returns:
        Tuple of (temperatures, pressures) for plotting
    """
    return (temperatures, pressure_levels)


def calculate_dew_point_profile(
    dew_points: List[float],
    pressure_levels: List[float]
) -> Tuple[List[float], List[float]]:
    """Prepare dew point profile data for meteograph display.
    
    Args:
        dew_points: Dew point values in Celsius
        pressure_levels: Corresponding pressure levels in hPa
        
    Returns:
        Tuple of (dew_points, pressures) for plotting
    """
    return (dew_points, pressure_levels)


def calculate_wind_profile(
    wind_speeds: List[float],
    wind_directions: List[int],
    pressure_levels: List[float]
) -> Tuple[List[float], List[float], List[float]]:
    """Prepare wind profile data for meteograph display.
    
    Args:
        wind_speeds: Wind speeds in km/h
        wind_directions: Wind directions in degrees (0-360)
        pressure_levels: Corresponding pressure levels in hPa
        
    Returns:
        Tuple of (speeds_ms, directions_deg, pressures) for plotting
    """
    speeds_ms = [kmh_to_ms(s) for s in wind_speeds]
    return (speeds_ms, wind_directions, pressure_levels)


def calculate_lapse_rate(
    temperatures: List[float],
    pressure_levels: List[float]
) -> Tuple[List[float], List[float]]:
    """Calculate environmental lapse rate.
    
    Args:
        temperatures: Temperature values in Celsius
        pressure_levels: Corresponding pressure levels in hPa
        
    Returns:
        Tuple of (lapse_rates, pressures) for plotting
    """
    if len(temperatures) < 2 or len(pressure_levels) < 2:
        return ([], [])
    
    lapse_rates = []
    pressures_out = []
    
    # Convert to height using barometric formula
    heights = []
    for p in pressure_levels:
        # Approximate height from pressure (hypsometric equation)
        h = 15000 * (1 - (p / 1013.25) ** 0.1903)
        heights.append(h)
    
    for i in range(1, len(temperatures)):
        dt = temperatures[i] - temperatures[i-1]
        dh = heights[i] - heights[i-1]
        
        if dh != 0:
            lapse_rate = dt / (dh / 1000)  # K/km
            lapse_rates.append(lapse_rate)
            pressures_out.append(pressure_levels[i])
    
    return (lapse_rates, pressures_out)


def calculate_stability_index(
    temperatures: List[float],
    pressure_levels: List[float]
) -> str:
    """Determine atmospheric stability from temperature profile.
    
    Args:
        temperatures: Temperature values in Celsius
        pressure_levels: Corresponding pressure levels in hPa
        
    Returns:
        Stability classification string
    """
    if len(temperatures) < 2:
        return "Unknown"
    
    # Calculate average lapse rate in troposphere (1000-500 hPa)
    tropospheric_temps = []
    tropospheric_pressures = []
    
    for t, p in zip(temperatures, pressure_levels):
        if 500 <= p <= 1000:
            tropospheric_temps.append(t)
            tropospheric_pressures.append(p)
    
    if len(tropospheric_temps) < 2:
        return "Unknown"
    
    # Calculate lapse rate
    dt = tropospheric_temps[-1] - tropospheric_temps[0]
    dp = tropospheric_pressures[-1] - tropospheric_pressures[0]
    
    if dp == 0:
        return "Neutral"
    
    # Approximate height difference from pressure difference
    dh_km = abs(dp) * 8.5 / 100  # Rough estimate: 8.5 km per 100 hPa
    
    lapse_rate = abs(dt / dh_km) if dh_km > 0 else 0
    
    if lapse_rate > 9.8:
        return "Absolutely Unstable"
    elif lapse_rate > 6.5:
        return "Conditionally Unstable"
    elif lapse_rate > 2:
        return "Stable"
    else:
        return "Very Stable"


def calculate_inversion_layers(
    temperatures: List[float],
    pressure_levels: List[float],
    threshold_kkm: float = 2.0
) -> List[Tuple[float, float]]:
    """Find inversion layers in the temperature profile.
    
    An inversion layer is where temperature increases with height.
    
    Args:
        temperatures: Temperature values in Celsius
        pressure_levels: Corresponding pressure levels in hPa
        threshold_kkm: Minimum lapse rate to qualify as inversion (K/km)
        
    Returns:
        List of (start_pressure, end_pressure) tuples for each inversion layer
    """
    inversions = []
    
    if len(temperatures) < 2 or len(pressure_levels) < 2:
        return inversions
    
    in_inversion = False
    start_pressure = None
    
    for i in range(1, len(temperatures)):
        dt = temperatures[i] - temperatures[i-1]
        
        # Inversion: temperature increases with height (pressure decreases)
        if dt > threshold_kkm:
            if not in_inversion:
                in_inversion = True
                start_pressure = pressure_levels[i-1]
        else:
            if in_inversion:
                in_inversion = False
                inversions.append((start_pressure, pressure_levels[i]))
    
    # Handle case where inversion extends to top of profile
    if in_inversion and start_pressure is not None:
        inversions.append((start_pressure, pressure_levels[-1]))
    
    return inversions


def calculate_mixing_ratio_profile(
    dew_points: List[float],
    pressure_levels: List[float]
) -> Tuple[List[float], List[float]]:
    """Calculate mixing ratio profile.
    
    Args:
        dew_points: Dew point temperatures in Celsius
        pressure_levels: Corresponding pressure levels in hPa
        
    Returns:
        Tuple of (mixing_ratios, pressures)
    """
    from weathertype.calculations.thermodynamics import calculate_mixing_ratio
    
    mixing_ratios = []
    
    for dp, p in zip(dew_points, pressure_levels):
        mr = calculate_mixing_ratio(dp, p)
        mixing_ratios.append(mr)
    
    return (mixing_ratios, pressure_levels)


def calculate_relative_humidity_profile(
    temperatures: List[float],
    dew_points: List[float]
) -> Tuple[List[float], List[float]]:
    """Calculate relative humidity profile.
    
    Args:
        temperatures: Temperature values in Celsius
        dew_points: Dew point temperatures in Celsius
        
    Returns:
        Tuple of (relative humidities, pressures)
    """
    from weathertype.calculations.thermodynamics import calculate_relative_humidity
    
    rh_values = []
    
    for temp, dp in zip(temperatures, dew_points):
        rh = calculate_relative_humidity(temp, dp)
        rh_values.append(rh)
    
    return (rh_values, [])
