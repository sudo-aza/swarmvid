"""Procedural map of the Hannover / Lower Saxony region."""

from __future__ import annotations

import math
from PIL import Image, ImageDraw


# ── Geographic data ──────────────────────────────────────────────────────────────
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

LEINE_RIVER = [
    (9.75, 52.6), (9.70, 52.5), (9.72, 52.4), (9.74, 52.37),
    (9.73, 52.35), (9.73, 52.3), (9.74, 52.2), (9.75, 52.15),
    (9.80, 52.0), (9.85, 51.8),
]

WESER_RIVER = [
    (9.15, 52.85), (9.10, 52.75), (9.08, 52.65), (9.10, 52.55),
    (9.12, 52.45), (9.15, 52.35), (9.18, 52.25), (9.20, 52.15),
    (9.22, 52.05), (9.25, 51.9),
]

ALLER_RIVER = [
    (9.60, 52.9), (9.65, 52.8), (9.68, 52.7), (9.72, 52.6),
    (9.75, 52.6),
]

ROAD_CONNECTIONS = [
    ("Hannover", "Hildesheim"), ("Hannover", "Braunschweig"),
    ("Hannover", "Celle"), ("Hannover", "Hameln"),
    ("Hannover", "Lehrte"), ("Hannover", "Wunstorf"),
    ("Hannover", "Langenhagen"), ("Braunschweig", "Wolfsburg"),
    ("Hildesheim", "Gottingen"), ("Celle", "Nienburg"),
    ("Hameln", "Nienburg"),
]

LOWER_SAXONY_BORDER = [
    (8.9, 53.1), (9.0, 52.9), (8.9, 52.7), (8.9, 52.5), (8.9, 52.3),
    (9.0, 52.1), (9.1, 52.0), (9.3, 51.9), (9.5, 51.85), (9.8, 51.8),
    (10.1, 51.8), (10.4, 51.85), (10.6, 51.9), (10.8, 52.0), (11.0, 52.1),
    (11.0, 52.3), (10.9, 52.5), (10.8, 52.7), (10.7, 52.9), (10.5, 53.1),
    (10.3, 53.2), (10.0, 53.2), (9.7, 53.2), (9.4, 53.2), (9.2, 53.2),
    (9.0, 53.15), (8.9, 53.1),
]

SCENE_LOCATIONS = {
    1: ["Hannover"], 2: ["Hannover", "Hildesheim"],
    3: ["Hannover", "Hildesheim", "Braunschweig"], 4: ["Hannover"],
    5: ["Hannover", "Celle"], 6: ["Hannover", "Hildesheim", "Braunschweig"],
    7: ["Hannover", "Lehrte", "Langenhagen"], 8: ["Hannover"],
    9: ["Hannover", "Hildesheim"], 10: ["Hannover", "Laatzen", "Springe"],
    11: ["Hannover"], 12: ["Hannover"], 13: ["Hannover", "Lehrte"],
    14: ["Hannover"], 15: ["Hannover", "Langenhagen", "Garbsen"],
    16: ["Hannover", "Braunschweig", "Wolfsburg"], 17: ["Hannover"],
    18: ["Hannover"], 19: ["Hannover", "Hildesheim"], 20: ["Hannover", "Laatzen"],
    21: ["Hannover"], 22: ["Hannover", "Celle", "Nienburg"], 23: ["Hannover"],
    24: ["Hannover"], 25: ["Hannover"], 26: ["Hannover", "Braunschweig"],
    27: ["Hannover"], 28: ["Hannover"],
}


# ── Utilities ─────────────────────────────────────────────────────────────────

def geo_to_map(lon: float, lat: float,
               panel_x: int, panel_y: int,
               panel_w: int, panel_h: int,
               padding: int = 30) -> tuple[int, int]:
    """Convert geographic coordinates to pixel position within the map panel."""
    t = (lon - MAP_LON_MIN) / (MAP_LON_MAX - MAP_LON_MIN)
    u = 1.0 - (lat - MAP_LAT_MIN) / (MAP_LAT_MAX - MAP_LAT_MIN)
    x = panel_x + padding + t * (panel_w - 2 * padding)
    y = panel_y + padding + u * (panel_h - 2 * padding)
    return int(x), int(y)


def make_map_bg(panel_w: int, panel_h: int) -> Image.Image:
    """Pre-compute the map panel dark background gradient (RGBA)."""
    bg = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bg)
    for y_row in range(panel_h):
        t = y_row / panel_h
        darkness = int(18 + 8 * t)
        draw.line([(0, y_row), (panel_w - 1, y_row)],
                  fill=(darkness, darkness, darkness + 5, 255))
    return bg


def draw_map_panel(draw: ImageDraw.ImageDraw, od: ImageDraw.ImageDraw,
                   panel_x: int, panel_y: int,
                   panel_w: int, panel_h: int,
                   accent: tuple, frame_idx: int,
                   scene_num: int, fonts: dict) -> None:
    """Draw the documentary-style map onto RGBA overlays."""
    from visuals.colors import alpha_color

    # Dark panel background
    for y_row in range(panel_h):
        t = y_row / panel_h
        darkness = int(18 + 8 * t)
        draw.line([(panel_x, panel_y + y_row), (panel_x + panel_w - 1, panel_y + y_row)],
                  fill=(darkness, darkness, darkness + 5))

    # Border
    od.rectangle(
        [(panel_x + 1, panel_y + 1), (panel_x + panel_w - 2, panel_y + panel_h - 2)],
        outline=alpha_color(accent, 100), width=1
    )

    # Lower Saxony border
    border_px = [geo_to_map(lon, lat, panel_x, panel_y, panel_w, panel_h)
                 for lon, lat in LOWER_SAXONY_BORDER]
    if len(border_px) > 2:
        od.polygon(border_px, outline=alpha_color(accent, 80), fill=None)

    # River Leine (animated)
    river_px = [geo_to_map(lon, lat, panel_x, panel_y, panel_w, panel_h)
                for lon, lat in LEINE_RIVER]
    if len(river_px) > 1:
        river_color = (50, 100, 160, 140)
        for i in range(len(river_px) - 1):
            dash_phase = (frame_idx * 0.02 + i * 0.15) % 1.0
            if dash_phase < 0.7:
                od.line([river_px[i], river_px[i + 1]], fill=river_color, width=3)
        river_glow = (60, 120, 190, 60)
        for i in range(len(river_px) - 1):
            od.line([river_px[i], river_px[i + 1]], fill=river_glow, width=7)

    # Secondary rivers
    for river_path in [WESER_RIVER, ALLER_RIVER]:
        rpx = [geo_to_map(lon, lat, panel_x, panel_y, panel_w, panel_h)
               for lon, lat in river_path]
        if len(rpx) > 1:
            for i in range(len(rpx) - 1):
                od.line([rpx[i], rpx[i + 1]], fill=(40, 80, 130, 130), width=2)

    # Roads
    for city_a, city_b in ROAD_CONNECTIONS:
        if city_a in HANNOVER_LOCATIONS and city_b in HANNOVER_LOCATIONS:
            ax, ay = geo_to_map(HANNOVER_LOCATIONS[city_a]["lon"],
                               HANNOVER_LOCATIONS[city_a]["lat"],
                               panel_x, panel_y, panel_w, panel_h)
            bx, by = geo_to_map(HANNOVER_LOCATIONS[city_b]["lon"],
                               HANNOVER_LOCATIONS[city_b]["lat"],
                               panel_x, panel_y, panel_w, panel_h)
            od.line([(ax, ay), (bx, by)],
                    fill=alpha_color((80, 80, 90), 90), width=1)

    # Location markers
    highlight_names = SCENE_LOCATIONS.get(scene_num, ["Hannover"])
    for name, loc in HANNOVER_LOCATIONS.items():
        px, py = geo_to_map(loc["lon"], loc["lat"],
                             panel_x, panel_y, panel_w, panel_h)
        is_highlight = name in highlight_names
        loc_type = loc["type"]

        if is_highlight:
            pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.05)
            glow_r = int(12 + 6 * pulse)
            od.ellipse([px - glow_r, py - glow_r, px + glow_r, py + glow_r],
                      fill=alpha_color(accent, int(30 + 20 * pulse)))
            dot_r = 6 if loc_type == "capital" else 4
            od.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r],
                      fill=alpha_color(accent, 220))
            od.ellipse([px - 2, py - 2, px + 2, py + 2],
                      fill=(255, 255, 255, 230))
            label = name if len(name) <= 12 else name[:11] + "."
            bbox = od.textbbox((0, 0), label, font=fonts["map_label_b"])
            tw = bbox[2] - bbox[0]
            label_x = px - tw // 2
            label_y = py - dot_r - 18
            od.rectangle([(label_x - 3, label_y - 1), (label_x + tw + 3, label_y + 15)],
                         fill=(15, 15, 20, 180))
            od.text((label_x, label_y), label,
                    fill=alpha_color((240, 240, 240), 220), font=fonts["map_label_b"])
        elif loc_type == "city":
            od.ellipse([px - 2, py - 2, px + 2, py + 2],
                      fill=(120, 130, 140, 140))
            short = name if len(name) <= 10 else name[:9] + "."
            bbox = od.textbbox((0, 0), short, font=fonts["map_label"])
            tw = bbox[2] - bbox[0]
            od.text((px - tw // 2, py + 5), short,
                    fill=alpha_color((130, 130, 140), 120), font=fonts["map_label"])

    # "NIEDERSACHSEN" label
    region_label = "NIEDERSACHSEN"
    bbox = od.textbbox((0, 0), region_label, font=fonts["map_region"])
    tw = bbox[2] - bbox[0]
    od.text((panel_x + panel_w // 2 - tw // 2, panel_y + 12),
            text=region_label, fill=alpha_color((170, 170, 180), 180),
            font=fonts["map_region"])

    # Compass rose
    cx, cy = panel_x + 50, panel_y + 55
    od.polygon([(cx, cy - 18), (cx - 5, cy), (cx + 5, cy)],
               fill=alpha_color((220, 70, 70), 200))
    od.polygon([(cx, cy + 18), (cx - 5, cy), (cx + 5, cy)],
               fill=alpha_color((140, 140, 150), 140))
    od.text((cx - 4, cy - 30), text="N",
            fill=alpha_color((210, 210, 210), 200), font=fonts["map_label"])

    # Scale bar
    sb_x = panel_x + 30
    sb_y = panel_y + panel_h - 35
    scale_len = int((panel_w - 60) * 0.2)
    od.line([(sb_x, sb_y), (sb_x + scale_len, sb_y)],
            fill=alpha_color((180, 180, 190), 160), width=1)
    od.line([(sb_x, sb_y - 3), (sb_x, sb_y + 3)],
            fill=alpha_color((180, 180, 190), 160), width=1)
    od.line([(sb_x + scale_len, sb_y - 3), (sb_x + scale_len, sb_y + 3)],
            fill=alpha_color((180, 180, 190), 160), width=1)
    od.text((sb_x + scale_len // 2 - 12, sb_y + 4), text="~50 km",
            fill=alpha_color((160, 160, 170), 160), font=fonts["map_label"])

    # Lat/lon grid
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
