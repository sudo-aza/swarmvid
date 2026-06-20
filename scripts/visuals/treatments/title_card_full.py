"""Title card full-screen treatment.

Full bleed title with large typography, animated accent lines,
corner brackets, and slow zoom/ken-burns effect on a gradient background.
Used for scene intros and major era transitions."""

from __future__ import annotations

import math
from PIL import Image, ImageDraw

from visuals.colors import alpha_color
from visuals.compositing import make_bg_composited
from visuals.fonts import W, H, TEXT_PANEL_LEFT, TEXT_TOP_MARGIN, MAX_VISIBLE_LINES, BODY_LINE_HEIGHT, BODY_FONT_SIZE
from visuals.particles import precompute_particles, draw_particles
from visuals.typography import (
    prewrap_text, draw_word_reveal, draw_cursor_blink,
    draw_lower_third_banner, draw_source_watermark,
    get_lower_third_state,
)
from visuals.treatments.base import TreatmentBase, RenderContext, draw_global_overlays

class TitleCardFullTreatment(TreatmentBase):
    """Full-screen cinematic title card with large typography and animated elements.
    After the title card phase, transitions to a centered narration layout."""

    name = "title_card"
    description = "Full-screen cinematic title card, then centered narration"

    def prepare(self, ctx: RenderContext) -> None:
        parsed = []
        for c in ctx.scene.get("gradient", ["#1a1a2e", "#16213e", "#0f3460"]):
            c = c.lstrip("#")
            parsed.append(tuple(int(c[i:i+2], 16) for i in (0, 2, 4)))

        ctx.bg_composited = make_bg_composited(W, H, parsed, vignette_strength=0.6)
        ctx.bg_rgba = ctx.bg_composited.convert("RGBA")
        ctx.particles = precompute_particles(
            15, W, H, seed=ctx.scene.get("scene_num", 0) * 137,
            style="dust"
        )
        ctx.wrapped = prewrap_text(
            ctx.scene.get("segments", []), ctx.fonts["body"],
            W - 120  # wider text area, centered
        )

    def render_frame(self, ctx: RenderContext, frame_idx: int,
                     total_frames: int, seg_idx: int,
                     seg_progress: float, cross_fade: float) -> Image.Image:
        accent = ctx.accent_rgb
        segments = ctx.scene.get("segments", [])

        img = ctx.bg_composited.copy()

        # Subtle particles
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        draw_particles(od, ctx.particles, frame_idx, H)
        img_rgba = Image.alpha_composite(ctx.bg_rgba, overlay)

        first_seg_dur = segments[0].get("duration_s", 5.0)
        title_time = 5.0 / first_seg_dur  # longer title phase
        in_title = (seg_idx == 0 and seg_progress < title_time)

        if in_title:
            img_rgba = self._draw_full_title(ctx, img_rgba, frame_idx, seg_progress, title_time)
        else:
            img_rgba = self._draw_centered_narration(ctx, img_rgba, frame_idx, seg_idx, seg_progress, cross_fade)

        global_ov = draw_global_overlays(ctx, frame_idx, total_frames)
        img_rgba = Image.alpha_composite(img_rgba, global_ov)
        return img_rgba.convert("RGB")

    def _draw_full_title(self, ctx, img_rgba, frame_idx, seg_progress, title_time):
        accent = ctx.accent_rgb
        tp = min(1.0, seg_progress / title_time)

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        # Ken Burns: slow zoom on background
        # (simulated by darkening edges progressively)
        dark_a = int(180 * min(1.0, tp * 3))
        od.rectangle([(0, 0), (W, H)], fill=(0, 0, 0, dark_a))

        cx, cy = W // 2, H // 2

        # Animated horizontal lines (expand from center)
        if tp > 0.05:
            prog = min(1.0, (tp - 0.05) * 2.5)
            line_half = int(400 * prog)
            od.line([(cx - line_half, cy - 80), (cx + line_half, cy - 80)],
                    fill=alpha_color(accent, int(200 * prog)), width=2)

        # Title (extra large)
        title = ctx.scene.get("title", "")
        if tp > 0.1:
            text_a = min(255, int(255 * min(1.0, (tp - 0.1) * 4)))
            title_font = ctx.fonts["title"]
            bbox = od.textbbox((0, 0), title, font=title_font)
            tw = bbox[2] - bbox[0]
            od.text((cx - tw // 2, cy - 60), title,
                    fill=alpha_color((255, 255, 255), text_a), font=title_font)

        # Bottom accent line
        if tp > 0.2:
            prog2 = min(1.0, (tp - 0.2) * 2.5)
            line_half2 = int(250 * prog2)
            od.line([(cx - line_half2, cy + 10), (cx + line_half2, cy + 10)],
                    fill=alpha_color(accent, int(180 * prog2)), width=2)

        # Subtitle
        subtitle = ctx.scene.get("subtitle", "")
        if subtitle and tp > 0.3:
            sub_a = min(255, int(255 * min(1.0, (tp - 0.3) * 3)))
            bbox = od.textbbox((0, 0), subtitle, font=ctx.fonts["subtitle"])
            sw = bbox[2] - bbox[0]
            od.text((cx - sw // 2, cy + 25), subtitle,
                    fill=alpha_color((200, 200, 200), sub_a), font=ctx.fonts["subtitle"])

        # Era label (top-left)
        era = ctx.scene.get("era", "")
        if era and tp > 0.15:
            ea = min(255, int(255 * min(1.0, (tp - 0.15) * 3)))
            od.text((80, 60), era,
                    fill=alpha_color((150, 150, 150), ea), font=ctx.fonts["era"])

        # Corner brackets (animated)
        if tp > 0.1:
            ba = min(220, int(220 * min(1.0, (tp - 0.1) * 3)))
            blen = int(80 * min(1.0, (tp - 0.1) * 2))
            bc = alpha_color(accent, ba)
            m = 50
            od.line([(m, m), (m + blen, m)], fill=bc, width=2)
            od.line([(m, m), (m, m + blen)], fill=bc, width=2)
            od.line([(W - m, H - m), (W - m - blen, H - m)], fill=bc, width=2)
            od.line([(W - m, H - m), (W - m, H - m - blen)], fill=bc, width=2)

        # Scene counter
        if tp > 0.3:
            na = min(180, int(180 * min(1.0, (tp - 0.3) * 3)))
            od.text((W - 80, H - 60), f"{ctx.scene_num} / {ctx.total_scenes}",
                    fill=alpha_color((120, 120, 120), na), font=ctx.fonts["tiny"],
                    anchor="rb")

        return Image.alpha_composite(img_rgba, overlay)

    def _draw_centered_narration(self, ctx, img_rgba, frame_idx, seg_idx, seg_progress, cross_fade):
        accent = ctx.accent_rgb

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        # Centered text with wider margins
        text_x = 80
        text_w = W - 160
        max_lines = 9
        text_y = 100

        # Era + title at top
        era = ctx.scene.get("era", "")
        if era:
            od.text((text_x, 30), era,
                    fill=alpha_color(accent, 200), font=ctx.fonts["small"])
        title = ctx.scene.get("title", "")
        if title:
            od.text((text_x, 55), title,
                    fill=alpha_color((220, 220, 220), 220), font=ctx.fonts["subtitle"])

        # Subtle backdrop
        od.rounded_rectangle(
            [(text_x - 15, text_y - 15),
             (W - text_x + 15, text_y + max_lines * BODY_LINE_HEIGHT + 20)],
            radius=8, fill=(0, 0, 0, 100)
        )

        # Accent left border
        od.rectangle(
            [(text_x - 15, text_y - 5),
             (text_x - 12, text_y + max_lines * BODY_LINE_HEIGHT + 10)],
            fill=alpha_color(accent, 140)
        )

        # Word reveal
        if seg_idx < len(ctx.wrapped):
            seg_data = ctx.wrapped[seg_idx]
            text_a = int(255 * cross_fade)
            draw_word_reveal(
                od, seg_data, seg_progress,
                text_x, text_y, text_w,
                max_lines, BODY_LINE_HEIGHT, BODY_FONT_SIZE,
                ctx.fonts["body"], ctx.fonts["body"],
                text_color=(240, 240, 240, text_a),
                dummy_draw=ctx.dummy_draw,
            )

        # Lower-thirds
        facts = ctx.scene.get("facts", [])
        ft, sp, fv = get_lower_third_state(frame_idx, facts)
        if fv:
            draw_lower_third_banner(od, ft, sp, accent, ctx.fonts,
                                    text_x - 15, text_y + max_lines * BODY_LINE_HEIGHT + 40,
                                    max_width=700)

        # Source watermark
        sources = ctx.scene.get("sources", [])
        draw_source_watermark(od, sources, accent, ctx.fonts, W, H - 60)

        # Scene counter
        od.text((W - 40, 20), f"{ctx.scene_num} / {ctx.total_scenes}",
                fill=(130, 130, 130, 200), font=ctx.fonts["tiny"], anchor="rt")

        return Image.alpha_composite(img_rgba, overlay)
