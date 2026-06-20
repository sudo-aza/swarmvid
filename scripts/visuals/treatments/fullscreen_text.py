"""Fullscreen text treatment — large centered typography, no map.

Clean, typographic-focused layout. Text takes center stage with
generous whitespace, large readable font, and minimal visual noise.
Good for philosophical commentary, quotes, concluding reflections."""

from __future__ import annotations

from PIL import Image, ImageDraw

from visuals.colors import alpha_color
from visuals.compositing import make_bg_composited
from visuals.fonts import (
    W, H, BODY_LINE_HEIGHT, BODY_FONT_SIZE,
)
from visuals.particles import precompute_particles, draw_particles
from visuals.typography import (
    prewrap_text, draw_word_reveal, draw_cursor_blink,
    draw_lower_third_banner, draw_source_watermark,
    get_lower_third_state,
)
from visuals.treatments.base import TreatmentBase, RenderContext, draw_global_overlays

class FullscreenTextTreatment(TreatmentBase):
    """Large centered text, no map panel. Typographic focus."""

    name = "fullscreen_text"
    description = "Full-screen centered text, no map, typographic focus"

    def prepare(self, ctx: RenderContext) -> None:
        parsed = []
        for c in ctx.scene.get("gradient", ["#121212", "#1a1a1a", "#0d0d0d"]):
            c = c.lstrip("#")
            parsed.append(tuple(int(c[i:i+2], 16) for i in (0, 2, 4)))

        ctx.bg_composited = make_bg_composited(W, H, parsed, vignette_strength=0.6, dark_factor=0.7)
        ctx.bg_rgba = ctx.bg_composited.convert("RGBA")
        ctx.particles = precompute_particles(
            8, W, H, seed=ctx.scene.get("scene_num", 0) * 137,
            style="dust"
        )
        ctx.wrapped = prewrap_text(
            ctx.scene.get("segments", []), ctx.fonts["bold"],  # larger font
            800  # wide centered area
        )

    def render_frame(self, ctx: RenderContext, frame_idx: int,
                     total_frames: int, seg_idx: int,
                     seg_progress: float, cross_fade: float) -> Image.Image:
        accent = ctx.accent_rgb

        img = ctx.bg_composited.copy()

        # Subtle particles
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        draw_particles(od, ctx.particles, frame_idx, H)
        img_rgba = Image.alpha_composite(ctx.bg_rgba, overlay)

        # ── CENTERED TEXT LAYOUT ──
        text_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(text_overlay)

        text_x = 120
        text_w = W - 240
        text_y = 140
        max_lines = 10
        line_h = 36  # slightly more spacious

        # Top: era + title
        era = ctx.scene.get("era", "")
        if era:
            od.text((text_x, 40), era,
                    fill=alpha_color(accent, 180), font=ctx.fonts["small"])
        title = ctx.scene.get("title", "")
        if title:
            od.text((text_x, 65), title,
                    fill=alpha_color((210, 210, 210), 200), font=ctx.fonts["subtitle"])

        # Thin horizontal rule below title
        od.line([(text_x, 100), (text_x + 200, 100)],
                fill=alpha_color(accent, 100), width=1)

        # Word reveal with larger font
        if seg_idx < len(ctx.wrapped):
            seg_data = ctx.wrapped[seg_idx]
            text_a = int(255 * cross_fade)
            draw_word_reveal(
                od, seg_data, seg_progress,
                text_x, text_y, text_w,
                max_lines, line_h, BODY_FONT_SIZE + 2,
                ctx.fonts["bold"], ctx.fonts["bold"],
                text_color=(245, 245, 245, text_a),
                dummy_draw=ctx.dummy_draw,
            )

        # Lower-thirds (positioned below text block)
        facts = ctx.scene.get("facts", [])
        ft, sp, fv = get_lower_third_state(frame_idx, facts)
        if fv:
            draw_lower_third_banner(od, ft, sp, accent, ctx.fonts,
                                    text_x, text_y + max_lines * line_h + 30,
                                    max_width=750)

        # Source watermark
        sources = ctx.scene.get("sources", [])
        draw_source_watermark(od, sources, accent, ctx.fonts, W, H - 60)

        # Scene counter
        od.text((W - 40, 20), f"{ctx.scene_num} / {ctx.total_scenes}",
                fill=(100, 100, 100, 180), font=ctx.fonts["tiny"], anchor="rt")

        img_rgba = Image.alpha_composite(img_rgba, text_overlay)

        # Global overlays
        global_ov = draw_global_overlays(ctx, frame_idx, total_frames)
        img_rgba = Image.alpha_composite(img_rgba, global_ov)

        return img_rgba.convert("RGB")
