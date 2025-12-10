"""Coordinate conversion utilities for mobile automation.

Supports three coordinate systems:
- Normalized (0-1): Percentage of screen dimension
- Thousandths (1-1000): Per-mille of screen dimension
- Pixels (>1000): Absolute pixel values
"""

from enum import Enum


class CoordinateSystem(str, Enum):
    """Coordinate system types."""

    NORMALIZED = "normalized"  # 0.0 - 1.0
    THOUSANDTHS = "thousandths"  # 1 - 1000
    PIXELS = "pixels"  # > 1000

    @classmethod
    def detect(cls, value: float) -> CoordinateSystem:
        """Detect coordinate system from value.

        Args:
            value: Coordinate value

        Returns:
            Detected coordinate system
        """
        if 0 <= value <= 1:
            return cls.NORMALIZED
        elif 1 < value <= 1000:
            return cls.THOUSANDTHS
        else:
            return cls.PIXELS


def normalize_coordinate(value: float, dimension: int) -> int:
    """Convert coordinate value to pixel coordinate.

    Supports three input formats:
    - 0-1: Normalized coordinate, multiply by dimension
    - 1-1000: Thousandths, divide by 1000 then multiply by dimension
    - >1000: Absolute pixel value, clamp to valid range

    Args:
        value: Input coordinate value
        dimension: Screen dimension (width or height) in pixels

    Returns:
        Pixel coordinate value (0 to dimension-1)
    """
    # Handle negative values
    if value < 0:
        return 0

    system = CoordinateSystem.detect(value)

    if system == CoordinateSystem.NORMALIZED:
        pixel = int(value * dimension)
        # For normalized values, allow full dimension at 1.0
        return max(0, min(pixel, dimension))
    elif system == CoordinateSystem.THOUSANDTHS:
        pixel = int(value / 1000 * dimension)
        # For thousandths, allow full dimension at 1000
        return max(0, min(pixel, dimension))
    else:  # PIXELS
        pixel = int(value)
        # For absolute pixels, clamp to dimension - 1
        return max(0, min(pixel, dimension - 1))
