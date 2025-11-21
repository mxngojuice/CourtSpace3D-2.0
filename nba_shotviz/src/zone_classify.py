"""
Zone classification helpers.

- classify_basic_zone(x, y): returns NBA SHOT_ZONE_BASIC for a given floor coordinate (feet)
- classify_area_lane(y): returns NBA SHOT_ZONE_AREA lane label based on lateral position

Coordinates:
    x: distance from baseline into the court, in feet (0..47)
    y: lateral from center, in feet (-25..+25), center line = 0

Relies on court constants to match NBA dimensions.
"""

import math
from .court_geometry import (
    HOOP_X, HOOP_Y,
    THREE_PT_RADIUS, THREE_PT_CORNER,
    FT_LINE_X, PAINT_WIDTH
)

# Precompute the 3PT arc meet point with the straight corner lines
_THETA0 = math.asin(THREE_PT_CORNER / THREE_PT_RADIUS)   # arcsin(22/23.75)
_X_MEET = HOOP_X + THREE_PT_RADIUS * math.cos(_THETA0)   # where arc meets straight corner lines
# Restricted area radius (feet) and lane half-width
_RESTRICTED_R = 4.0
_HALF_PAINT = PAINT_WIDTH / 2.0

# SHOT_ZONE_AREA labels (NBA convention)
_AREAS = [
    ("Left Side(L)",          -25.0, -15.0),
    ("Left Side Center(LC)",  -15.0,  -5.0),
    ("Center(C)",              -5.0,   5.0),
    ("Right Side Center(RC)",   5.0,  15.0),
    ("Right Side(R)",          15.0,  25.0),
]


def classify_area_lane(y: float) -> str:
    """
    Map lateral y (feet) into one of the 5 vertical lanes used by NBA shot zones.
    """
    # Clamp y to [-25, 25] just in case
    yy = max(-25.0, min(25.0, float(y)))
    for name, y0, y1 in _AREAS:
        if y0 <= yy < y1:
            return name
    # Right-most inclusive
    return "Right Side(R)"


def classify_basic_zone(x: float, y: float, pad_ft: float = 0.0) -> str:
    """
    Returns one of:
      - "Restricted Area"
      - "In The Paint (Non-RA)"
      - "Mid-Range"
      - "Left Corner 3" / "Right Corner 3"
      - "Above the Break 3"

    pad_ft expands the PAINT rectangle by pad_ft on all sides for grid/bin classification.
    """
    xf = float(x); yf = float(y)

    # Restricted circle (exact, no padding)
    if math.hypot(xf - HOOP_X, yf - HOOP_Y) <= _RESTRICTED_R:
        return "Restricted Area"

    # PAINT rectangle (allow optional padding)
    half_paint = _HALF_PAINT + pad_ft
    x0 = 0.0 - pad_ft
    x1 = FT_LINE_X + pad_ft
    if x0 <= xf <= x1 and abs(yf) <= half_paint:
        return "In The Paint (Non-RA)"

    # 3PT detection (exact, no padding)
    if abs(yf) >= THREE_PT_CORNER and xf <= _X_MEET:
        return "Left Corner 3" if yf < 0 else "Right Corner 3"

    if math.hypot(xf - HOOP_X, yf - HOOP_Y) >= THREE_PT_RADIUS:
        return "Above the Break 3"

    return "Mid-Range"
