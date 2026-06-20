"""Default split treatment — map panel (left) + narration text (right).

This is the current renderer behavior: dark vignette background, procedural map
on the left 520px, word-by-word narration text on the right, with title card
intro, lower-third fact banners, and source watermark."""

from __future__ import annotations

import math
from PIL import Image, ImageDraw

from visuals.colors import alpha_color
from visuals.compositing import make_bg_composited
from visuals.map_panel import make_map_bg
from visuals.fonts import (
    W, H, MAP_PANEL_W, TEXT_PANEL_LEFT, TEXT_PANEL_RIGHT, TEXT_PANEL_W,
    TEXT_TOP_MARGIN, MAX_VISIBLE_LINES, BODY_LINE_HEIGHT, BODY_FONT_SIZE,
    TITLE_CARD_DURATION, SEGMENT_CROSS_FADE,
)
from visuals.particles import precompute_particles, draw_particles
from visuals.typography import (
    prewrap_text, draw_word_reveal, draw_cursor_blink,
    draw_lower_third_banner, draw_source_watermark,
    get_lower_third_state,
)
from visuals.treatments.base import TreatmentBase, RenderContext, draw_global_overlays


def _divider_gradient(w, h, divider_x, fade_width=20):
    """Pre-compute the vertical divider + fade gradient."""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for fade_x in range(divider_x, divider_x + fade_width):
        fade_a = int(60 * (1.0 - (fade_x - divider_x) / fade_width))
        draw.line([(fade_x, 0), (fade_x, h)],
                  fill=(15, 15, 20, fade_a))
    return overlay


class DefaultSplitTreatment(TreatmentBase):
    """Map + narration split layout. The workhorse treatment."""

    name = "default"
    description = "Split layout: procedural map (left) + narration text (right)"

    def prepare(self, ctx: RenderContext) -> None:
        parsed = []
        for c in ctx.scene.get("gradient", ["#1a1a2e", "#16213e", "#0f3460"]):
            c = c.lstrip("#")
            parsed.append(tuple(int(c[i:i+2], 16) for i in (0, 2, 4)))

        ctx.bg_composited = make_bg_composited(W, H, parsed)
        ctx.bg_rgba = ctx.bg_composited.convert("RGBA")
        ctx.extra["map_bg"] = make_map_bg(MAP_PANEL_W, H)
        ctx.extra["divider_overlay"] = _divider_gradient(W, H, MAP_PANEL_W)
        ctx.particles = precompute_particles(
            30, W, H, seed=ctx.scene.get("scene_num", 0) * 137,
            style="warm_glow"
        )
        ctx.wrapped = prewrap_text(ctx.scene.get("segments", []), ctx.fonts["body"], TEXT_PANEL_W)

    def render_frame(self, ctx: RenderContext, frame_idx: int,
                     total_frames: int, seg_idx: int,
                     seg_progress: float, cross_fade: float) -> Image.Image:
        from visuals.map_panel import draw_map_panel

        scene = ctx.scene
        accent = ctx.accent_rgb
        segments = scene.get("segments", [])
        num_segs = len(segments)

        # Background
        img = ctx.bg_composited.copy()

        # Particles
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        draw_particles(od, ctx.particles, frame_idx, H)
        img_rgba = Image.alpha_composite(ctx.bg_rgba, overlay)

        # Title card vs narration mode
        first_seg_dur = segments[0].get("duration_s", 5.0)
        title_card_time = TITLE_CARD_DURATION / first_seg_dur
        in_title = (seg_idx == 0 and seg_progress < title_card_time)

        if in_title:
            img_rgba = self._draw_title_card(ctx, img_rgba, frame_idx, seg_progress, title_card_time)
        else:
            img_rgba = self._draw_narration(ctx, img_rgba, frame_idx, seg_idx, seg_progress, cross_fade)

        # Global overlays (timeline, progress bar)
        global_ov = draw_global_overlays(ctx, frame_idx, total_frames)
        img_rgba = Image.alpha_composite(img_rgba, global_ov)

        return img_rgba.convert("RGB")

    def _draw_title_card(self, ctx, img_rgba, frame_idx, seg_progress, title_card_time):
        accent = ctx.accent_rgb
        tp = seg_progress / title_card_time

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        dark_a = int(200 * min(1.0, tp * 4))
        od.rectangle([(0, 0), (W, H)], fill=(0, 0, 0, dark_a))

        deco_a = max(0, min(255, int(255 * min(1.0, (tp - 0.1) * 5))))

        title = ctx.scene.get("title", "")
        title_bbox = od.textbbox((0, 0), title, font=ctx.fonts["title"])
        title_w = title_bbox[2] - title_bbox[0]
        cx = W // 2
        cy = H // 2 - 40

        if tp > 0.05:
            line_prog = min(1.0, (tp - 0.05) * 3)
            half_w = int(title_w * 0.7 * line_prog)
            od.line([(cx - half_w, cy - 50), (cx + half_w, cy - 50)],
                    fill=alpha_color(accent, deco_a), width=3)

        if tp > 0.1:
            text_a = min(255, int(255 * min(1.0, (tp - 0.1) * 5)))
            od.text((cx - title_w // 2, cy), title,
                    fill=alpha_color((255, 255, 255), text_a), font=ctx.fonts["title"])

        if tp > 0.2:
            line_prog2 = min(1.0, (tp - 0.2) * 3)
            half_w2 = int(title_w * 0.5 * line_prog2)
            od.line([(cx - half_w2, cy + 65), (cx + half_w2, cy + 65)],
                    fill=alpha_color(accent, deco_a), width=2)

        subtitle = ctx.scene.get("subtitle", "")
        if subtitle and tp > 0.25:
            sub_a = min(255, int(255 * min(1.0, (tp - 0.25) * 4)))
            sub_bbox = od.textbbox((0, 0), subtitle, font=ctx.fonts["subtitle"])
            sub_w = sub_bbox[2] - sub_bbox[0]
            od.text((cx - sub_w // 2, cy + 80), subtitle,
                    fill=alpha_color((200, 200, 200), sub_a), font=ctx.fonts["subtitle"])

        era = ctx.scene.get("era", "")
        if era and tp > 0.3:
            era_a = min(255, int(255 * min(1.0, (tp - 0.3) * 4)))
            od.text((80, 80), era,
                    fill=alpha_color((150, 150, 150), era_a), font=ctx.fonts["era"])

        if tp > 0.15:
            bracket_a = min(200, int(200 * min(1.0, (tp - 0.15) * 3)))
            bracket_len = int(60 * min(1.0, (tp - 0.15) * 2))
            bc = alpha_color(accent, bracket_a)
            margin = 60
            od.line([(margin, margin), (margin + bracket_len, margin)], fill=bc, width=2)
            od.line([(margin, margin), (margin, margin + bracket_len)], fill=bc, width=2)
            od.line([(W - margin, H - margin), (W - margin - bracket_len, H - margin)], fill=bc, width=2)
            od.line([(W - margin, H - margin), (W - margin, H - margin - bracket_len)], fill=bc, width=2)

        if tp > 0.4:
            num_a = min(180, int(180 * min(1.0, (tp - 0.4) * 3)))
            num_text = f"{ctx.scene_num} / {ctx.total_scenes}"
            od.text((W - 80, H - 60), num_text,
                    fill=alpha_color((120, 120, 120), num_a), font=ctx.fonts["tiny"],
                    anchor="rb")

        return Image.alpha_composite(img_rgba, overlay)

    def _draw_narration(self, ctx, img_rgba, frame_idx, seg_idx, seg_progress, cross_fade):
        from visuals.map_panel import draw_map_panel

        accent = ctx.accent_rgb

        # ── LEFT PANEL: Map ──
        map_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        map_draw = ImageDraw.Draw(map_overlay)
        map_rgba = ctx.extra["map_bg"].copy()
        map_od = ImageDraw.Draw(map_rgba)

        draw_map_panel(map_draw, map_od, 0, 0, MAP_PANEL_W, H,
                       accent, frame_idx, ctx.scene_num, ctx.fonts)
        map_overlay.paste(map_rgba, (0, 0), map_rgba)

        map_draw.line([(MAP_PANEL_W, 0), (MAP_PANEL_W, H)],
                       fill=alpha_color(accent, 60), width=2)
        map_overlay = Image.alpha_composite(map_overlay, ctx.extra["divider_overlay"])
        img_rgba = Image.alpha_composite(img_rgba, map_overlay)

        # ── RIGHT PANEL: Narration ──
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        seg_data = ctx.wrapped[seg_idx]

        # Text backdrop
        od.rounded_rectangle(
            [(TEXT_PANEL_LEFT - 15, TEXT_TOP_MARGIN - 20),
             (TEXT_PANEL_RIGHT + 15, TEXT_TOP_MARGIN + MAX_VISIBLE_LINES * BODY_LINE_HEIGHT + 30)],
            radius=6, fill=(0, 0, 0, 80)
        )
        od.rectangle(
            [(TEXT_PANEL_LEFT - 15, TEXT_TOP_MARGIN - 10),
             (TEXT_PANEL_LEFT - 12, TEXT_TOP_MARGIN + MAX_VISIBLE_LINES * BODY_LINE_HEIGHT + 20)],
            fill=alpha_color(accent, 160)
        )

        # Word reveal
        text_a = int(255 * cross_fade)
        draw_word_reveal(
            od, seg_data, seg_progress,
            TEXT_PANEL_LEFT, TEXT_TOP_MARGIN, TEXT_PANEL_W,
            MAX_VISIBLE_LINES, BODY_LINE_HEIGHT, BODY_FONT_SIZE,
            ctx.fonts["body"], ctx.fonts["body"],
            text_color=(240, 240, 240, text_a),
            dummy_draw=ctx.dummy_draw,
        )

        # Cursor blink
        draw_cursor_blink(
            od, seg_data, seg_progress,
            TEXT_PANEL_LEFT, TEXT_TOP_MARGIN, TEXT_PANEL_W,
            MAX_VISIBLE_LINES, BODY_LINE_HEIGHT, BODY_FONT_SIZE,
            accent, frame_idx, ctx.fonts["body"], ctx.dummy_draw,
        )

        # Segment progress bar
        bar_y = H - 50
        od.rectangle([(TEXT_PANEL_LEFT, bar_y), (TEXT_PANEL_RIGHT, bar_y + 3)],
                      fill=(60, 60, 60, 100))
        fill_w = int(TEXT_PANEL_W * seg_progress)
        od.rectangle([(TEXT_PANEL_LEFT, bar_y), (TEXT_PANEL_LEFT + fill_w, bar_y + 3)],
                      fill=alpha_color(accent, 180))

        # Lower-third banners
        facts = ctx.scene.get("facts", [])
        fact_text, slide_prog, fact_visible = get_lower_third_state(frame_idx, facts)
        if fact_visible:
            banner_y = TEXT_TOP_MARGIN + MAX_VISIBLE_LINES * BODY_LINE_HEIGHT + 50
            draw_lower_third_banner(od, fact_text, slide_prog, accent, ctx.fonts,
                                    TEXT_PANEL_LEFT - 15, banner_y)

        # Source watermark
        sources = ctx.scene.get("sources", [])
        draw_source_watermark(od, sources, accent, ctx.fonts, W, H - 60)

        # Scene number (top-right)
        num_text = f"{ctx.scene_num} / {ctx.total_scenes}"
        od.text((W - 40, 20), num_text,
                fill=(130, 130, 130, 200), font=ctx.fonts["tiny"], anchor="rt")

        # Era + title (top of text panel)
        era = ctx.scene.get("era", "")
        if era:
            od.text((TEXT_PANEL_LEFT, 20), era,
                    fill=alpha_color(accent, 220), font=ctx.fonts["small"])
        title = ctx.scene.get("title", "")
        if title:
            od.text((TEXT_PANEL_LEFT, 45), title,
                    fill=alpha_color((220, 220, 220), 230), font=ctx.fonts["subtitle"])

        return Image.alpha_composite(img_rgba, overlay)
