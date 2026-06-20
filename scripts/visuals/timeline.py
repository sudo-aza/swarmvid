"""Historical era timeline bar — shared overlay component."""

from __future__ import annotations

from PIL import ImageDraw

from visuals.colors import alpha_color

# ── Era definitions ───────────────────────────────────────────────────────────
ERA_DEFINITION = [
    {"label": "Mittelalter",          "range": "800-1500",  "scenes": [1, 2, 3, 4, 5]},
    {"label": "Renaissance",          "range": "1500-1600", "scenes": [6, 7, 8]},
    {"label": "Drei\u00dfigj\u00e4hriger Krieg", "range": "1618-1648", "scenes": [9, 10, 11]},
    {"label": "Barock",               "range": "1648-1714", "scenes": [12, 13, 14]},
    {"label": "Kurf\u00fcrstentum",   "range": "1692-1814", "scenes": [15, 16, 17]},
    {"label": "K\u00f6nigreich",      "range": "1814-1866", "scenes": [18, 19, 20, 21]},
    {"label": "Preu\u00dfen",         "range": "1866-1918", "scenes": [22, 23, 24]},
    {"label": "Weimar & NS",          "range": "1918-1945", "scenes": [25, 26]},
    {"label": "Nachkriegszeit",       "range": "1945-2000", "scenes": [27, 28]},
]

# ── Layout constants ────────────────────────────────────────────────────────────
TIMELINE_BAR_MARGIN = 60
TIMELINE_NODE_R = 4
TIMELINE_BAR_H = 20


def draw_timeline_bar(od: ImageDraw.ImageDraw, scene_num: int,
                      total_scenes: int, accent: tuple,
                      fonts: dict, w: int, h: int) -> None:
    """Draw the historical era timeline at the bottom of a frame."""
    bar_left = TIMELINE_BAR_MARGIN
    bar_right = w - TIMELINE_BAR_MARGIN
    bar_w = bar_right - bar_left
    bar_top = h - 32 - TIMELINE_BAR_H // 2

    # Background strip
    od.rounded_rectangle(
        [(bar_left - 10, bar_top - 4), (bar_right + 10, bar_top + TIMELINE_BAR_H + 4)],
        radius=4, fill=(0, 0, 0, 160)
    )

    # Compute x positions for each scene node
    total = total_scenes
    scene_x = {}
    for s in range(1, total + 1):
        frac = (s - 1) / max(total - 1, 1)
        scene_x[s] = bar_left + int(frac * bar_w)

    # Era segments
    for era in ERA_DEFINITION:
        era_scenes = era["scenes"]
        if not era_scenes:
            continue
        first_s, last_s = era_scenes[0], era_scenes[-1]
        x1 = scene_x.get(first_s, bar_left)
        x2 = scene_x.get(last_s, bar_right)

        od.rectangle(
            [(x1, bar_top + 2), (x2, bar_top + TIMELINE_BAR_H - 2)],
            fill=alpha_color(accent, 20)
        )

        era_center_x = (x1 + x2) // 2
        label_text = era["label"]
        if len(label_text) > 16:
            label_text = label_text[:15] + "."
        bbox = od.textbbox((0, 0), label_text, font=fonts["timeline_label"])
        tw = bbox[2] - bbox[0]
        if x2 - x1 > tw + 10:
            od.text((era_center_x - tw // 2, bar_top - 15), label_text,
                    fill=alpha_color((180, 180, 190), 180),
                    font=fonts["timeline_label"])

    # Main timeline line
    od.line([(bar_left, bar_top + TIMELINE_BAR_H // 2),
             (bar_right, bar_top + TIMELINE_BAR_H // 2)],
            fill=alpha_color((120, 120, 130), 180), width=1)

    # Scene nodes
    for s in range(1, total + 1):
        x = scene_x[s]
        y = bar_top + TIMELINE_BAR_H // 2
        r = TIMELINE_NODE_R
        if s == scene_num:
            od.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3],
                      fill=alpha_color(accent, 90))
            od.ellipse([x - r, y - r, x + r, y + r],
                      fill=alpha_color(accent, 240))
            od.ellipse([x - 1, y - 1, x + 1, y + 1],
                      fill=(255, 255, 255, 230))
        elif s < scene_num:
            od.ellipse([x - r + 1, y - r + 1, x + r - 1, y + r - 1],
                      fill=alpha_color(accent, 80))
        else:
            od.ellipse([x - r + 1, y - r + 1, x + r - 1, y + r - 1],
                      fill=(60, 60, 70, 80))
