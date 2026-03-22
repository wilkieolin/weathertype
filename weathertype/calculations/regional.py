"""Grid utility functions for regional weather visualizations."""

from typing import Dict, List, Optional, Tuple


def find_contours(
    values: List[Optional[float]],
    rows: int,
    cols: int,
    interval: float,
) -> Dict[float, List[Tuple[int, int]]]:
    """Find cells where value crosses contour levels at given interval.

    A cell is "on" a contour if the contour value lies between
    the cell and any of its 4-connected neighbors.

    Returns dict mapping contour_value -> list of (row, col) cells.
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return {}

    v_min = min(valid)
    v_max = max(valid)

    # Generate contour levels spanning the data range
    import math
    first_level = math.ceil(v_min / interval) * interval
    levels = []
    level = first_level
    while level <= v_max:
        levels.append(level)
        level += interval

    contours: Dict[float, List[Tuple[int, int]]] = {}

    for level in levels:
        cells = []
        for r in range(rows):
            for c in range(cols):
                val = values[r * cols + c]
                if val is None:
                    continue
                # Check 4-neighbors
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nval = values[nr * cols + nc]
                        if nval is not None:
                            if (val <= level <= nval) or (nval <= level <= val):
                                cells.append((r, c))
                                break
        if cells:
            contours[level] = cells

    return contours
