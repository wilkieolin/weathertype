"""CLI entry point for weathertype."""

import argparse
import sys

from weathertype.api.open_meteo import OpenMeteoClient
from weathertype.api.models import WeatherProfile
from weathertype.utils.coordinates import geocode_location, validate_coordinates
from weathertype.calculations.thermodynamics import (
    calculate_lcl,
    calculate_cape_cin,
    calculate_potential_temperature,
    calculate_equivalent_potential_temperature,
    calculate_relative_humidity,
)
from weathertype.calculations.hodogram import (
    calculate_mean_wind,
    calculate_bulk_shear,
)
from weathertype.calculations.meteograph import (
    calculate_stability_index,
    calculate_inversion_layers,
)
from weathertype.visualizations.skewt import SkewTPlotter
from weathertype.visualizations.hodogram import HodogramPlotter
from weathertype.visualizations.meteograph import MeteographPlotter
from weathertype.visualizations.forecast import ForecastPlotter


def print_header(profile: WeatherProfile, location_name: str = "") -> None:
    """Print the weather profile header."""
    print("=" * 70)
    print("WEATHERTYPE - Terminal Weather Visualization")
    print("=" * 70)
    if location_name:
        print(f"  Location: {location_name}")
    print(f"  Coordinates: {profile.latitude:.4f}°N, {profile.longitude:.4f}°E")
    print(f"  Elevation: {profile.elevation:.0f} m")
    if profile.time:
        print(f"  Forecast time: {profile.time}")
    print(f"  Pressure levels: {profile.num_levels} ({max(profile.pressure_levels):.0f} - {min(profile.pressure_levels):.0f} hPa)")
    print("=" * 70)
    print()


def print_summary(profile: WeatherProfile) -> None:
    """Print a text summary of key meteorological parameters."""
    print("-" * 40)
    print("KEY PARAMETERS")
    print("-" * 40)

    # Surface conditions (highest pressure level)
    sfc_idx = 0  # First level is highest pressure (surface)
    sfc_temp = profile.temperatures[sfc_idx]
    sfc_dp = profile.dew_points[sfc_idx]
    sfc_p = profile.pressure_levels[sfc_idx]
    sfc_ws = profile.wind_speeds[sfc_idx]
    sfc_wd = profile.wind_directions[sfc_idx]

    print(f"  Surface ({sfc_p:.0f} hPa):")
    print(f"    Temperature:  {sfc_temp:.1f} °C")
    print(f"    Dew point:    {sfc_dp:.1f} °C")
    print(f"    RH:           {calculate_relative_humidity(sfc_temp, sfc_dp):.0f}%")
    print(f"    Wind:         {sfc_ws:.0f} km/h from {sfc_wd:03d}°")

    # LCL
    lcl_height, lcl_pressure = calculate_lcl(sfc_temp, sfc_dp, sfc_p)
    print(f"  LCL:            {lcl_height:.0f} m ({lcl_pressure:.0f} hPa)")

    # Potential temperature
    theta = calculate_potential_temperature(sfc_temp, sfc_p)
    print(f"  θ (surface):    {theta:.1f} °C")

    # Equivalent potential temperature
    theta_e = calculate_equivalent_potential_temperature(sfc_temp, sfc_dp, sfc_p)
    print(f"  θe (surface):   {theta_e:.1f} °C")

    # CAPE/CIN
    cape, cin = calculate_cape_cin(
        profile.temperatures, profile.dew_points, profile.pressure_levels
    )
    print(f"  CAPE:           {cape:.0f} J/kg")
    print(f"  CIN:            {cin:.0f} J/kg")

    # Stability
    stability = calculate_stability_index(profile.temperatures, profile.pressure_levels)
    print(f"  Stability:      {stability}")

    # Inversions
    inversions = calculate_inversion_layers(profile.temperatures, profile.pressure_levels)
    if inversions:
        for i, (p_bot, p_top) in enumerate(inversions):
            print(f"  Inversion {i+1}:    {p_bot:.0f} - {p_top:.0f} hPa")
    else:
        print("  Inversions:     None detected")

    # Bulk shear
    shear = calculate_bulk_shear(
        profile.wind_speeds,
        profile.wind_directions,
        profile.pressure_levels,
        lower_level_hpa=max(profile.pressure_levels),
        upper_level_hpa=min(profile.pressure_levels),
    )
    print(f"  Bulk shear:     {shear:.1f} m/s")

    # Mean wind
    mean_u, mean_v = calculate_mean_wind(profile.wind_speeds, profile.wind_directions)
    import math
    mean_speed = math.sqrt(mean_u**2 + mean_v**2)
    print(f"  Mean wind:      {mean_speed:.1f} m/s")

    print()


def print_data_table(profile: WeatherProfile) -> None:
    """Print a tabular view of the profile data."""
    print("-" * 70)
    print(f"{'Press (hPa)':>12} {'Temp (°C)':>10} {'Dewpt (°C)':>11} {'RH (%)':>8} {'Wnd (km/h)':>11} {'Dir (°)':>8}")
    print("-" * 70)

    for i in range(profile.num_levels):
        p = profile.pressure_levels[i]
        t = profile.temperatures[i]
        td = profile.dew_points[i]
        rh = calculate_relative_humidity(t, td)
        ws = profile.wind_speeds[i]
        wd = profile.wind_directions[i]
        print(f"{p:>12.0f} {t:>10.1f} {td:>11.1f} {rh:>8.0f} {ws:>11.0f} {wd:>8d}")

    print()


def run_skewt(profile: WeatherProfile) -> None:
    """Display the Skew-T diagram."""
    plotter = SkewTPlotter()
    print(plotter.plot_full_skewt(
        profile.temperatures,
        profile.dew_points,
        profile.pressure_levels,
    ))
    print()


def run_hodogram(profile: WeatherProfile) -> None:
    """Display the hodogram."""
    plotter = HodogramPlotter()
    print(plotter.plot_hodogram(
        profile.wind_speeds,
        profile.wind_directions,
        profile.pressure_levels,
    ))
    print()


def run_meteograph(profile: WeatherProfile) -> None:
    """Display the meteograph."""
    plotter = MeteographPlotter()
    print(plotter.plot_full_meteograph(
        profile.temperatures,
        profile.dew_points,
        profile.wind_speeds,
        profile.pressure_levels,
    ))
    print()


def run_forecast(latitude: float, longitude: float, location_name: str) -> None:
    """Fetch and display the 36-hour forecast."""
    print(f"Fetching 36-hour forecast for {location_name}...")
    client = OpenMeteoClient()
    response = client.get_forecast_data(latitude, longitude, hours=36)

    if response.error:
        print(f"Error: {response.error}", file=sys.stderr)
        return

    forecast = response.forecast
    if forecast is None or forecast.num_hours == 0:
        print("Error: No forecast data available", file=sys.stderr)
        return

    plotter = ForecastPlotter()
    print(plotter.plot_forecast(forecast))
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weathertype",
        description="Terminal weather visualization: Skew-T, hodogram, and meteograph displays",
    )

    location = parser.add_argument_group("location")
    location.add_argument(
        "--location", "-l",
        type=str,
        help="City name (e.g. 'Chicago, IL')",
    )
    location.add_argument("--lat", type=float, help="Latitude")
    location.add_argument("--lon", type=float, help="Longitude")

    display = parser.add_argument_group("display")
    display.add_argument(
        "--skewt", action="store_true", help="Show Skew-T diagram"
    )
    display.add_argument(
        "--hodogram", action="store_true", help="Show hodogram"
    )
    display.add_argument(
        "--meteograph", action="store_true", help="Show meteograph"
    )
    display.add_argument(
        "--summary", action="store_true", help="Show key parameters summary"
    )
    display.add_argument(
        "--table", action="store_true", help="Show data table"
    )
    display.add_argument(
        "--forecast", action="store_true", help="Show 36-hour forecast"
    )
    display.add_argument(
        "--all", "-a", action="store_true", help="Show all visualizations"
    )

    parser.add_argument(
        "--hour", type=int, default=None,
        help="Forecast hour (0-23, default: current hour)",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable colored output",
    )

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Handle --no-color before any imports that read the env var
    if args.no_color:
        import os
        os.environ["NO_COLOR"] = "1"
        # Re-set the flag in the colors module
        import weathertype.utils.colors as _colors
        _colors._COLORS_ON = False

    # Resolve location
    latitude = None
    longitude = None
    location_name = ""

    if args.location:
        result = geocode_location(args.location)
        if result is None:
            print(f"Error: Could not find location '{args.location}'", file=sys.stderr)
            return 1
        latitude, longitude, location_name = result
    elif args.lat is not None and args.lon is not None:
        latitude = args.lat
        longitude = args.lon
        if not validate_coordinates(latitude, longitude):
            print(f"Error: Invalid coordinates ({latitude}, {longitude})", file=sys.stderr)
            return 1
        location_name = f"{latitude:.4f}°N, {longitude:.4f}°E"
    else:
        parser.print_help()
        print("\nError: Specify --location or --lat/--lon", file=sys.stderr)
        return 1

    # If no display flags given, show all
    show_all = args.all or not any([args.skewt, args.hodogram, args.meteograph, args.summary, args.table, args.forecast])

    # Fetch data
    print(f"Fetching weather data for {location_name}...")
    client = OpenMeteoClient()
    response = client.get_weather_profile(latitude, longitude, forecast_hour=args.hour)

    if response.error:
        print(f"Error: {response.error}", file=sys.stderr)
        return 1

    profile = response.profile
    if profile is None or profile.num_levels == 0:
        print("Error: No weather data available for this location", file=sys.stderr)
        return 1

    print()

    # Display
    print_header(profile, location_name)

    if show_all or args.summary:
        print_summary(profile)

    if show_all or args.table:
        print_data_table(profile)

    if show_all or args.skewt:
        run_skewt(profile)

    if show_all or args.hodogram:
        run_hodogram(profile)

    if show_all or args.meteograph:
        run_meteograph(profile)

    if show_all or args.forecast:
        run_forecast(latitude, longitude, location_name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
