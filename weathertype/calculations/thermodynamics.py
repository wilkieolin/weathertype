"""Thermodynamic calculations for meteorological analysis."""

import math
from typing import List, Tuple, Optional

from weathertype.utils.units import (
    celsius_to_kelvin,
    kelvin_to_celsius,
    hpa_to_pa,
    pa_to_hpa
)


# Constants
GAS_CONSTANT_AIR = 287.058  # J/(kg·K)
GRAVITY = 9.80665         # m/s²
CP_DRY_AIR = 1004.6       # J/(kg·K)
CV_DRY_AIR = 717.1        # J/(kg·K)
RATIO_CP_CV = CP_DRY_AIR / CV_DRY_AIR
LATENT_HEAT_VAPORIZATION = 2.5e6  # J/kg

# Magnus formula constants for water vapor
MAGNUS_A = 611.21  # Pa
MAGNUS_B = 17.368
MAGNUS_C = 238.3   # K


def calculate_potential_temperature(
    temperature_c: float,
    pressure_hpa: float,
    reference_pressure_hpa: float = 1000.0
) -> float:
    """Calculate potential temperature (θ).
    
    Potential temperature is the temperature a parcel of air would have 
    if brought adiabatically to a reference pressure (usually 1000 hPa).
    
    Args:
        temperature_c: Temperature in Celsius
        pressure_hpa: Pressure in hPa
        reference_pressure_hpa: Reference pressure in hPa
        
    Returns:
        Potential temperature in Celsius
    """
    temp_k = celsius_to_kelvin(temperature_c)

    # Poisson's equation: θ = T * (p_ref / p)^(R/Cp)
    kappa = GAS_CONSTANT_AIR / CP_DRY_AIR  # ≈ 0.286
    theta_k = temp_k * (reference_pressure_hpa / pressure_hpa) ** kappa

    return kelvin_to_celsius(theta_k)


def calculate_equivalent_potential_temperature(
    temperature_c: float,
    dew_point_c: float,
    pressure_hpa: float,
    reference_pressure_hpa: float = 1000.0
) -> float:
    """Calculate equivalent potential temperature (θe).
    
    θe is the potential temperature a parcel would have after all 
    moisture has been condensed and removed.
    
    Args:
        temperature_c: Temperature in Celsius
        dew_point_c: Dew point temperature in Celsius
        pressure_hpa: Pressure in hPa
        reference_pressure_hpa: Reference pressure in hPa
        
    Returns:
        Equivalent potential temperature in Celsius
    """
    temp_k = celsius_to_kelvin(temperature_c)

    # Mixing ratio from dew point (use corrected Magnus with °C)
    e = MAGNUS_A * math.exp(MAGNUS_B * dew_point_c / (dew_point_c + MAGNUS_C))
    p_pa = hpa_to_pa(pressure_hpa)
    mixing_ratio = 0.622 * e / (p_pa - e)  # kg/kg

    # Bolton (1980) approximation for θe
    kappa = GAS_CONSTANT_AIR / CP_DRY_AIR
    theta_k = temp_k * (reference_pressure_hpa / pressure_hpa) ** kappa
    theta_e_k = theta_k * math.exp(
        (LATENT_HEAT_VAPORIZATION * mixing_ratio) / (CP_DRY_AIR * temp_k)
    )

    return kelvin_to_celsius(theta_e_k)


def calculate_lcl(
    temperature_c: float,
    dew_point_c: float,
    pressure_hpa: float
) -> Tuple[float, float]:
    """Calculate the Lifting Condensation Level (LCL).
    
    The LCL is the height at which a parcel of air becomes saturated 
    when lifted dry adiabatically.
    
    Args:
        temperature_c: Temperature in Celsius
        dew_point_c: Dew point temperature in Celsius
        pressure_hpa: Pressure in hPa
        
    Returns:
        Tuple of (LCL height in meters, LCL pressure in hPa)
    """
    # Approximate formula for LCL
    # LCL height (meters) ≈ 125 * (T - Td)
    height_m = 125.0 * (temperature_c - dew_point_c)
    
    # LCL pressure approximation (hPa)
    # Using barometric formula
    surface_k = celsius_to_kelvin(temperature_c)
    lapse_rate = 6.5 / 1000  # K/m
    
    # Iterative calculation for LCL pressure
    p_lcl = pressure_hpa
    temp_k = surface_k
    
    for _ in range(10):  # Iterate to converge
        height_m = 125.0 * (kelvin_to_celsius(temp_k) - dew_point_c)
        if height_m <= 0:
            break
        p_lcl = pressure_hpa * (1 - lapse_rate * height_m / temp_k) ** 5.256
        temp_k = surface_k - lapse_rate * height_m
    
    return (height_m, max(p_lcl, 100.0))


def calculate_cape_cin(
    temperatures: List[float],
    dew_points: List[float],
    pressures: List[float]
) -> Tuple[float, float]:
    """Calculate Convective Available Potential Energy (CAPE) and 
    Convective Inhibition (CIN).
    
    Args:
        temperatures: Temperature profile in Celsius
        dew_points: Dew point profile in Celsius
        pressures: Pressure profile in hPa
        
    Returns:
        Tuple of (CAPE in J/kg, CIN in J/kg)
    """
    if len(temperatures) != len(dew_points) or len(dew_points) != len(pressures):
        raise ValueError("All input arrays must have the same length")
    
    n = len(temperatures)

    # Surface parcel
    sfc_t = temperatures[0]
    sfc_td = dew_points[0]
    sfc_p = pressures[0]

    # Lift parcel dry-adiabatically to LCL, then moist-adiabatically above
    _, lcl_pressure = calculate_lcl(sfc_t, sfc_td, sfc_p)

    kappa = GAS_CONSTANT_AIR / CP_DRY_AIR
    parcel_t_k = celsius_to_kelvin(sfc_t)

    cape = 0.0
    cin = 0.0

    for i in range(1, n):
        p = pressures[i]
        env_t_k = celsius_to_kelvin(temperatures[i])

        if p >= lcl_pressure:
            # Below LCL: dry adiabatic
            parcel_t_k_here = celsius_to_kelvin(sfc_t) * (p / sfc_p) ** kappa
        else:
            # Above LCL: approximate moist adiabatic (~6 K/km)
            # Use pseudo-adiabatic lapse rate approximation
            dp_hpa = pressures[i - 1] - p
            dz = dp_hpa * 8.5  # rough m per hPa
            parcel_t_k -= 6.0 * (dz / 1000.0)
            parcel_t_k_here = parcel_t_k

        # Layer depth in terms of pressure (integrate using Rd*T*dln(p))
        dlnp = math.log(pressures[i - 1] / p)
        energy = GAS_CONSTANT_AIR * (parcel_t_k_here - env_t_k) * dlnp

        if energy > 0:
            cape += energy
        else:
            cin += energy  # CIN is negative

    return (max(cape, 0.0), min(cin, 0.0))


def calculate_virtual_temperature(
    temperature_c: float,
    mixing_ratio_kgkg: float
) -> float:
    """Calculate virtual temperature.
    
    Virtual temperature is the temperature at which dry air would have 
    the same density as moist air at the actual temperature.
    
    Args:
        temperature_c: Temperature in Celsius
        mixing_ratio_kgkg: Mixing ratio in kg/kg
        
    Returns:
        Virtual temperature in Celsius
    """
    temp_k = celsius_to_kelvin(temperature_c)
    tv_k = temp_k * (1 + 0.61 * mixing_ratio_kgkg)
    return kelvin_to_celsius(tv_k)


def calculate_saturation_vapor_pressure(temperature_c: float) -> float:
    """Calculate saturation vapor pressure over water (Magnus formula).

    Args:
        temperature_c: Temperature in Celsius

    Returns:
        Saturation vapor pressure in hPa
    """
    # Magnus formula uses °C directly (constants calibrated for °C)
    e_sat_pa = MAGNUS_A * math.exp(
        (MAGNUS_B * temperature_c) / (temperature_c + MAGNUS_C)
    )

    return pa_to_hpa(e_sat_pa)


def calculate_relative_humidity(
    temperature_c: float,
    dew_point_c: float
) -> float:
    """Calculate relative humidity.
    
    Args:
        temperature_c: Temperature in Celsius
        dew_point_c: Dew point temperature in Celsius
        
    Returns:
        Relative humidity as a percentage (0-100)
    """
    e_sat_temp = calculate_saturation_vapor_pressure(temperature_c)
    e_sat_dp = calculate_saturation_vapor_pressure(dew_point_c)
    
    # At dew point, relative humidity is 100%, so we can calculate
    # actual vapor pressure from the saturation vapor pressure at dew point
    rh_percent = (e_sat_dp / e_sat_temp) * 100
    
    return max(0.0, min(100.0, rh_percent))


def calculate_dew_point_from_rh(
    temperature_c: float,
    relative_humidity_percent: float
) -> float:
    """Calculate dew point temperature from relative humidity.
    
    Args:
        temperature_c: Temperature in Celsius
        relative_humidity_percent: Relative humidity as percentage (0-100)
        
    Returns:
        Dew point temperature in Celsius
    """
    # Invert Magnus formula
    e_sat = calculate_saturation_vapor_pressure(temperature_c)
    e_actual = (relative_humidity_percent / 100.0) * e_sat
    
    # Solve for Td in Magnus formula
    # e = A * exp(B * Td / (Td + C))
    # ln(e/A) = B * Td / (Td + C)
    # ln(e/A) * (Td + C) = B * Td
    # ln(e/A) * Td + ln(e/A) * C = B * Td
    # Td * (B - ln(e/A)) = C * ln(e/A)
    # Td = C * ln(e/A) / (B - ln(e/A))
    
    import math
    ratio = e_actual / MAGNUS_A
    if ratio <= 0:
        return -273.15  # Absolute zero
    
    ln_ratio = math.log(ratio)
    td_k = MAGNUS_C * ln_ratio / (MAGNUS_B - ln_ratio)
    
    return kelvin_to_celsius(td_k)


def calculate_mixing_ratio(
    dew_point_c: float,
    pressure_hpa: float
) -> float:
    """Calculate mixing ratio from dew point and pressure.
    
    Args:
        dew_point_c: Dew point temperature in Celsius
        pressure_hpa: Pressure in hPa
        
    Returns:
        Mixing ratio in kg/kg
    """
    # At the dew point, actual vapor pressure = saturation vapor pressure
    e_hpa = calculate_saturation_vapor_pressure(dew_point_c)

    # Mixing ratio: w = 0.622 * e / (p - e)
    mixing_ratio = 0.622 * e_hpa / (pressure_hpa - e_hpa)

    return max(mixing_ratio, 0.0)


def calculate_adiabatic_lapse_rate(
    temperature_c: float,
    pressure_hpa: float,
    is_moist: bool = False
) -> float:
    """Calculate the adiabatic lapse rate.
    
    Args:
        temperature_c: Temperature in Celsius
        pressure_hpa: Pressure in hPa
        is_moist: Whether to calculate moist adiabatic lapse rate
        
    Returns:
        Lapse rate in K/km
    """
    temp_k = celsius_to_kelvin(temperature_c)
    
    if is_moist:
        # Moist adiabatic lapse rate (approximate)
        # Depends on temperature and pressure
        latent_heat = 2.5e6  # J/kg
        mixing_ratio = calculate_mixing_ratio(temperature_c, pressure_hpa)
        
        term1 = CP_DRY_AIR + (latent_heat ** 2 * mixing_ratio) / (GAS_CONSTANT_AIR * temp_k)
        term2 = CP_DRY_AIR + (latent_heat * mixing_ratio) / GAS_CONSTANT_AIR
        moist_lapse_rate = (GRAVITY / temp_k) * (term1 / term2) * 1000  # K/km
        
        return moist_lapse_rate
    else:
        # Dry adiabatic lapse rate
        return (GRAVITY / CP_DRY_AIR) * 1000  # ~9.8 K/km


def calculate_height_from_pressure(
    pressure_hpa: float,
    surface_pressure_hpa: float = 1013.25,
    surface_temp_c: float = 15.0
) -> float:
    """Calculate geometric height from pressure using barometric formula.
    
    Args:
        pressure_hpa: Pressure at desired height in hPa
        surface_pressure_hpa: Surface pressure in hPa (default: standard atmosphere)
        surface_temp_c: Surface temperature in Celsius (default: 15°C)
        
    Returns:
        Height above sea level in meters
    """
    temp_k = celsius_to_kelvin(surface_temp_c)
    
    # Barometric formula for height
    # h = (T0 / L) * [1 - (P/P0)^(R*L/g)]
    lapse_rate = 6.5 / 1000  # K/m
    
    ratio = pressure_hpa / surface_pressure_hpa
    height_m = (temp_k / lapse_rate) * (1 - ratio ** (GAS_CONSTANT_AIR * lapse_rate / GRAVITY))
    
    return max(0.0, height_m)
