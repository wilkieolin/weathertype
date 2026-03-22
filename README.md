# weathertype

Terminal weather visualization tool that displays atmospheric profiles as Skew-T Log-P diagrams, hodograms, and meteographs. Data is fetched from the [Open-Meteo](https://open-meteo.com/) API.

## Features

- **Skew-T Log-P diagram** -- temperature and dew point profiles with dry adiabats and isotherms
- **Hodogram** -- wind profile with altitude-colored segments and speed rings
- **Meteograph** -- vertical profiles of temperature, dew point, and wind speed
- **Key parameters** -- LCL, CAPE/CIN, bulk shear, stability index, inversions
- **Live TUI mode** -- persistent full-screen interface (like `top`/`htop`) with auto-refresh
- **ANSI color output** with `--no-color` fallback
- **Auto-scaling** axes to zoom in on actual data

## Setup

```bash
conda create -n weathertype python=3.12 numpy requests
conda activate weathertype
```

## Usage

```bash
# Show everything for a location
python -m weathertype.main --location Chicago

# By coordinates
python -m weathertype.main --lat 41.85 --lon -87.65

# Individual displays
python -m weathertype.main -l Chicago --skewt
python -m weathertype.main -l Chicago --hodogram
python -m weathertype.main -l Chicago --meteograph
python -m weathertype.main -l Chicago --summary --table

# 36-hour forecast timeline
python -m weathertype.main -l Chicago --forecast

# Specific forecast hour (0-23)
python -m weathertype.main -l Chicago --hour 18

# Disable colors
python -m weathertype.main -l Chicago --no-color

# Live TUI mode (persistent, auto-refreshing)
python -m weathertype.main -l Chicago --live

# Live mode with 5-minute refresh interval
python -m weathertype.main -l Chicago --live --refresh-interval 300
```

## Displays

### Skew-T Log-P

Plots temperature (red) and dew point (blue) on a skewed temperature axis with log-pressure vertical axis. Includes dry adiabat and isotherm reference lines.

### Hodogram

Wind vectors plotted as u/v components, connected from surface to upper atmosphere. Segments are colored by altitude band:

| Color  | Layer       |
|--------|-------------|
| Red    | Sfc -- 850 hPa |
| Yellow | 850 -- 700 hPa |
| Green  | 700 -- 500 hPa |
| Cyan   | 500 -- 300 hPa |
| Blue   | 300+ hPa      |

### Meteograph

Vertical profiles of temperature (red), dew point (blue), and wind speed (green) against log-pressure.

### 36-Hour Forecast

Multi-panel time-series display starting from the current hour:

- **Temperature & Dew Point** -- sparkline chart (red/blue)
- **Wind Speed & Gusts** -- sustained (green) and gusts (yellow) with direction arrows
- **Precipitation** -- bar chart with type indicators (rain/snow/freezing) and probability
- **Cloud Cover** -- low/mid/high layers using density fill characters
- **Pressure** -- mean sea-level pressure trend (magenta)
- **Weather Summary** -- WMO weather code timeline with legend

### Summary

Key meteorological parameters: surface conditions, LCL, potential temperature, equivalent potential temperature, CAPE/CIN, stability classification, inversion layers, bulk shear, and mean wind.

### Live TUI Mode

A persistent full-screen interface using curses. Switch between all views without restarting, with automatic data refresh.

| Key | Action |
|-----|--------|
| `1`-`5` | Switch view (Skew-T, Hodogram, Meteograph, Forecast, Summary) |
| `Tab` / `Shift-Tab` | Cycle views |
| `j`/`k` or arrows | Scroll |
| `r` | Force data refresh |
| `q` | Quit |

Data auto-refreshes at a configurable interval (default: 1 hour). The header shows the last update time, and a "Refreshing..." indicator appears during API calls.

## Data Source

All weather data comes from the [Open-Meteo API](https://open-meteo.com/) (no API key required). Pressure-level data is fetched for levels: 1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150 hPa.

## Project Structure

```
weathertype/
  main.py                  # CLI entry point
  api/
    open_meteo.py          # Open-Meteo API client
    models.py              # WeatherProfile data model
  calculations/
    thermodynamics.py      # LCL, CAPE/CIN, potential temperature
    hodogram.py            # Wind components, shear, mean wind
    meteograph.py           # Stability, inversions, lapse rate
  visualizations/
    skewt.py               # Skew-T Log-P diagram
    hodogram.py            # Wind hodogram
    meteograph.py          # Vertical profile charts
    forecast.py            # 36-hour forecast timeline
  tui/
    app.py                 # Curses TUI application and event loop
    views.py               # View classes for each visualization
    ansi_parser.py         # ANSI-to-curses color mapping
  utils/
    units.py               # Unit conversions
    coordinates.py         # Geocoding via Open-Meteo
    colors.py              # ANSI terminal colors
```
