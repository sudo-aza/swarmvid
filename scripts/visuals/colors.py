"""Shared color utilities for visual rendering."""

from __future__ import annotations


def hex_rgb(h: str) -> tuple[int, int, int]:
    """Parse hex color string to (R, G, B) tuple."""
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def alpha_color(rgb: tuple, a: int) -> tuple:
    """Return (R, G, B, A) with clamped alpha."""
    return (*rgb[:3], int(max(0, min(255, a))))
