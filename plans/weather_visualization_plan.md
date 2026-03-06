# Weather Visualization Program Plan

## Project Overview
A CLI-based weather visualization program that retrieves recent weather prediction models from public APIs and creates terminal-compatible visualizations including:
- Log P-Skew T diagrams
- Meteographs
- Hodograms

## Technology Stack

### Language: Python 3.10+

### Core Libraries
| Library | Purpose |
|---------|---------|
| `requests` | HTTP requests to weather APIs |
| `pandas` | Data manipulation and processing |
| `numpy` | Numerical calculations for meteorological formulas |
| `termplotlib` or `rich` | Terminal-based plotting and visualization |

### Weather API Options
1. **Open-Meteo** (Recommended)
   - Free, no API key required
   - Provides GFS model data including temperature, dew point, wind, pressure
   - Simple REST API with JSON responses

2. **NOAA NCEP Reanalysis**
   - Free, comprehensive historical data
   - More complex to access but very complete

3. **Meteostat**
   - Free tier available
   - Good for current observations and forecasts

## Program Architecture

```
weathertype/
├── main.py                    # Entry point with CLI interface
├── requirements.txt           # Python dependencies
├── README.md                  # Documentation
│
├── api/                       # Weather API integration
│   ├── __init__.py
│   ├── open_meteo.py          # Open-Meteo API client
│   └── models.py              # Data models for weather data
│
├── calculations/              # Meteorological calculations
│   ├── __init__.py
│   ├── thermodynamics.py      # Skew-T related calculations
│   ├── hodogram.py            # Hodogram calculations
│   └── meteograph.py          # Meteograph calculations
│
├── visualizations/            # Terminal plotting
│   ├── __init__.py
│   ├── skewt.py               # Log P-Skew T diagram
│   ├── hodogram.py            # Wind hodogram
│   └── meteograph.py          # Meteograph display
│
└── utils/                     # Helper functions
    ├── __init__.py
    ├── units.py               # Unit conversions
    └── coordinates.py         # Location lookup and validation
```

## Core Features

### 1. Data Retrieval Module (`api/open_meteo.py`)
- Fetch GFS model data from Open-Meteo
- Support for latitude/longitude input
- Parse vertical profile data (temperature, dew point, wind speed/direction at various pressure levels)
- Cache responses to reduce API calls

### 2. Meteorological Calculations (`calculations/`)

#### Thermodynamics (`thermodynamics.py`)
- Calculate potential temperature (θ)
- Calculate equivalent potential temperature (θe)
- Calculate lifting condensation level (LCL)
- Calculate convective available potential energy (CAPE)
- Calculate convective inhibition (CIN)

#### Hodogram (`hodogram.py`)
- Convert wind components (u, v) from speed/direction
- Calculate wind shear
- Prepare data for hodogram plotting

#### Meteograph (`meteograph.py`)
- Calculate temperature profiles
- Calculate dew point profiles
- Calculate wind speed profiles

### 3. Visualization Module (`visualizations/`)

#### Skew-T Diagram (`skewt.py`)
- Create log-pressure coordinate system
- Plot temperature and dew point curves
- Add dry adiabats, moist adiabats, mixing ratio lines
- Display key parameters (LCL, LFC, EL, CAPE, CIN)
- Use termplotlib for terminal rendering

#### Hodogram (`hodogram.py`)
- Create polar coordinate plot of wind vectors
- Plot wind speed as distance from center
- Show wind direction as angle
- Add shear vector annotations

#### Meteograph (`meteograph.py`)
- Horizontal layout showing surface to upper air data
- Temperature, dew point, and wind barbs
- Compact display for terminal environment

### 4. CLI Interface (`main.py`)

```bash
# Usage examples:
weathertype --location "Chicago, IL"
weathertype --lat 41.8781 --lon -87.6298
weathertype --zip 60601
```

Options:
- `--location`: City name or coordinates
- `--output`: Output format (ansi, unicode, emoji)
- `--verbose`: Show additional meteorological parameters

## Implementation Steps

### Phase 1: Foundation
1. Set up project structure and dependencies
2. Implement API client for Open-Meteo
3. Create data models for weather profiles
4. Add unit conversion utilities

### Phase 2: Calculations
5. Implement thermodynamic calculations
6. Add hodogram calculations
7. Implement meteograph data processing

### Phase 3: Visualizations
8. Create Skew-T diagram with termplotlib
9. Implement hodogram plotting
10. Build meteograph display

### Phase 4: CLI and Polish
11. Build command-line interface
12. Add error handling and validation
13. Create documentation
14. Test with multiple locations

## Terminal Graphics Approach

Using `termplotlib` for rendering:
- Supports line plots, scatter plots, and basic shapes
- Works in any terminal with ANSI escape codes
- Can export to various formats (ASCII, UTF-8, emoji)

Example Skew-T structure:
```
Pressure (hPa)
1000 |    *     *   Temperature
 925 |   *       *
 850 |  *         *   Dew Point
 700 | *           *
 500 |*             *
     -------------------
      -40 -20  0  20  40  (°C)
```

## Next Steps

1. Create the project structure
2. Install dependencies (`pip install requests pandas numpy termplotlib`)
3. Implement API client and test with a sample location
4. Begin calculations module development
5. Build visualization components incrementally
