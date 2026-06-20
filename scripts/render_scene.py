#!/usr/bin/env python3
"""
render_scene.py — Documentary motion graphics renderer.

Renders Pillow frames piped to ffmpeg for H.264 MP4 output at 1280x720.

Visual design:
  - Full-screen dark vignette with gradient backgrounds
  - Procedural map of Hannover region with location markers (left panel)
  - Cinematic title sequences with animated decorative elements
  - Word-by-word text reveal animation on right narration panel
  - Floating light particles (warm glow)
  - Horizontal progress timeline at bottom
  - Lower-third era/scene labels

Usage:
    python3 render_scene.py --scene-json scene.json --audio audio.wav --output scene_N.mp4
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
import wave

import numpy as np

from PIL import Image, ImageDraw, ImageFont

# ── Constants ──────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 24

# Layout: split view — map panel (left) + narration panel (right)
MAP_PANEL_W = 520
MAP_PANEL_X = 0
MAP_PANEL_Y = 0

TEXT_PANEL_LEFT = 540
TEXT_PANEL_RIGHT = 1240
TEXT_PANEL_W = TEXT_PANEL_RIGHT - TEXT_PANEL_LEFT

# Title card
TITLE_CARD_DURATION = 3.5

# Particles
PARTICLE_COUNT = 30

# Typography
BODY_FONT_SIZE = 22
BODY_LINE_HEIGHT = 32
MAX_VISIBLE_LINES = 7
TEXT_TOP_MARGIN = 130

# Animation speeds
WORD_REVEAL_SPEED = 0.03
SEGMENT_CROSS_FADE = 0.08

# Timeline bar
TIMELINE_BAR_Y = H - 32
TIMELINE_BAR_H = 20
TIMELINE_BAR_MARGIN = 60
TIMELINE_NODE_R = 4

# Lower-third banner
LOWER_THIRD_H = 44
LOWER_THIRD_FONT_SIZE = 20
LOWER_THIRD_SLIDE_FRAMES = 12  # frames for slide-in animation
LOWER_THIRD_HOLD_FRAMES = 48  # frames to hold before slide-out
LOWER_THIRD_GAP_FRAMES = 24  # frames between banners

# Source watermark
SOURCE_WATERMARK_Y = H - 60
SOURCE_WATERMARK_MAX_ALPHA = 150

# ── Historical Era Timeline ──────────────────────────────────────────────────
# Maps scene numbers to era labels and display positions on timeline.
# The 28 scenes span ~1000 years of Hannover's history.
ERA_DEFINITION = [
    {"label": "Mittelalter",        "range": "800-1500", "scenes": [1, 2, 3, 4, 5]},
    {"label": "Renaissance",        "range": "1500-1600", "scenes": [6, 7, 8]},
    {"label": "Dreißigjähriger Krieg", "range": "1618-1648", "scenes": [9, 10, 11]},
    {"label": "Barock",             "range": "1648-1714", "scenes": [12, 13, 14]},
    {"label": "Kurfürstentum",      "range": "1692-1814", "scenes": [15, 16, 17]},
    {"label": "Königreich",         "range": "1814-1866", "scenes": [18, 19, 20, 21]},
    {"label": "Preußen",           "range": "1866-1918", "scenes": [22, 23, 24]},
    {"label": "Weimar & NS",        "range": "1918-1945", "scenes": [25, 26]},
    {"label": "Nachkriegszeit",    "range": "1945-2000", "scenes": [27, 28]},
]


# ── Hannover Region Map Data ───────────────────────────────────────────────────
# Geographic coordinates for key locations (lon, lat)
# Map covers roughly 9.0-11.0 E, 51.8-53.0 N
MAP_LON_MIN, MAP_LON_MAX = 8.9, 11.0
MAP_LAT_MIN, MAP_LAT_MAX = 51.8, 53.2

HANNOVER_LOCATIONS = {
    "Hannover":        {"lon": 9.736, "lat": 52.370, "type": "capital"},
    "Hildesheim":      {"lon": 9.947, "lat": 52.151, "type": "city"},
    "Braunschweig":    {"lon": 10.526, "lat": 52.262, "type": "city"},
    "Gottingen":       {"lon": 9.936, "lat": 51.532, "type": "city"},
    "Hameln":          {"lon": 9.327, "lat": 52.105, "type": "city"},
    "Celle":           {"lon": 9.608, "lat": 52.617, "type": "city"},
    "Lehrte":          {"lon": 9.973, "lat": 52.370, "type": "town"},
    "Petershagen":     {"lon": 9.018, "lat": 52.382, "type": "town"},
    "Neustadt":        {"lon": 9.724, "lat": 52.529, "type": "town"},
    "Langenhagen":     {"lon": 9.743, "lat": 52.447, "type": "town"},
    "Garbsen":         {"lon": 9.596, "lat": 52.421, "type": "town"},
    "Wunstorf":        {"lon": 9.427, "lat": 52.425, "type": "town"},
    "Springe":         {"lon": 9.838, "lat": 52.214, "type": "town"},
    "Laatzen":         {"lon": 9.731, "lat": 52.318, "type": "town"},
    "Nienburg":        {"lon": 9.142, "lat": 52.642, "type": "city"},
    "Stade":           {"lon": 9.475, "lat": 53.597, "type": "city"},
    "Luneburg":        {"lon": 10.410, "lat": 53.245, "type": "city"},
    "Peine":           {"lon": 10.232, "lat": 52.326, "type": "town"},
    "Wolfsburg":       {"lon": 10.790, "lat": 52.425, "type": "city"},
    "Hildesheim (Bf)": {"lon": 9.950, "lat": 52.148, "type": "town"},
}

# River Leine path — simplified polyline (lon, lat)
LEINE_RIVER = [
    (9.75, 52.6), (9.70, 52.5), (9.72, 52.4), (9.74, 52.37),
    (9.73, 52.35), (9.73, 52.3), (9.74, 52.2), (9.75, 52.15),
    (9.80, 52.0), (9.85, 51.8),
]

# River Weser path (major river west of Leine)
WESER_RIVER = [
    (9.15, 52.85), (9.10, 52.75), (9.08, 52.65), (9.10, 52.55),
    (9.12, 52.45), (9.15, 52.35), (9.18, 52.25), (9.20, 52.15),
    (9.22, 52.05), (9.25, 51.9),
]

# River Aller path (joins Leine at Schwarmstedt)
ALLER_RIVER = [
    (9.60, 52.9), (9.65, 52.8), (9.68, 52.7), (9.72, 52.6),
    (9.75, 52.6),
]

# Major road connections (simplified)
ROAD_CONNECTIONS = [
    ("Hannover", "Hildesheim"),
    ("Hannover", "Braunschweig"),
    ("Hannover", "Celle"),
    ("Hannover", "Hameln"),
    ("Hannover", "Lehrte"),
    ("Hannover", "Wunstorf"),
    ("Hannover", "Langenhagen"),
    ("Braunschweig", "Wolfsburg"),
    ("Hildesheim", "Gottingen"),
    ("Celle", "Nienburg"),
    ("Hameln", "Nienburg"),
]

# Approximate border of Lower Saxony (simplified polygon)
LOWER_SAXONY_BORDER = [
    (8.9, 53.1), (9.0, 52.9), (8.9, 52.7), (8.9, 52.5), (8.9, 52.3),
    (9.0, 52.1), (9.1, 52.0), (9.3, 51.9), (9.5, 51.85), (9.8, 51.8),
    (10.1, 51.8), (10.4, 51.85), (10.6, 51.9), (10.8, 52.0), (11.0, 52.1),
    (11.0, 52.3), (10.9, 52.5), (10.8, 52.7), (10.7, 52.9), (10.5, 53.1),
    (10.3, 53.2), (10.0, 53.2), (9.7, 53.2), (9.4, 53.2), (9.2, 53.2),
    (9.0, 53.15), (8.9, 53.1),
]

# Scene-specific location highlights: which locations matter per scene era
SCENE_LOCATIONS = {
    1: ["Hannover"],
    2: ["Hannover", "Hildesheim"],
    3: ["Hannover", "Hildesheim", "Braunschweig"],
    4: ["Hannover"],
    5: ["Hannover", "Celle"],
    6: ["Hannover", "Hildesheim", "Braunschweig"],
    7: ["Hannover", "Lehrte", "Langenhagen"],
    8: ["Hannover"],
    9: ["Hannover", "Hildesheim"],
    10: ["Hannover", "Laatzen", "Springe"],
    11: ["Hannover"],
    12: ["Hannover"],
    13: ["Hannover", "Lehrte"],
    14: ["Hannover"],
    15: ["Hannover", "Langenhagen", "Garbsen"],
    16: ["Hannover", "Braunschweig", "Wolfsburg"],
    17: ["Hannover"],
    18: ["Hannover"],
    19: ["Hannover", "Hildesheim"],
    20: ["Hannover", "Laatzen"],
    21: ["Hannover"],
    22: ["Hannover", "Celle", "Nienburg"],
    23: ["Hannover"],
    24: ["Hannover"],
    25: ["Hannover"],
    26: ["Hannover", "Braunschweig"],
    27: ["Hannover"],
    28: ["Hannover"],
}


# ── Font Loading ──────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _font(path, size):
    key = (path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def get_fonts():
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
        "lower_third": _font(sans_b, LOWER_THIRD_FONT_SIZE),
        "timeline_label": _font(sans, 11),
    }


# ── Color Utilities ─────────────────────────────────────────────────────────────
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def alpha_color(rgb, a):
    return (*rgb, int(max(0, min(255, a))))


def make_bg_composited(w, h, colors, vignette_strength=0.5, dark_factor=0.85):
    """Pre-compute background: gradient with vignette darkening baked in.
    Eliminates the per-frame vignette.point(lambda) call."""
    n = len(colors)
    cx, cy = w / 2.0, h / 2.0
    y_coords, x_coords = np.mgrid[0:h, 0:w]
    dx = (x_coords - cx) / cx
    dy = (y_coords - cy) / cy
    d = np.sqrt(dx*dx + dy*dy) / 1.414
    d = np.clip(d, 0, 1.0)
    t = d * (n - 1)
    colors_arr = np.array(colors, dtype=np.float64)
    idx = np.clip(t.astype(int), 0, n - 2)
    frac = (t - idx)[..., np.newaxis]
    gradient = colors_arr[idx] * (1 - frac) + colors_arr[idx + 1] * frac
    # Vignette darkening
    vig = np.clip(1.0 - d * vignette_strength, 0, 1)
    blend = np.where(vig >= dark_factor, 1.0, vig / dark_factor)
    result = gradient * blend[..., np.newaxis]
    return Image.fromarray(result.astype(np.uint8), "RGB")


def make_map_bg(panel_w, panel_h):
    """Pre-compute the map panel dark background gradient."""
    bg = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bg)
    for y_row in range(panel_h):
        t = y_row / panel_h
        darkness = int(18 + 8 * t)
        draw.line([(0, y_row), (panel_w - 1, y_row)],
                  fill=(darkness, darkness, darkness + 5, 255))
    return bg


def make_divider_gradient(w, h, divider_x, fade_width=20):
    """Pre-compute the divider + fade gradient as a reusable RGBA overlay."""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for fade_x in range(divider_x, divider_x + fade_width):
        fade_a = int(60 * (1.0 - (fade_x - divider_x) / fade_width))
        draw.line([(fade_x, 0), (fade_x, h)],
                  fill=(15, 15, 20, fade_a))
    return overlay


# ── Pre-computation ──────────────────────────────────────────────────────────
def precompute_particles(count, w, h, seed):
    rng = random.Random(seed)
    particles = []
    for _ in range(count):
        particles.append({
            "x": rng.randint(0, w),
            "y_base": rng.randint(0, h),
            "speed": rng.uniform(0.2, 0.8),
            "size": rng.randint(2, 5),
            "brightness": rng.randint(80, 200),
            "phase": rng.uniform(0, math.tau),
        })
    return particles


def prewrap_text(segments, font, max_width):
    result = []
    for seg in segments:
        lines = []
        text = seg.get("text", "")
        words = text.split()
        current = ""
        dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
        for word in words:
            test = current + (" " if current else "") + word
            bbox = dummy.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        result.append({"lines": lines, "words": text.split()})
    return result


# ── Timeline Bar Drawing ──────────────────────────────────────────────────
def draw_timeline_bar(od, scene_num, total_scenes, accent, fonts):
    """Draw historical era timeline at bottom of frame.
    Shows all scenes as nodes grouped by era, with current scene highlighted."""
    bar_left = TIMELINE_BAR_MARGIN
    bar_right = W - TIMELINE_BAR_MARGIN
    bar_w = bar_right - bar_left
    bar_top = TIMELINE_BAR_Y - TIMELINE_BAR_H // 2

    # Semi-transparent background strip
    od.rounded_rectangle(
        [(bar_left - 10, bar_top - 4), (bar_right + 10, bar_top + TIMELINE_BAR_H + 4)],
        radius=4, fill=(0, 0, 0, 160)
    )

    # Compute x positions for each scene node (evenly spaced)
    total = total_scenes  # 28
    scene_x = {}
    for s in range(1, total + 1):
        frac = (s - 1) / max(total - 1, 1)
        scene_x[s] = bar_left + int(frac * bar_w)

    # Draw era segments (colored spans between first and last scene of each era)
    for era in ERA_DEFINITION:
        era_scenes = era["scenes"]
        if not era_scenes:
            continue
        first_s = era_scenes[0]
        last_s = era_scenes[-1]
        x1 = scene_x.get(first_s, bar_left)
        x2 = scene_x.get(last_s, bar_right)

        # Era background strip
        od.rectangle(
            [(x1, bar_top + 2), (x2, bar_top + TIMELINE_BAR_H - 2)],
            fill=alpha_color(accent, 20)
        )

        # Era label (centered between first and last scene of era, above bar)
        era_center_x = (x1 + x2) // 2
        label_text = era["label"]
        if len(label_text) > 16:
            label_text = label_text[:15] + "."
        bbox = od.textbbox((0, 0), label_text, font=fonts["timeline_label"])
        tw = bbox[2] - bbox[0]
        # Place era label above timeline only if there's enough space
        if x2 - x1 > tw + 10:
            od.text((era_center_x - tw // 2, bar_top - 15), label_text,
                    fill=alpha_color((180, 180, 190), 180),
                    font=fonts["timeline_label"])

    # Draw the main timeline line
    od.line([(bar_left, bar_top + TIMELINE_BAR_H // 2),
             (bar_right, bar_top + TIMELINE_BAR_H // 2)],
            fill=alpha_color((120, 120, 130), 180), width=1)

    # Draw scene nodes
    for s in range(1, total + 1):
        x = scene_x[s]
        y = bar_top + TIMELINE_BAR_H // 2
        r = TIMELINE_NODE_R
        if s == scene_num:
            # Current scene: bright accent with glow
            od.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3],
                      fill=alpha_color(accent, 90))
            od.ellipse([x - r, y - r, x + r, y + r],
                      fill=alpha_color(accent, 240))
            od.ellipse([x - 1, y - 1, x + 1, y + 1],
                      fill=(255, 255, 255, 230))
        elif s < scene_num:
            # Past scenes: dim accent
            od.ellipse([x - r + 1, y - r + 1, x + r - 1, y + r - 1],
                      fill=alpha_color(accent, 80))
        else:
            # Future scenes: dark
            od.ellipse([x - r + 1, y - r + 1, x + r - 1, y + r - 1],
                      fill=(60, 60, 70, 80))


# ── Lower-Third Banner Drawing ─────────────────────────────────────────────────
def get_lower_third_state(frame_idx, facts):
    """Compute which fact banner to show and animation progress.
    Returns (fact_text, slide_progress, visible)."""
    if not facts:
        return None, None, False

    total_cycle = LOWER_THIRD_SLIDE_FRAMES + LOWER_THIRD_HOLD_FRAMES + LOWER_THIRD_GAP_FRAMES
    fact_idx = (frame_idx // total_cycle) % len(facts)
    cycle_pos = frame_idx % total_cycle

    if cycle_pos < LOWER_THIRD_SLIDE_FRAMES:
        # Slide in (ease-out cubic)
        slide_t = cycle_pos / LOWER_THIRD_SLIDE_FRAMES
        slide_t = 1.0 - (1.0 - slide_t) ** 3
        return facts[fact_idx], slide_t, True
    elif cycle_pos < LOWER_THIRD_SLIDE_FRAMES + LOWER_THIRD_HOLD_FRAMES:
        # Holding
        return facts[fact_idx], 1.0, True
    else:
        # Gap between banners
        return None, None, False


def draw_lower_third_banner(od, fact_text, slide_progress, accent, fonts):
    """Draw a slide-in lower-third fact banner below the text panel."""
    if slide_progress <= 0:
        return
    banner_h = LOWER_THIRD_H
    # Banner positioned below the text area
    banner_y = TEXT_TOP_MARGIN + MAX_VISIBLE_LINES * BODY_LINE_HEIGHT + 50
    banner_x_start = TEXT_PANEL_LEFT - 15

    # Calculate text width for content sizing
    bbox = od.textbbox((0, 0), fact_text, font=fonts["lower_third"])
    text_w = bbox[2] - bbox[0]
    content_w = min(text_w + 50, 620)

    # Slide-in from left
    offset_x = int((1.0 - slide_progress) * -content_w)
    draw_x = banner_x_start + offset_x

    # Background box with accent left border
    od.rounded_rectangle(
        [(draw_x, banner_y), (draw_x + content_w, banner_y + banner_h)],
        radius=4, fill=(0, 0, 0, 180)
    )
    od.rectangle(
        [(draw_x, banner_y + 4), (draw_x + 3, banner_y + banner_h - 4)],
        fill=alpha_color(accent, 220)
    )
    # Text
    od.text((draw_x + 12, banner_y + (banner_h - LOWER_THIRD_FONT_SIZE) // 2 - 1),
            fact_text,
            fill=alpha_color((230, 230, 235), 230),
            font=fonts["lower_third"])


# ── Source Watermark Drawing ─────────────────────────────────────────────────
def draw_source_watermark(od, sources, accent, fonts):
    """Draw persistent semi-transparent source citation watermark in bottom-right."""
    if not sources:
        return

    lines = sources[:2]
    font = fonts["tiny"]

    # Measure widest line
    max_w = 0
    for line in lines:
        bbox = od.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        max_w = max(max_w, tw)

    line_h = 16
    box_w = max_w + 16
    box_h = len(lines) * line_h + 10
    box_x = W - box_w - 10
    box_y = SOURCE_WATERMARK_Y - box_h + 5

    # Semi-transparent dark background
    od.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=3, fill=(0, 0, 0, 100)
    )
    # Subtle accent top border
    od.line([(box_x + 3, box_y), (box_x + box_w - 3, box_y)],
            fill=alpha_color(accent, 100), width=1)

    # Draw source text
    for i, line in enumerate(lines):
        od.text((box_x + 8, box_y + 5 + i * line_h), line,
                fill=alpha_color((170, 170, 175), SOURCE_WATERMARK_MAX_ALPHA),
                font=font)


# ── Map Drawing ───────────────────────────────────────────────────────────────
def geo_to_map(lon, lat, panel_x, panel_y, panel_w, panel_h, padding=30):
    """Convert geographic coordinates to pixel position within the map panel."""
    t = (lon - MAP_LON_MIN) / (MAP_LON_MAX - MAP_LON_MIN)
    u = 1.0 - (lat - MAP_LAT_MIN) / (MAP_LAT_MAX - MAP_LAT_MIN)
    x = panel_x + padding + t * (panel_w - 2 * padding)
    y = panel_y + padding + u * (panel_h - 2 * padding)
    return int(x), int(y)


def draw_map_panel(draw, od, panel_x, panel_y, panel_w, panel_h,
                   accent, frame_idx, scene_num, fonts):
    """Draw a documentary-style map of the Hannover/Lower Saxony region."""

    # Dark panel background with subtle gradient
    for y_row in range(panel_h):
        t = y_row / panel_h
        darkness = int(18 + 8 * t)  # slightly lighter at bottom
        draw.line([(panel_x, panel_y + y_row), (panel_x + panel_w - 1, panel_y + y_row)],
                 fill=(darkness, darkness, darkness + 5))

    # Draw border
    od.rectangle(
        [(panel_x + 1, panel_y + 1), (panel_x + panel_w - 2, panel_y + panel_h - 2)],
        outline=alpha_color(accent, 100), width=1
    )

    # Draw Lower Saxony border (subtle)
    border_px = [geo_to_map(lon, lat, panel_x, panel_y, panel_w, panel_h)
                 for lon, lat in LOWER_SAXONY_BORDER]
    if len(border_px) > 2:
        od.polygon(border_px, outline=alpha_color(accent, 80), fill=None)

    # Draw River Leine (animated flow)
    river_px = [geo_to_map(lon, lat, panel_x, panel_y, panel_w, panel_h)
                for lon, lat in LEINE_RIVER]
    if len(river_px) > 1:
        # Main river line
        river_color = (50, 100, 160, 140)
        for i in range(len(river_px) - 1):
            # Animated dash effect
            dash_phase = (frame_idx * 0.02 + i * 0.15) % 1.0
            if dash_phase < 0.7:
                od.line([river_px[i], river_px[i+1]], fill=river_color, width=3)
        # River glow
        river_glow = (60, 120, 190, 60)
        for i in range(len(river_px) - 1):
            od.line([river_px[i], river_px[i+1]], fill=river_glow, width=7)

    # Determine which locations to highlight for this scene
    highlight_names = SCENE_LOCATIONS.get(scene_num, ["Hannover"])

    # Draw all locations
    for name, loc in HANNOVER_LOCATIONS.items():
        px, py = geo_to_map(loc["lon"], loc["lat"],
                             panel_x, panel_y, panel_w, panel_h)
        is_highlight = name in highlight_names
        loc_type = loc["type"]

        if is_highlight:
            # Pulsing glow for highlighted location
            pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.05)
            glow_r = int(12 + 6 * pulse)

            # Outer glow
            od.ellipse([px - glow_r, py - glow_r, px + glow_r, py + glow_r],
                      fill=alpha_color(accent, int(30 + 20 * pulse)))

            # Inner dot
            dot_r = 6 if loc_type == "capital" else 4
            od.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r],
                      fill=alpha_color(accent, 220))

            # White center
            od.ellipse([px - 2, py - 2, px + 2, py + 2],
                      fill=(255, 255, 255, 230))

            # Label
            label = name
            if len(label) > 12:
                label = label[:11] + "."
            bbox = od.textbbox((0, 0), label, font=fonts["map_label_b"])
            tw = bbox[2] - bbox[0]
            label_x = px - tw // 2
            label_y = py - dot_r - 18

            # Label background
            od.rectangle([(label_x - 3, label_y - 1),
                          (label_x + tw + 3, label_y + 15)],
                         fill=(15, 15, 20, 180))
            od.text((label_x, label_y), label,
                    fill=alpha_color((240, 240, 240), 220),
                    font=fonts["map_label_b"])

        elif loc_type in ("city",):
            # Smaller dim dots for other cities
            od.ellipse([px - 2, py - 2, px + 2, py + 2],
                      fill=(120, 130, 140, 140))

    # "NIEDERSACHSEN" region label at top of map
    region_label = "NIEDERSACHSEN"
    bbox = od.textbbox((0, 0), region_label, font=fonts["map_region"])
    tw = bbox[2] - bbox[0]
    od.text((panel_x + panel_w // 2 - tw // 2, panel_y + 12),
            text=region_label,
            fill=alpha_color((170, 170, 180), 180),
            font=fonts["map_region"])

    # Compass rose (top-left corner of map)
    cx, cy = panel_x + 50, panel_y + 55
    # N arrow
    od.polygon([(cx, cy - 18), (cx - 5, cy), (cx + 5, cy)],
               fill=alpha_color((220, 70, 70), 200))
    od.polygon([(cx, cy + 18), (cx - 5, cy), (cx + 5, cy)],
               fill=alpha_color((140, 140, 150), 140))
    od.text((cx - 4, cy - 30), text="N",
            fill=alpha_color((210, 210, 210), 200), font=fonts["map_label"])

    # Scale bar (bottom of map)
    sb_x = panel_x + 30
    sb_y = panel_y + panel_h - 35
    # ~50km roughly = (MAP_LON_MAX - MAP_LON_MIN) * 0.5
    scale_len = int((panel_w - 60) * 0.2)
    od.line([(sb_x, sb_y), (sb_x + scale_len, sb_y)],
            fill=alpha_color((180, 180, 190), 160), width=1)
    od.line([(sb_x, sb_y - 3), (sb_x, sb_y + 3)],
            fill=alpha_color((180, 180, 190), 160), width=1)
    od.line([(sb_x + scale_len, sb_y - 3), (sb_x + scale_len, sb_y + 3)],
            fill=alpha_color((180, 180, 190), 160), width=1)
    od.text((sb_x + scale_len // 2 - 12, sb_y + 4), text="~50 km",
            fill=alpha_color((160, 160, 170), 160), font=fonts["map_label"])

    # Latitude/longitude grid lines (very subtle)
    for lon_deg in [9, 10, 11]:
        lon_frac = (lon_deg - MAP_LON_MIN) / (MAP_LON_MAX - MAP_LON_MIN)
        gx = panel_x + 30 + int(lon_frac * (panel_w - 60))
        od.line([(gx, panel_y + 40), (gx, panel_y + panel_h - 45)],
                fill=alpha_color((70, 70, 80), 40), width=1)
    for lat_deg in [52, 53]:
        lat_frac = 1.0 - (lat_deg - MAP_LAT_MIN) / (MAP_LAT_MAX - MAP_LAT_MIN)
        gy = panel_y + 40 + int(lat_frac * (panel_h - 85))
        od.line([(panel_x + 30, gy), (panel_x + panel_w - 30, gy)],
                fill=alpha_color((70, 70, 80), 40), width=1)


# ── Render Frame ─────────────────────────────────────────────────────────────
def render_frame(frame_idx, total_frames, scene, seg_idx, seg_progress,
                 fonts, accent_rgb,
                 bg_composited, bg_rgba, map_bg, divider_overlay,
                 particles, wrapped, scene_num, total_scenes, _dummy_draw):
    """Render one frame. Returns RGB PIL Image."""
    segments = scene.get("segments", [])
    num_segs = len(segments)
    accent = accent_rgb

    # ── Cross-segment fade ──
    if seg_progress > (1.0 - SEGMENT_CROSS_FADE) and seg_idx < num_segs - 1:
        cross_fade = (1.0 - seg_progress) / SEGMENT_CROSS_FADE
    elif seg_progress < SEGMENT_CROSS_FADE and seg_idx > 0:
        cross_fade = seg_progress / SEGMENT_CROSS_FADE
    else:
        cross_fade = 1.0
    cross_fade = max(0.0, min(1.0, cross_fade))

    # ── Background: pre-composited gradient+vignette (no per-frame lambda) ──
    img = bg_composited.copy()

    # ── Floating warm particles ──
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for p in particles:
        py_pos = (p["y_base"] - frame_idx * p["speed"]) % H
        pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.03 + p["phase"])
        a = int(p["brightness"] * pulse)
        s = int(p["size"] * (0.8 + 0.2 * pulse))
        od.ellipse([p["x"]-s, py_pos-s, p["x"]+s, py_pos+s],
                   fill=(255, 220, 180, min(255, a)))
    img_rgba = Image.alpha_composite(bg_rgba, overlay)

    # ── Determine if we're in title card phase ──
    first_seg_dur = segments[0].get("duration_s", 5.0)
    title_card_time = TITLE_CARD_DURATION / first_seg_dur
    in_title = (seg_idx == 0 and seg_progress < title_card_time)

    if in_title:
        # ═══ TITLE CARD ═══
        tp = seg_progress / title_card_time
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        # Full-screen dark overlay, fading in
        dark_a = int(200 * min(1.0, tp * 4))
        od.rectangle([(0, 0), (W, H)], fill=(0, 0, 0, dark_a))

        deco_a = max(0, min(255, int(255 * min(1.0, (tp - 0.1) * 5))))

        title = scene.get("title", "")
        title_bbox = od.textbbox((0, 0), title, font=fonts["title"])
        title_w = title_bbox[2] - title_bbox[0]
        cx = W // 2
        cy = H // 2 - 40

        # Top accent line
        if tp > 0.05:
            line_prog = min(1.0, (tp - 0.05) * 3)
            half_w = int(title_w * 0.7 * line_prog)
            od.line([(cx - half_w, cy - 50), (cx + half_w, cy - 50)],
                    fill=alpha_color(accent, deco_a), width=3)

        # Title text
        if tp > 0.1:
            text_a = min(255, int(255 * min(1.0, (tp - 0.1) * 5)))
            od.text((cx - title_w // 2, cy), title,
                    fill=alpha_color((255, 255, 255), text_a), font=fonts["title"])

        # Bottom accent line
        if tp > 0.2:
            line_prog2 = min(1.0, (tp - 0.2) * 3)
            half_w2 = int(title_w * 0.5 * line_prog2)
            od.line([(cx - half_w2, cy + 65), (cx + half_w2, cy + 65)],
                    fill=alpha_color(accent, deco_a), width=2)

        # Subtitle
        subtitle = scene.get("subtitle", "")
        if subtitle and tp > 0.25:
            sub_a = min(255, int(255 * min(1.0, (tp - 0.25) * 4)))
            sub_bbox = od.textbbox((0, 0), subtitle, font=fonts["subtitle"])
            sub_w = sub_bbox[2] - sub_bbox[0]
            od.text((cx - sub_w // 2, cy + 80), subtitle,
                    fill=alpha_color((200, 200, 200), sub_a), font=fonts["subtitle"])

        # Era text (small, top-left)
        era = scene.get("era", "")
        if era and tp > 0.3:
            era_a = min(255, int(255 * min(1.0, (tp - 0.3) * 4)))
            od.text((80, 80), era,
                    fill=alpha_color((150, 150, 150), era_a), font=fonts["era"])

        # Animated corner brackets
        if tp > 0.15:
            bracket_a = min(200, int(200 * min(1.0, (tp - 0.15) * 3)))
            bracket_len = int(60 * min(1.0, (tp - 0.15) * 2))
            bc = alpha_color(accent, bracket_a)
            margin = 60
            od.line([(margin, margin), (margin + bracket_len, margin)], fill=bc, width=2)
            od.line([(margin, margin), (margin, margin + bracket_len)], fill=bc, width=2)
            od.line([(W - margin, H - margin), (W - margin - bracket_len, H - margin)], fill=bc, width=2)
            od.line([(W - margin, H - margin), (W - margin, H - margin - bracket_len)], fill=bc, width=2)

        # Scene number indicator
        if tp > 0.4:
            num_a = min(180, int(180 * min(1.0, (tp - 0.4) * 3)))
            num_text = f"{scene_num} / {total_scenes}"
            od.text((W - 80, H - 60), num_text,
                    fill=alpha_color((120, 120, 120), num_a), font=fonts["tiny"],
                    anchor="rb")

        img_rgba = Image.alpha_composite(img_rgba, overlay)

    else:
        # ═══ NARRATION MODE — SPLIT LAYOUT ═══
        # ── LEFT PANEL: Procedural Map ──
        map_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        map_draw = ImageDraw.Draw(map_overlay)
        map_rgba = map_bg.copy()
        map_od = ImageDraw.Draw(map_rgba)

        draw_map_panel(
            map_draw, map_od,
            MAP_PANEL_X, MAP_PANEL_Y, MAP_PANEL_W, H,
            accent, frame_idx, scene_num, fonts
        )

        # Composite map_rgba onto map_overlay so map content is visible
        map_overlay.paste(map_rgba, (MAP_PANEL_X, MAP_PANEL_Y), map_rgba)

        # Vertical divider between map and text (pre-computed + accent line)
        map_draw.line([(MAP_PANEL_W, 0), (MAP_PANEL_W, H)],
                       fill=alpha_color(accent, 60), width=2)
        map_overlay = Image.alpha_composite(map_overlay, divider_overlay)

        img_rgba = Image.alpha_composite(img_rgba, map_overlay)

        # ── RIGHT PANEL: Narration text ──
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        seg_data = wrapped[seg_idx]
        words = seg_data["words"]

        # Subtle backdrop for text area
        od.rounded_rectangle(
            [(TEXT_PANEL_LEFT - 15, TEXT_TOP_MARGIN - 20),
             (TEXT_PANEL_RIGHT + 15, TEXT_TOP_MARGIN + MAX_VISIBLE_LINES * BODY_LINE_HEIGHT + 30)],
            radius=6, fill=(0, 0, 0, 80)
        )

        # Accent left border on text panel
        od.rectangle(
            [(TEXT_PANEL_LEFT - 15, TEXT_TOP_MARGIN - 10),
             (TEXT_PANEL_LEFT - 12, TEXT_TOP_MARGIN + MAX_VISIBLE_LINES * BODY_LINE_HEIGHT + 20)],
            fill=alpha_color(accent, 160)
        )

        # Word-by-word reveal
        total_words = len(words)
        words_to_show = int(seg_progress * total_words * 1.5)
        words_to_show = max(1, min(total_words, words_to_show))

        # Build revealed lines
        revealed_lines = []
        dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
        current = ""
        for word in words[:words_to_show]:
            test = current + (" " if current else "") + word
            bbox = dummy.textbbox((0, 0), test, font=fonts["body"])
            if bbox[2] - bbox[0] > TEXT_PANEL_W:
                if current:
                    revealed_lines.append(current)
                current = word
            else:
                current = test
        if current:
            revealed_lines.append(current)

        # Scroll if too many lines
        if len(revealed_lines) > MAX_VISIBLE_LINES:
            scroll_start = len(revealed_lines) - MAX_VISIBLE_LINES
            visible = revealed_lines[scroll_start:]
        else:
            visible = revealed_lines

        # Draw text lines
        text_a = int(255 * cross_fade)
        for i, line in enumerate(visible):
            y = TEXT_TOP_MARGIN + i * BODY_LINE_HEIGHT
            od.text((TEXT_PANEL_LEFT, y), line,
                    fill=(240, 240, 240, text_a), font=fonts["body"])

        # Cursor blink
        if words_to_show < total_words:
            cursor_visible = int(frame_idx * 0.1) % 2 == 0
            if cursor_visible and visible:
                last_line = visible[-1]
                bbox = _dummy_draw.textbbox((0, 0), last_line, font=fonts["body"])
                cursor_x = TEXT_PANEL_LEFT + (bbox[2] - bbox[0]) + 4
                cursor_y = TEXT_TOP_MARGIN + (len(visible) - 1) * BODY_LINE_HEIGHT
                od.rectangle([(cursor_x, cursor_y + 2),
                              (cursor_x + 2, cursor_y + BODY_FONT_SIZE)],
                             fill=alpha_color(accent, 200))

        # ── Bottom: segment progress bar ──
        bar_y = H - 50
        bar_h = 3
        od.rectangle([(TEXT_PANEL_LEFT, bar_y), (TEXT_PANEL_RIGHT, bar_y + bar_h)],
                      fill=(60, 60, 60, 100))
        fill_w = int(TEXT_PANEL_W * seg_progress)
        od.rectangle([(TEXT_PANEL_LEFT, bar_y), (TEXT_PANEL_LEFT + fill_w, bar_y + bar_h)],
                      fill=alpha_color(accent, 180))

        # ── Lower-third fact banners ──
        facts = scene.get("facts", [])
        fact_text, slide_prog, fact_visible = get_lower_third_state(frame_idx, facts)
        if fact_visible:
            draw_lower_third_banner(od, fact_text, slide_prog, accent, fonts)

        # ── Bottom-right: source citation watermark ──
        sources = scene.get("sources", [])
        draw_source_watermark(od, sources, accent, fonts)

        # ── Top-right: scene number ──
        num_text = f"{scene_num} / {total_scenes}"
        od.text((W - 40, 20), num_text,
                fill=(130, 130, 130, 200), font=fonts["tiny"], anchor="rt")

        # ── Top of text panel: era + title ──
        era = scene.get("era", "")
        if era:
            od.text((TEXT_PANEL_LEFT, 20), era,
                    fill=alpha_color(accent, 220), font=fonts["small"])
        title = scene.get("title", "")
        if title:
            od.text((TEXT_PANEL_LEFT, 45), title,
                    fill=alpha_color((220, 220, 220), 230), font=fonts["subtitle"])

        img_rgba = Image.alpha_composite(img_rgba, overlay)

    # ── Global overlays: timeline bar + thin progress bar at very bottom ──
    progress = frame_idx / max(total_frames - 1, 1)
    global_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(global_overlay)

    # Historical timeline bar
    draw_timeline_bar(gd, scene_num, total_scenes, accent, fonts)

    # Thin progress bar at very bottom
    gd.rectangle([(0, H - 3), (W, H)], fill=(30, 30, 30, 150))
    gd.rectangle([(0, H - 3), (int(W * progress), H)],
                  fill=alpha_color(accent, 200))
    img_rgba = Image.alpha_composite(img_rgba, global_overlay)

    return img_rgba.convert("RGB")


# ── Main Render ─────────────────────────────────────────────────────────────
def render_scene(scene_path, audio_path, output_path, fps=FPS):
    with open(scene_path) as f:
        scene = json.load(f)

    with wave.open(audio_path, "rb") as wf:
        audio_duration = wf.getnframes() / wf.getframerate()

    total_frames = int(audio_duration * fps)
    accent_rgb = hex_rgb(scene.get("accent", "#e94560"))
    gradient_colors = [hex_rgb(c) for c in scene.get("gradient",
                         ["#1a1a2e", "#16213e", "#0f3460"])]

    segments = scene.get("segments", [])
    seg_starts = []
    t = 0.0
    for seg in segments:
        seg_starts.append(t)
        t += seg.get("duration_s", 5.0)
    total_seg_duration = t
    time_scale = audio_duration / total_seg_duration if total_seg_duration > 0 else 1.0

    fonts = get_fonts()

    # Pre-compute
    print("  Pre-computing assets...", end=" ", flush=True)
    t0 = time.time()
    bg_composited = make_bg_composited(W, H, gradient_colors, vignette_strength=0.5, dark_factor=0.85)
    bg_rgba = bg_composited.convert("RGBA")
    map_bg = make_map_bg(MAP_PANEL_W, H)
    divider_overlay = make_divider_gradient(W, H, MAP_PANEL_W, fade_width=20)
    particles = precompute_particles(PARTICLE_COUNT, W, H,
                                       seed=scene.get("scene_num", 0) * 137)
    wrapped = prewrap_text(segments, fonts["body"], TEXT_PANEL_W)
    scene_num = scene.get("scene_num", 1)
    total_scenes = scene.get("total_scenes", 28)
    # Reusable 1x1 ImageDraw for text measurement
    _dummy_draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    print(f"{time.time() - t0:.1f}s")

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-profile:v", "main", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        output_path,
    ]

    print(f"Rendering scene {scene_num}: {total_frames} frames, {audio_duration:.1f}s")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t_start = time.time()

    for frame_idx in range(total_frames):
        t_sec = frame_idx / fps * time_scale

        seg_idx = len(segments) - 1
        for i, start in enumerate(seg_starts):
            if t_sec < (start + segments[i].get("duration_s", 5.0)) * time_scale:
                seg_idx = i
                break

        seg_elapsed = t_sec - seg_starts[seg_idx] * time_scale
        seg_dur = segments[seg_idx].get("duration_s", 5.0) * time_scale
        seg_progress = seg_elapsed / max(seg_dur, 0.001)

        img = render_frame(
            frame_idx, total_frames, scene,
            seg_idx, seg_progress,
            fonts, accent_rgb,
            bg_composited, bg_rgba, map_bg, divider_overlay,
            particles, wrapped,
            scene_num, total_scenes, _dummy_draw,
        )
        proc.stdin.write(img.tobytes())

        if frame_idx > 0 and frame_idx % 100 == 0:
            elapsed = time.time() - t_start
            fps_now = frame_idx / elapsed
            eta = (total_frames - frame_idx) / max(fps_now, 0.1)
            print(f"  Frame {frame_idx}/{total_frames} ({fps_now:.1f} fps, ETA {eta:.0f}s)")

    proc.stdin.close()
    proc.wait()
    err = proc.stderr.read()
    elapsed = time.time() - t_start

    if proc.returncode != 0:
        print(f"ffmpeg error: {err.decode()[-500:]}", file=sys.stderr)
        sys.exit(1)

    size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({size / 1_048_576:.1f} MB, {elapsed:.1f}s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-json", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fps", type=int, default=FPS)
    args = parser.parse_args()
    render_scene(args.scene_json, args.audio, args.output, args.fps)


if __name__ == "__main__":
    main()
