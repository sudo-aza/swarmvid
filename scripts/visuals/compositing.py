"""Compositing utilities — alpha blending, overlays, pre-computed backgrounds."""

from __future__ import annotations

import numpy as np
from PIL import Image


def make_bg_composited(w: int, h: int, colors: list[tuple],
                       vignette_strength: float = 0.5,
                       dark_factor: float = 0.85) -> Image.Image:
    """Pre-compute background: radial gradient with vignette darkening baked in.
    Returns an RGB PIL Image."""
    n = len(colors)
    cx, cy = w / 2.0, h / 2.0
    y_coords, x_coords = np.mgrid[0:h, 0:w]
    dx = (x_coords - cx) / cx
    dy = (y_coords - cy) / cy
    d = np.sqrt(dx * dx + dy * dy) / 1.414
    d = np.clip(d, 0, 1.0)
    t = d * (n - 1)
    colors_arr = np.array(colors, dtype=np.float64)
    idx = np.clip(t.astype(int), 0, n - 2)
    frac = (t - idx)[..., np.newaxis]
    gradient = colors_arr[idx] * (1 - frac) + colors_arr[idx + 1] * frac
    vig = np.clip(1.0 - d * vignette_strength, 0, 1)
    blend = np.where(vig >= dark_factor, 1.0, vig / dark_factor)
    result = gradient * blend[..., np.newaxis]
    return Image.fromarray(result.astype(np.uint8), "RGB")


def make_solid_bg(w: int, h: int, color: tuple) -> Image.Image:
    """Create a solid-color background. Returns an RGB PIL Image."""
    return Image.new("RGB", (w, h), color)


def make_gradient_bg(w: int, h: int, colors: list[tuple],
                     direction: str = "vertical") -> Image.Image:
    """Create a linear gradient background.
    direction: 'vertical', 'horizontal', 'radial'
    Returns an RGB PIL Image."""
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    n = len(colors)
    colors_arr = np.array(colors, dtype=np.float64)
    if direction == "horizontal":
        t = np.linspace(0, n - 1, w)
        idx = np.clip(t.astype(int), 0, n - 2)
        frac = (t - idx)[..., np.newaxis]
        row = colors_arr[idx] * (1 - frac) + colors_arr[idx + 1] * frac
        arr[:] = row[np.newaxis, :, :]
    elif direction == "radial":
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        dx = (x_coords - w / 2.0) / (w / 2.0)
        dy = (y_coords - h / 2.0) / (h / 2.0)
        d = np.sqrt(dx * dx + dy * dy) / 1.414
        d = np.clip(d, 0, 1.0)
        t = d * (n - 1)
        idx = np.clip(t.astype(int), 0, n - 2)
        frac = (t - idx)[..., np.newaxis]
        arr = (colors_arr[idx] * (1 - frac) + colors_arr[idx + 1] * frac).astype(np.uint8)
    else:  # vertical (default)
        t = np.linspace(0, n - 1, h)
        idx = np.clip(t.astype(int), 0, n - 2)
        frac = (t - idx)[..., np.newaxis]
        col = colors_arr[idx] * (1 - frac) + colors_arr[idx + 1] * frac
        arr[:] = col[:, np.newaxis, :]
    return Image.fromarray(arr, "RGB")
