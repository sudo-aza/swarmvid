"""Map focus treatment — full-width map with narration text overlaid.

The map takes the full frame width with text panel floating on top
as a semi-transparent card. Good for scenes about geography, trade routes,
battles with troop movements."""

from __future__ import annotations

import math
from PIL import Image, ImageDraw

from visuals.colors import alpha_color
from visuals.compositing import make_bg_composited
from visuals.fonts import (
    W, H, TEXT_TOP_MARGIN, MAX_VISIBLE_LINES, BODY_LINE_HEIGHT, BODY_FONT_SIZE,
)
from visuals.map_panel import geo_to_map, HANNOVER_LOCATIONS, LEINE_RIVER, WESER_RIVER, ALLER_RIVER
from visuals.map_panel import ROAD_CONNECTIONS, LOWER_SAXONY_BORDER, SCENE_LOCATIONS
from visuals.map_panel import MAP_LON_MIN, MAP_LON_MAX, MAP_LAT_MIN, MAP_LAT_MAX
from visuals.particles import precompute_particles, draw_particles
from visuals.typography import (
    prewrap_text, draw_word_reveal, draw_cursor_blink,
    draw_lower_third_banner, draw_source_watermark,
    get_lower_third_state,
)
from visuals.treatments.base import TreatmentBase, RenderContext, draw_global_overlays

class MapFocusTreatment(TreatmentBase):
    """Full-width map with floating text overlay card. For geographic scenes."""

    name = "map_focus"
    description = "Full-width map with floating semi-transparent text card"

    def prepare(self, ctx: RenderContext) -> None:
        parsed = []
        for c in ctx.scene.get("gradient", ["#0a1628", "#0d1f3c", "#102848"]):
            c = c.lstrip("#")
            parsed.append(tuple(int(c[i:i+2], 16) for i in (0, 2, 4)))

        ctx.bg_composited = make_bg_composited(W, H, parsed, vignette_strength=0.4, dark_factor=0.75)
        ctx.bg_rgba = ctx.bg_composited.convert("RGBA")
        ctx.particles = precompute_particles(
            10, W, H, seed=ctx.scene.get("scene_num", 0) * 137,
            style="dust"
        )
        ctx.wrapped = prewrap_text(
            ctx.scene.get("segments", []), ctx.fonts["body"], 550  # narrower text in overlay
        )

    def render_frame(self, ctx: RenderContext, frame_idx: int,
                     total_frames: int, seg_idx: int,
                     seg_progress: float, cross_fade: float) -> Image.Image:
        accent = ctx.accent_rgb

        img = ctx.bg_composited.copy()

        # ── FULL-WIDTH MAP ──
        map_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        map_draw = ImageDraw.Draw(map_overlay)
        map_od = ImageDraw.Draw(map_overlay)  # draw directly on overlay for full-width

        # Dark base
        for y_row in range(H):
            t = y_row / H
            darkness = int(12 + 6 * t)
            map_draw.line([(0, y_row), (W - 1, y_row)],
                  fill=(darkness, darkness, darkness + 3))

        # Border
        map_od.rectangle([(1, 1), (W - 2, H - 2)],
                        outline=alpha_color(accent, 60), width=1)

        # Lower Saxony border (full-width coords)
        border_px = [geo_to_map(lon, lat, 0, 0, W, H, padding=40)
                     for lon, lat in LOWER_SAXONY_BORDER]
        if len(border_px) > 2:
            map_od.polygon(border_px, outline=alpha_color(accent, 50), fill=alpha_color(accent, 8))

        # Rivers (full-width)
        for river_path, color, width in [
            (LEINE_RIVER, (50, 100, 160, 140), 4),
            (WESER_RIVER, (40, 80, 130, 80), 3),
            (ALLER_RIVER, (40, 80, 130, 60), 2),
        ]:
            rpx = [geo_to_map(lon, lat, 0, 0, W, H, padding=40)
                   for lon, lat in river_path]
            if len(rpx) > 1:
                for i in range(len(rpx) - 1):
                    dash = (frame_idx * 0.02 + i * 0.15) % 1.0
                    if dash < 0.7 or river_path is not LEINE_RIVER:
                        map_od.line([rpx[i], rpx[i+1]], fill=color, width=width)
                # Glow for main river
                if river_path is LEINE_RIVER:
                    for i in range(len(rpx) - 1):
                        map_od.line([rpx[i], rpx[i+1]], fill=(60, 120, 190, 40), width=9)

        # Roads
        for city_a, city_b in ROAD_CONNECTIONS:
            if city_a in HANNOVER_LOCATIONS and city_b in HANNOVER_LOCATIONS:
                ax, ay = geo_to_map(HANNOVER_LOCATIONS[city_a]["lon"],
                                   HANNOVER_LOCATIONS[city_a]["lat"], 0, 0, W, H, padding=40)
                bx, by = geo_to_map(HANNOVER_LOCATIONS[city_b]["lon"],
                                   HANNOVER_LOCATIONS[city_b]["lat"], 0, 0, W, H, padding=40)
                map_od.line([(ax, ay), (bx, by)],
                           fill=alpha_color((100, 100, 110), 60), width=1)

        # City markers
        highlight_names = SCENE_LOCATIONS.get(ctx.scene_num, ["Hannover"])
        for name, loc in HANNOVER_LOCATIONS.items():
            px, py = geo_to_map(loc["lon"], loc["lat"], 0, 0, W, H, padding=40)
            is_highlight = name in highlight_names
            loc_type = loc["type"]

            if is_highlight:
                pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.05)
                glow_r = int(14 + 8 * pulse)
                map_od.ellipse([px - glow_r, py - glow_r, px + glow_r, py + glow_r],
                             fill=alpha_color(accent, int(25 + 20 * pulse)))
                dot_r = 7 if loc_type == "capital" else 5
                map_od.ellipse([px - dot_r, py - dot_r, px + dot_r, py + dot_r],
                             fill=alpha_color(accent, 220))
                map_od.ellipse([px - 2, py - 2, px + 2, py + 2],
                             fill=(255, 255, 255, 230))
                label = name if len(name) <= 14 else name[:13] + "."
                bbox = map_od.textbbox((0, 0), label, font=ctx.fonts["map_label_b"])
                tw = bbox[2] - bbox[0]
                map_od.rectangle([(px - tw // 2 - 3, py - dot_r - 20),
                                (px + tw // 2 + 3, py - dot_r - 3)],
                               fill=(10, 10, 15, 200))
                map_od.text((px - tw // 2, py - dot_r - 19), label,
                           fill=alpha_color((240, 240, 240), 230), font=ctx.fonts["map_label_b"])
            elif loc_type == "city":
                map_od.ellipse([px - 2, py - 2, px + 2, py + 2],
                             fill=(120, 130, 140, 160))
                short = name if len(name) <= 10 else name[:9] + "."
                bbox = map_od.textbbox((0, 0), short, font=ctx.fonts["map_label"])
                tw = bbox[2] - bbox[0]
                map_od.text((px - tw // 2, py + 5), short,
                           fill=alpha_color((140, 140, 150), 140), font=ctx.fonts["map_label"])

        # "NIEDERSACHSEN" label
        rl = "NIEDERSACHSEN"
        bbox = map_od.textbbox((0, 0), rl, font=ctx.fonts["map_region"])
        tw = bbox[2] - bbox[0]
        map_od.text((W // 2 - tw // 2, 15), text=rl,
                    fill=alpha_color((170, 170, 180), 160), font=ctx.fonts["map_region"])

        img_rgba = Image.alpha_composite(ctx.bg_rgba, map_overlay)

        # ── FLOATING TEXT CARD (bottom-right) ──
        card_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(card_overlay)

        card_x = 640
        card_y = H - 280
        card_w = W - card_x - 40
        card_h = 240

        # Card background
        od.rounded_rectangle(
            [(card_x, card_y), (card_x + card_w, card_y + card_h)],
            radius=8, fill=(10, 12, 18, 200)
        )
        od.line([(card_x, card_y), (card_x + card_w, card_y)],
                fill=alpha_color(accent, 120), width=2)

        # Era + title inside card
        era = ctx.scene.get("era", "")
        if era:
            od.text((card_x + 15, card_y + 10), era,
                    fill=alpha_color(accent, 200), font=ctx.fonts["small"])
        title = ctx.scene.get("title", "")
        if title:
            od.text((card_x + 15, card_y + 30), title,
                    fill=alpha_color((220, 220, 220), 220), font=ctx.fonts["subtitle"])

        # Word reveal inside card
        if seg_idx < len(ctx.wrapped):
            seg_data = ctx.wrapped[seg_idx]
            text_a = int(255 * cross_fade)
            draw_word_reveal(
                od, seg_data, seg_progress,
                card_x + 15, card_y + 65, card_w - 30,
                5, BODY_LINE_HEIGHT - 2, BODY_FONT_SIZE - 2,
                ctx.fonts["body"], ctx.fonts["body"],
                text_color=(235, 235, 235, text_a),
                dummy_draw=ctx.dummy_draw,
            )

        # Lower-thirds
        facts = ctx.scene.get("facts", [])
        ft, sp, fv = get_lower_third_state(frame_idx, facts)
        if fv:
            draw_lower_third_banner(od, ft, sp, accent, ctx.fonts,
                                    card_x + 15, card_y + card_h - 55, max_width=card_w - 30)

        # Source watermark
        sources = ctx.scene.get("sources", [])
        draw_source_watermark(od, sources, accent, ctx.fonts, W, H - 60)

        # Scene counter
        od.text((W - 40, 20), f"{ctx.scene_num} / {ctx.total_scenes}",
                fill=(150, 150, 150, 200), font=ctx.fonts["tiny"], anchor="rt")

        img_rgba = Image.alpha_composite(img_rgba, card_overlay)

        # Global overlays
        global_ov = draw_global_overlays(ctx, frame_idx, total_frames)
        img_rgba = Image.alpha_composite(img_rgba, global_ov)

        return img_rgba.convert("RGB")
