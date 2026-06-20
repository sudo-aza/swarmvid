"""Stark minimal treatment — harsh contrast, red accents, dramatic.

For war, destruction, crisis scenes (WWII, Thirty Years' War).
Heavy contrast, desaturated palette, red accent only.
Text appears in short stark lines with hard cuts, no word reveal."""

from __future__ import annotations

import math
from PIL import Image, ImageDraw

from visuals.colors import alpha_color
from visuals.compositing import make_solid_bg
from visuals.fonts import (
    W, H, BODY_LINE_HEIGHT, BODY_FONT_SIZE,
)
from visuals.particles import precompute_particles, draw_particles
from visuals.typography import (
    prewrap_text, draw_source_watermark,
    get_lower_third_state, draw_lower_third_banner,
)
from visuals.treatments.base import TreatmentBase, RenderContext, draw_global_overlays

class StarkMinimalTreatment(TreatmentBase):
    """Harsh, dramatic. Red accent, near-black bg, hard-cut text reveal.
    For war/destruction/crisis scenes."""

    name = "stark"
    description = "Harsh contrast, red accent, dramatic. For war/crisis scenes"

    def prepare(self, ctx: RenderContext) -> None:
        ctx.bg_composited = make_solid_bg(W, H, (8, 8, 8))
        ctx.bg_rgba = ctx.bg_composited.convert("RGBA")
        ctx.particles = precompute_particles(
            5, W, H, seed=ctx.scene.get("scene_num", 0) * 137,
            style="embers"
        )
        # Pre-wrap with wider layout
        ctx.wrapped = prewrap_text(
            ctx.scene.get("segments", []), ctx.fonts["body"], W - 200
        )

    def render_frame(self, ctx: RenderContext, frame_idx: int,
                     total_frames: int, seg_idx: int,
                     seg_progress: float, cross_fade: float) -> Image.Image:
        # Override accent to red for stark treatment
        accent = (200, 30, 30)

        img = ctx.bg_composited.copy()

        # Sparse ember particles
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        draw_particles(od, ctx.particles, frame_idx, H)
        img_rgba = Image.alpha_composite(ctx.bg_rgba, overlay)

        # ── STARK TEXT LAYOUT ──
        text_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(text_overlay)

        text_x = 100
        text_w = W - 200
        text_y = 120

        # Era + title with red accent
        era = ctx.scene.get("era", "")
        if era:
            od.text((text_x, 40), era.upper(),
                    fill=alpha_color(accent, 220), font=ctx.fonts["small"])

        # Red line separator
        od.line([(text_x, 70), (text_x + 150, 70)],
                fill=alpha_color(accent, 255), width=2)

        # HARD CUT text reveal — show full lines at once, no word-by-word
        if seg_idx < len(ctx.wrapped):
            seg_data = ctx.wrapped[seg_idx]
            lines = seg_data["lines"]
            words = seg_data["words"]
            total_words = len(words)

            # How many lines to show (hard cut, not word-by-word)
            total_lines = len(lines)
            lines_to_show = min(total_lines, int(seg_progress * total_lines * 1.2) + 1)

            # Show full lines with hard cross-fade between segments
            text_a = int(255 * cross_fade)
            for i in range(min(lines_to_show, 8)):
                ly = text_y + i * 40
                line_text = lines[i] if i < total_lines else ""
                if line_text:
                    # White text, last visible line slightly dimmer
                    if i == lines_to_show - 1 and lines_to_show < total_lines:
                        od.text((text_x, ly), line_text,
                                fill=(220, 220, 220, text_a), font=ctx.fonts["body"])
                    else:
                        od.text((text_x, ly), line_text,
                                fill=(240, 240, 240, text_a), font=ctx.fonts["body"])

        # Lower-thirds with red accent
        facts = ctx.scene.get("facts", [])
        ft, sp, fv = get_lower_third_state(frame_idx, facts)
        if fv:
            draw_lower_third_banner(od, ft, sp, accent, ctx.fonts,
                                    text_x, text_y + 8 * 40 + 20, max_width=700)

        # Source watermark
        sources = ctx.scene.get("sources", [])
        draw_source_watermark(od, sources, accent, ctx.fonts, W, H - 60)

        # Scene counter — red
        od.text((W - 40, 20), f"{ctx.scene_num} / {ctx.total_scenes}",
                fill=alpha_color((180, 180, 180), 180), font=ctx.fonts["tiny"], anchor="rt")

        img_rgba = Image.alpha_composite(img_rgba, text_overlay)

        # Global overlays (use red accent for timeline)
        saved_accent = ctx.accent_rgb
        ctx.accent_rgb = accent
        global_ov = draw_global_overlays(ctx, frame_idx, total_frames)
        ctx.accent_rgb = saved_accent
        img_rgba = Image.alpha_composite(img_rgba, global_ov)

        return img_rgba.convert("RGB")
