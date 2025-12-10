"""Tests for coordinate conversion utilities."""

import pytest

from odin.plugins.builtin.mobile.coordinates import normalize_coordinate, CoordinateSystem


class TestNormalizeCoordinate:
    """Test normalize_coordinate function."""

    def test_normalized_0_to_1(self):
        """0.5 on 1080px screen = 540px."""
        result = normalize_coordinate(0.5, 1080)
        assert result == 540

    def test_normalized_zero(self):
        """0.0 = 0px."""
        result = normalize_coordinate(0.0, 1920)
        assert result == 0

    def test_normalized_one(self):
        """1.0 = full dimension."""
        result = normalize_coordinate(1.0, 1080)
        assert result == 1080

    def test_thousandths_500(self):
        """500 (thousandths) on 1080px = 540px."""
        result = normalize_coordinate(500, 1080)
        assert result == 540

    def test_thousandths_1000(self):
        """1000 (thousandths) on 1080px = 1080px."""
        result = normalize_coordinate(1000, 1080)
        assert result == 1080

    def test_pixel_value(self):
        """Values > 1000 are treated as pixels."""
        result = normalize_coordinate(1500, 1080)
        assert result == 1079  # Clamped to dimension - 1

    def test_pixel_exact(self):
        """Exact pixel within bounds."""
        result = normalize_coordinate(1001, 1920)
        assert result == 1001

    def test_negative_clamps_to_zero(self):
        """Negative values clamp to 0."""
        result = normalize_coordinate(-0.1, 1080)
        assert result == 0


class TestCoordinateSystem:
    """Test CoordinateSystem detection."""

    def test_detect_normalized(self):
        """Values 0-1 are normalized."""
        assert CoordinateSystem.detect(0.5) == CoordinateSystem.NORMALIZED
        assert CoordinateSystem.detect(0.0) == CoordinateSystem.NORMALIZED
        assert CoordinateSystem.detect(1.0) == CoordinateSystem.NORMALIZED

    def test_detect_thousandths(self):
        """Values 1-1000 are thousandths."""
        assert CoordinateSystem.detect(500) == CoordinateSystem.THOUSANDTHS
        assert CoordinateSystem.detect(1.1) == CoordinateSystem.THOUSANDTHS
        assert CoordinateSystem.detect(1000) == CoordinateSystem.THOUSANDTHS

    def test_detect_pixels(self):
        """Values > 1000 are pixels."""
        assert CoordinateSystem.detect(1001) == CoordinateSystem.PIXELS
        assert CoordinateSystem.detect(1920) == CoordinateSystem.PIXELS
