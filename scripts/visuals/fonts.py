"""Font loading — shared across all treatments."""

from __future__ import annotations

import os
from PIL import ImageFont

# ── Layout constants shared across treatments ─────────────────────────────────
W, H = 1280, 720
FPS = 24
MAP_PANEL_W = 520
TEXT_PANEL_LEFT = 540
TEXT_PANEL_RIGHT = 1240
TEXT_PANEL_W = TEXT_PANEL_RIGHT - TEXT_PANEL_LEFT

BODY_FONT_SIZE = 22
BODY_LINE_HEIGHT = 32
MAX_VISIBLE_LINES = 7
TEXT_TOP_MARGIN = 130
TITLE_CARD_DURATION = 3.5
WORD_REVEAL_SPEED = 0.03
SEGMENT_CROSS_FADE = 0.08

_FONT_CACHE: dict = {}


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def get_fonts() -> dict:
    """Load all fonts needed for rendering. Returns a dict of named fonts."""
    sans = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    sans_b = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    serif = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    if not os.path.exists(sans):
        sans = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        sans_b = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        serif = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
    return {
        "title":    _font(serif, 52),
        "subtitle": _font(sans, 26),
        "body":     _font(sans, BODY_FONT_SIZE),
        "bold":     _font(sans_b, BODY_FONT_SIZE),
        "small":    _font(sans, 18),
        "tiny":     _font(sans, 14),
        "era":      _font(serif, 22),
        "map_label": _font(sans, 13),
        "map_label_b": _font(sans_b, 14),
        "map_region": _font(serif, 16),
        "lower_third": _font(sans_b, 20),
        "timeline_label": _font(sans, 11),
    }
