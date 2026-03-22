"""View classes wrapping each plotter for curses display."""

import curses
import io
import sys

from weathertype.api.models import WeatherProfile, ForecastData, RegionalGrid, RadarData
from weathertype.visualizations.skewt import SkewTPlotter
from weathertype.visualizations.hodogram import HodogramPlotter
from weathertype.visualizations.meteograph import MeteographPlotter
from weathertype.visualizations.forecast import ForecastPlotter
from weathertype.visualizations.regional_temp import RegionalTempPlotter
from weathertype.visualizations.regional_pressure import RegionalPressurePlotter
from weathertype.visualizations.radar import RadarPlotter
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
from weathertype.tui.ansi_parser import render_to_pad


class View:
    """Base class for TUI views."""

    name: str = ""
    shortcut: str = ""

    def __init__(self):
        self._profile: WeatherProfile | None = None
        self._forecast: ForecastData | None = None
        self._regional_temp: RegionalGrid | None = None
        self._regional_pressure: RegionalGrid | None = None
        self._radar: RadarData | None = None

    def update_data(
        self,
        profile: WeatherProfile | None,
        forecast: ForecastData | None,
        **kwargs,
    ) -> None:
        self._profile = profile
        self._forecast = forecast
        self._regional_temp = kwargs.get("regional_temp")
        self._regional_pressure = kwargs.get("regional_pressure")
        self._radar = kwargs.get("radar")

    def render(self, pad: curses.window, width: int, height: int) -> int:
        """Render into pad. Returns content height (for scroll bounds)."""
        raise NotImplementedError


class SkewTView(View):
    name = "Skew-T"
    shortcut = "1"

    def render(self, pad, width, height):
        if self._profile is None:
            return 0
        p = self._profile
        # Leave room for title/legend lines the plotter adds
        plot_h = max(15, height - 5)
        plot_w = max(40, width - 2)
        plotter = SkewTPlotter(width=plot_w, height=plot_h)
        text = plotter.plot_full_skewt(p.temperatures, p.dew_points, p.pressure_levels)
        return render_to_pad(pad, text)


class HodogramView(View):
    name = "Hodogram"
    shortcut = "2"

    def render(self, pad, width, height):
        if self._profile is None:
            return 0
        p = self._profile
        # Hodogram is square, fit to smaller dimension
        size = min(width - 4, height - 10)
        size = max(15, size)
        size = size | 1  # must be odd
        plotter = HodogramPlotter(size=size)
        text = plotter.plot_hodogram(p.wind_speeds, p.wind_directions, p.pressure_levels)
        return render_to_pad(pad, text)


class MeteographView(View):
    name = "Meteograph"
    shortcut = "3"

    def render(self, pad, width, height):
        if self._profile is None:
            return 0
        p = self._profile
        # Meteograph renders two stacked panels
        plot_h = max(12, (height - 10) // 2)
        plot_w = max(40, width - 2)
        plotter = MeteographPlotter(width=plot_w, height=plot_h)
        text = plotter.plot_full_meteograph(
            p.temperatures, p.dew_points, p.wind_speeds, p.pressure_levels
        )
        return render_to_pad(pad, text)


class ForecastView(View):
    name = "Forecast"
    shortcut = "4"

    def render(self, pad, width, height):
        if self._forecast is None:
            return 0
        plot_w = max(40, width - 2)
        plotter = ForecastPlotter(width=plot_w)
        text = plotter.plot_forecast(self._forecast)
        return render_to_pad(pad, text)


class SummaryView(View):
    name = "Summary"
    shortcut = "5"

    def render(self, pad, width, height):
        if self._profile is None:
            return 0
        p = self._profile
        lines = []
        lines.append("-" * 40)
        lines.append("KEY PARAMETERS")
        lines.append("-" * 40)

        sfc_idx = 0
        sfc_temp = p.temperatures[sfc_idx]
        sfc_dp = p.dew_points[sfc_idx]
        sfc_p = p.pressure_levels[sfc_idx]
        sfc_ws = p.wind_speeds[sfc_idx]
        sfc_wd = p.wind_directions[sfc_idx]

        lines.append(f"  Surface ({sfc_p:.0f} hPa):")
        lines.append(f"    Temperature:  {sfc_temp:.1f} C")
        lines.append(f"    Dew point:    {sfc_dp:.1f} C")
        lines.append(f"    RH:           {calculate_relative_humidity(sfc_temp, sfc_dp):.0f}%")
        lines.append(f"    Wind:         {sfc_ws:.0f} km/h from {sfc_wd:03d}")

        lcl_height, lcl_pressure = calculate_lcl(sfc_temp, sfc_dp, sfc_p)
        lines.append(f"  LCL:            {lcl_height:.0f} m ({lcl_pressure:.0f} hPa)")

        theta = calculate_potential_temperature(sfc_temp, sfc_p)
        lines.append(f"  Theta (sfc):    {theta:.1f} C")

        theta_e = calculate_equivalent_potential_temperature(sfc_temp, sfc_dp, sfc_p)
        lines.append(f"  Theta-e (sfc):  {theta_e:.1f} C")

        cape, cin = calculate_cape_cin(p.temperatures, p.dew_points, p.pressure_levels)
        lines.append(f"  CAPE:           {cape:.0f} J/kg")
        lines.append(f"  CIN:            {cin:.0f} J/kg")

        stability = calculate_stability_index(p.temperatures, p.pressure_levels)
        lines.append(f"  Stability:      {stability}")

        inversions = calculate_inversion_layers(p.temperatures, p.pressure_levels)
        if inversions:
            for i, (p_bot, p_top) in enumerate(inversions):
                lines.append(f"  Inversion {i+1}:    {p_bot:.0f} - {p_top:.0f} hPa")
        else:
            lines.append("  Inversions:     None detected")

        shear = calculate_bulk_shear(
            p.wind_speeds, p.wind_directions, p.pressure_levels,
            lower_level_hpa=max(p.pressure_levels),
            upper_level_hpa=min(p.pressure_levels),
        )
        lines.append(f"  Bulk shear:     {shear:.1f} m/s")

        import math
        mean_u, mean_v = calculate_mean_wind(p.wind_speeds, p.wind_directions)
        mean_speed = math.sqrt(mean_u**2 + mean_v**2)
        lines.append(f"  Mean wind:      {mean_speed:.1f} m/s")

        lines.append("")

        # Data table
        lines.append("-" * 70)
        lines.append(f"{'Press (hPa)':>12} {'Temp (C)':>10} {'Dewpt (C)':>11} {'RH (%)':>8} {'Wnd (km/h)':>11} {'Dir':>8}")
        lines.append("-" * 70)
        for i in range(p.num_levels):
            rh = calculate_relative_humidity(p.temperatures[i], p.dew_points[i])
            lines.append(
                f"{p.pressure_levels[i]:>12.0f} {p.temperatures[i]:>10.1f} {p.dew_points[i]:>11.1f} "
                f"{rh:>8.0f} {p.wind_speeds[i]:>11.0f} {p.wind_directions[i]:>8d}"
            )

        text = "\n".join(lines)
        return render_to_pad(pad, text)


class RegionalTempView(View):
    name = "Temp Map"
    shortcut = "6"

    def render(self, pad, width, height):
        if self._regional_temp is None:
            return 0
        plot_w = max(40, width - 2)
        plotter = RegionalTempPlotter(width=plot_w)
        text = plotter.plot_temperature_map(self._regional_temp)
        return render_to_pad(pad, text)


class RegionalPressureView(View):
    name = "Pres Map"
    shortcut = "7"

    def render(self, pad, width, height):
        if self._regional_pressure is None:
            return 0
        plot_w = max(40, width - 2)
        plotter = RegionalPressurePlotter(width=plot_w)
        text = plotter.plot_pressure_map(self._regional_pressure)
        return render_to_pad(pad, text)


class RadarView(View):
    name = "Radar"
    shortcut = "8"

    def render(self, pad, width, height):
        if self._radar is None:
            return 0
        plot_w = max(40, width - 2)
        plot_h = max(15, height - 8)
        plotter = RadarPlotter(width=plot_w, height=plot_h)
        text = plotter.plot_radar(self._radar)
        return render_to_pad(pad, text)
