# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

weathertype is a terminal-based weather visualization CLI that renders Skew-T Log-P diagrams, hodograms, meteographs, and 36-hour forecast timelines using ANSI characters. All weather data comes from the Open-Meteo API (no API key required).

## Setup & Running

```bash
# Environment setup
conda create -n weathertype python=3.12 numpy requests
conda activate weathertype

# Run (module invocation — there is no installed entry point yet)
python -m weathertype.main --location Chicago
python -m weathertype.main --lat 41.85 --lon -87.65

# Individual displays
python -m weathertype.main -l Chicago --skewt
python -m weathertype.main -l Chicago --hodogram
python -m weathertype.main -l Chicago --meteograph
python -m weathertype.main -l Chicago --forecast
python -m weathertype.main -l Chicago --summary --table

# Disable color output
python -m weathertype.main -l Chicago --no-color
```

No test suite exists yet. Dependencies: `numpy`, `requests` (see `pyproject.toml`).

## Architecture

The data pipeline flows: **CLI args → geocoding → API fetch → calculations → terminal rendering**.

- `main.py` — CLI entry point (`argparse`). Orchestrates the full pipeline. If no display flags are given, all visualizations are shown.
- `api/open_meteo.py` — `OpenMeteoClient` fetches pressure-level profiles and surface forecast data. Has in-memory response caching. Pressure levels: 1000–150 hPa.
- `api/models.py` — `WeatherProfile` (vertical sounding at one time) and `ForecastData` (hourly surface time-series). Both are `@dataclass`es with validation.
- `calculations/` — Pure computation, no I/O. `thermodynamics.py` (LCL, CAPE/CIN, potential temp), `hodogram.py` (wind components, shear), `meteograph.py` (stability index, inversions).
- `visualizations/` — Each plotter class builds a string of ANSI-colored terminal output. `skewt.py`, `hodogram.py`, `meteograph.py`, `forecast.py`. All rendering is character-grid based (no external plotting library).
- `utils/colors.py` — ANSI color helpers. Respects `NO_COLOR` env var (toggled at runtime via `--no-color` flag which sets `_COLORS_ON = False`).
- `utils/coordinates.py` — Geocoding via Open-Meteo's geocoding API.
- `utils/units.py` — Unit conversion helpers.

## Key Conventions

- Visualizations render to strings (returned from plotter methods), then printed by `main.py`.
- Pressure levels are ordered descending (surface=highest pressure first, upper atmosphere last).
- Wind speeds from the API arrive in km/h; calculations may convert to m/s internally.
- The `WeatherProfile` dataclass validates that all parallel arrays have matching length on construction.
