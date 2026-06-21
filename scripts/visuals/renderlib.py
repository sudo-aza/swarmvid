"""renderlib — Central rendering library for swarmvid.

Provides a unified API for per-scene visual scripts. Each scene script
imports this module and uses it to compose frames. No layout decisions
are made here — only rendering primitives.

Usage in scene scripts:
    from visuals import renderlib as rl
    rl = rl.RenderLib(scene_data={...})
    state = rl.prepare()
    for frame_idx in range(total_frames):
        frame = rl.render(frame_idx, total_frames, state)
        # pipe frame to ffmpeg

Architecture:
    RenderLib maintains an internal RGBA compositing stack.
    Each method draws onto the current overlay, which gets composited
    onto the background each frame. Scene scripts call methods to build
    up a frame, then call .frame() to get the final RGB output.

Design principle:
    - Primitives only. No layout decisions.
    - Every method is stateless w.r.t. frame content (only uses passed params).
    - Scene scripts own ALL layout, animation choreography, and spatial decisions.
"""

from __future__ import annotations

import math
import os
import random
import sys
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Ensure scripts/ is on path for relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from visuals.colors import hex_rgb, alpha_color
from visuals.compositing import make_bg_composited, make_solid_bg, make_gradient_bg
from visuals.fonts import get_fonts, W, H, FPS
from visuals.particles import precompute_particles, draw_particles
from visuals.timeline import draw_timeline_bar


# ═══════════════════════════════════════════════════════════════════════════════
# Easing Functions
# ═══════════════════════════════════════════════════════════════════════════════

def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3

def ease_in_cubic(t: float) -> float:
    return t * t * t

def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2

def ease_out_back(t: float) -> float:
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

def ease_out_quad(t: float) -> float:
    return 1 - (1 - t) * (1 - t)

def ease_in_quad(t: float) -> float:
    return t * t

EASING_FNS: dict[str, Callable] = {
    "linear": lambda t: t,
    "out_cubic": ease_out_cubic,
    "in_cubic": ease_in_cubic,
    "in_out_cubic": ease_in_out_cubic,
    "out_back": ease_out_back,
    "out_quad": ease_out_quad,
    "in_quad": ease_in_quad,
}


# ═══════════════════════════════════════════════════════════════════════════════
# RenderLib
# ═══════════════════════════════════════════════════════════════════════════════

class RenderLib:
    """Central rendering library. One instance per scene.

    Provides primitives for backgrounds, text, images, shapes, particles,
    animation helpers, and compositing. Scene scripts call these methods
    to compose each frame.
    """

    def __init__(self, w: int = W, h: int = H, fps: int = FPS,
                 scene_data: dict | None = None,
                 accent: tuple = (233, 69, 96),
                 media_base: str = ""):
        self.w = w
        self.h = h
        self.fps = fps
        self.scene = scene_data or {}
        self.accent = accent
        self.media_base = media_base
        self.fonts = get_fonts()

        # Per-frame compositing state (set fresh each frame in .render())
        self._bg: Image.Image | None = None
        self._bg_rgba: Image.Image | None = None
        self._overlay: Image.Image | None = None
        self._od: ImageDraw.ImageDraw | None = None
        self._frame_idx: int = 0
        self._total_frames: int = 0

        # Pre-computed assets (populated by prepare or scene scripts)
        self.particles: list[dict] = []

    # ── Time helpers ─────────────────────────────────────────────────────────

    def time(self, frame_idx: int, total_frames: int) -> float:
        """Convert frame index to time in seconds."""
        return frame_idx / max(self.fps, 1)

    def segment_at_time(self, t: float) -> tuple[int, float]:
        """Given time in seconds, return (segment_index, progress_within_segment).
        segment_index: which narration segment we're in (0-based).
        progress: 0.0-1.0 within that segment."""
        segments = self.scene.get("segments", [])
        elapsed = 0.0
        for i, seg in enumerate(segments):
            dur = seg.get("duration_s", 12.0)
            if elapsed + dur > t:
                return i, (t - elapsed) / max(dur, 0.01)
            elapsed += dur
        # Past all segments — return last
        return max(0, len(segments) - 1), 1.0

    def seg_time(self, seg_idx: int, offset: float = 0.0) -> float:
        """Calculate absolute time in seconds for a point within a segment."""
        t = 0.0
        for i in range(seg_idx):
            t += self.scene["segments"][i].get("duration_s", 12.0)
        return t + offset

    # ── Frame lifecycle ──────────────────────────────────────────────────────

    def begin_frame(self, frame_idx: int, total_frames: int) -> None:
        """Start compositing a new frame. Must be called before drawing anything."""
        self._frame_idx = frame_idx
        self._total_frames = total_frames
        # Reset overlay
        self._overlay = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self._od = ImageDraw.Draw(self._overlay)

    def _ensure_overlay(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Auto-init overlay if not started."""
        if self._overlay is None:
            self.begin_frame(self._frame_idx, self._total_frames)
        return self._overlay, self._od

    # ── Backgrounds ─────────────────────────────────────────────────────────

    def gradient(self, colors: list[tuple], direction: str = "radial",
                 vignette: float = 0.5, dark_factor: float = 0.85) -> None:
        """Set the frame background to a gradient.
        colors: list of (R,G,B) tuples for gradient stops.
        direction: 'radial', 'vertical', 'horizontal'.
        vignette: 0.0-1.0 vignette darkening strength.
        dark_factor: threshold for vignette blend."""
        parsed = []
        for c in colors:
            if isinstance(c, str):
                parsed.append(hex_rgb(c))
            else:
                parsed.append(tuple(c[:3]))
        if direction == "radial":
            self._bg = make_bg_composited(self.w, self.h, parsed,
                                          vignette_strength=vignette,
                                          dark_factor=dark_factor)
        else:
            self._bg = make_gradient_bg(self.w, self.h, parsed, direction=direction)
        self._bg_rgba = self._bg.convert("RGBA")

    def solid(self, color: tuple) -> None:
        """Set the frame background to a solid color."""
        self._bg = make_solid_bg(self.w, self.h, color)
        self._bg_rgba = self._bg.convert("RGBA")

    def image_bg(self, path: str, fit: str = "cover", darken: float = 0.4) -> None:
        """Set the frame background to an image (ken burns base).
        fit: 'cover' (fill, crop) or 'contain' (fit, letterbox).
        darken: 0.0-1.0 overlay darkness (so text is readable)."""
        if not os.path.isfile(path):
            self.solid((10, 10, 15))
            return
        img = Image.open(path).convert("RGB")
        # Scale to cover
        iw, ih = img.size
        scale = max(self.w / max(iw, 1), self.h / max(ih, 1))
        if fit == "contain":
            scale = min(self.w / max(iw, 1), self.h / max(ih, 1))
        new_w, new_h = int(iw * scale), int(ih * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        # Center crop
        x_off = (new_w - self.w) // 2
        y_off = (new_h - self.h) // 2
        img = img.crop((x_off, y_off, x_off + self.w, y_off + self.h))
        # Darken overlay
        if darken > 0:
            dark = Image.new("RGBA", (self.w, self.h), (0, 0, 0, int(255 * darken)))
            img_rgba = img.convert("RGBA")
            img_rgba = Image.alpha_composite(img_rgba, dark)
            self._bg = img_rgba.convert("RGB")
        else:
            self._bg = img
        self._bg_rgba = self._bg.convert("RGBA")

    def vignette(self, strength: float = 0.6) -> None:
        """Add vignette darkening to the current overlay. Call after begin_frame()."""
        ov, od = self._ensure_overlay()
        cx, cy = self.w / 2.0, self.h / 2.0
        y_coords, x_coords = np.mgrid[0:self.h, 0:self.w]
        dx = (x_coords - cx) / cx
        dy = (y_coords - cy) / cy
        d = np.sqrt(dx * dx + dy * dy) / 1.414
        d = np.clip(d, 0, 1.0)
        alpha_arr = (d * 255 * strength).astype(np.uint8)
        vignette_img = Image.new("L", (self.w, self.h))
        vignette_img.putdata(alpha_arr.flatten().tolist())
        self._overlay = Image.alpha_composite(ov, vignette_img.convert("RGBA"))
        self._od = ImageDraw.Draw(self._overlay)

    def noise(self, intensity: float = 0.03) -> None:
        """Add film grain noise to the current overlay."""
        ov, od = self._ensure_overlay()
        arr = np.random.normal(0, intensity * 255, (self.h, self.w))
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        noise_img = Image.fromarray(arr, "L")
        noise_rgba = noise_img.convert("RGBA")
        pixels = noise_rgba.load()
        for y in range(self.h):
            for x in range(self.w):
                r, g, b, _ = pixels[x, y]
                pixels[x, y] = (r, g, b, 30)  # very subtle
        self._overlay = Image.alpha_composite(ov, noise_rgba)
        self._od = ImageDraw.Draw(self._overlay)

    # ── Text ─────────────────────────────────────────────────────────────────

    def text(self, text: str, x: int, y: int,
             font: ImageFont.FreeTypeFont | str = "body",
             color: tuple = (240, 240, 240, 255),
             anchor: str = "lt") -> tuple[int, int, int, int]:
        """Draw text at position. Returns bounding box (x1, y1, x2, y2).
        font: ImageFont object or font name from fonts dict ('body', 'title', etc.)
        color: (R, G, B, A) RGBA tuple.
        anchor: PIL anchor (lt=top-left, mm=middle-center, rt=top-right, etc.)"""
        ov, od = self._ensure_overlay()
        if isinstance(font, str):
            font = self.fonts.get(font, self.fonts["body"])
        od.text((x, y), text, fill=color, font=font, anchor=anchor)
        bbox = od.textbbox((x, y), text, font=font, anchor=anchor)
        return bbox

    def text_box(self, text: str, x: int, y: int, w: int,
                font: ImageFont.FreeTypeFont | str = "body",
                color: tuple = (240, 240, 240, 255),
                max_lines: int = 8, line_height: int = 28,
                align: str = "left") -> tuple[int, int]:
        """Draw word-wrapped text in a box. Returns (width_used, height_used).
        Wraps at 'w' pixels, draws up to max_lines."""
        ov, od = self._ensure_overlay()
        if isinstance(font, str):
            font = self.fonts.get(font, self.fonts["body"])
        dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            bbox = dummy.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > w:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

        drawn = lines[:max_lines]
        for i, line in enumerate(drawn):
            ly = y + i * line_height
            if align == "center":
                bbox = dummy.textbbox((0, 0), line, font=font)
                lw = bbox[2] - bbox[0]
                lx = x + (w - lw) // 2
            elif align == "right":
                bbox = dummy.textbbox((0, 0), line, font=font)
                lw = bbox[2] - bbox[0]
                lx = x + w - lw
            else:
                lx = x
            od.text((lx, ly), line, fill=color, font=font)

        max_w = max(dummy.textbbox((0, 0), l, font=font)[2] for l in drawn) if drawn else 0
        return max_w, len(drawn) * line_height

    def reveal_text(self, text: str, progress: float, x: int, y: int, w: int,
                   font: ImageFont.FreeTypeFont | str = "body",
                   color: tuple = (240, 240, 240, 255),
                   max_lines: int = 8, line_height: int = 28,
                   by_char: bool = False) -> tuple[int, int]:
        """Progressive text reveal — shows text up to progress (0.0-1.0).
        by_char: if True, reveal character-by-character; otherwise word-by-word.
        Returns (width_used, height_used) of drawn area."""
        if by_char:
            chars_to_show = int(progress * len(text))
            visible = text[:chars_to_show]
            return self.text_box(visible, x, y, w, font, color, max_lines, line_height)
        else:
            words = text.split()
            words_to_show = max(1, int(progress * len(words) * 1.5))
            visible = " ".join(words[:min(words_to_show, len(words))])
            return self.text_box(visible, x, y, w, font, color, max_lines, line_height)

    def callout(self, text: str, subtext: str = "", x: int | None = None,
                y: int | None = None, position: str = "center",
                style: str = "highlight", alpha_mult: float = 1.0) -> None:
        """Draw a styled callout (date, name, fact highlight).
        position: 'center', 'left', 'right', 'top', 'bottom', 'top-left', 'top-right',
                  'bottom-left', 'bottom-right'. Auto-positions if x/y not given.
        style: 'highlight' (gold), 'warning' (red), 'info' (blue), 'default' (accent)."""
        ov, od = self._ensure_overlay()
        font = self.fonts.get("subtitle", self.fonts["body"])
        sub_font = self.fonts.get("body", self.fonts["small"])

        # Style colors
        styles = {
            "default": {"bg": (*self.accent[:3], 0), "border": (*self.accent, 220), "text": (240, 240, 240, 240), "sub": (180, 180, 185, 200)},
            "highlight": {"bg": (30, 15, 0, 200), "border": (255, 180, 50, 240), "text": (255, 240, 200, 255), "sub": (220, 200, 160, 220)},
            "warning": {"bg": (40, 0, 0, 200), "border": (255, 60, 60, 240), "text": (255, 220, 220, 255), "sub": (220, 180, 180, 220)},
            "info": {"bg": (0, 10, 30, 200), "border": (80, 160, 255, 240), "text": (220, 230, 255, 255), "sub": (180, 200, 240, 220)},
        }
        s = styles.get(style, styles["default"])

        # Measure
        bbox = od.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        box_w = tw + 40
        box_h = th + 20
        if subtext:
            sbbox = od.textbbox((0, 0), subtext, font=sub_font)
            box_w = max(box_w, sbbox[2] - sbbox[0] + 40)
            box_h += sbbox[3] - sbbox[1] + 6

        if x is not None and y is not None:
            pass  # explicit position
        else:
            x, y = self._position(position, box_w, box_h, margin=50)

        # Apply alpha
        bg_c = self._scale_alpha(s["bg"], alpha_mult)
        border_c = self._scale_alpha(s["border"], alpha_mult)
        text_c = self._scale_alpha(s["text"], alpha_mult)
        sub_c = self._scale_alpha(s["sub"], alpha_mult)

        od.rounded_rectangle([(x, y), (x + box_w, y + box_h)],
                             radius=6, fill=bg_c)
        od.rectangle([(x, y), (x + 4, y + box_h)], fill=border_c)
        od.text((x + 20, y + 10), text, fill=text_c, font=font)
        if subtext:
            od.text((x + 20, y + th + 16), subtext, fill=sub_c, font=sub_font)

    def card(self, title: str, body: str = "",
             x: int | None = None, y: int | None = None,
             position: str = "right",
             width: int | None = None,
             style: str = "default", alpha_mult: float = 1.0) -> None:
        """Draw an info card with title + body text."""
        ov, od = self._ensure_overlay()
        title_font = self.fonts.get("subtitle", self.fonts["title"])
        body_font = self.fonts.get("body", self.fonts["small"])

        styles = {
            "default": {"bg": (0, 0, 0, 190), "border": (*self.accent, 220),
                        "title": (240, 240, 240, 240), "body": (180, 180, 185, 200)},
            "highlight": {"bg": (30, 15, 0, 200), "border": (255, 180, 50, 240),
                          "title": (255, 240, 200, 255), "body": (220, 200, 160, 220)},
            "warning": {"bg": (40, 0, 0, 200), "border": (255, 60, 60, 240),
                        "title": (255, 220, 220, 255), "body": (220, 180, 180, 220)},
        }
        s = styles.get(style, styles["default"])

        # Measure title
        tbbox = od.textbbox((0, 0), title, font=title_font)
        tw = tbbox[2] - tbbox[0]
        card_w = width or max(tw + 40, 280)

        # Wrap body
        dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
        lines = []
        if body:
            words = body.split()
            line = ""
            for word in words:
                test = line + (" " if line else "") + word
                bb = dummy.textbbox((0, 0), test, font=body_font)
                if bb[2] - bb[0] > card_w - 30:
                    if line:
                        lines.append(line)
                    line = word
                else:
                    line = test
            if line:
                lines.append(line)

        card_h = 50 + len(lines) * 22
        if x is not None and y is not None:
            pass
        else:
            x, y = self._position(position, card_w, card_h, margin=50)

        bg_c = self._scale_alpha(s["bg"], alpha_mult)
        border_c = self._scale_alpha(s["border"], alpha_mult)
        title_c = self._scale_alpha(s["title"], alpha_mult)
        body_c = self._scale_alpha(s["body"], alpha_mult)

        od.rounded_rectangle([(x, y), (x + card_w, y + card_h)],
                             radius=8, fill=bg_c)
        od.rectangle([(x, y), (x + card_w, y + 3)], fill=border_c)
        od.text((x + 15, y + 12), title, fill=title_c, font=title_font)
        for i, line in enumerate(lines[:6]):
            od.text((x + 15, y + 42 + i * 22), line, fill=body_c, font=body_font)

    # ── Images ───────────────────────────────────────────────────────────────

    def image(self, path: str, x: int, y: int,
              w: int | None = None, h: int | None = None,
              fit: str = "cover", alpha_mult: float = 1.0,
              border: bool = False) -> None:
        """Place an image at position. Auto-scales to fit within w x h.
        fit: 'cover' (fill, crop) or 'contain' (fit inside, no crop).
        alpha_mult: 0.0-1.0 overall transparency.
        border: draw accent-colored border."""
        ov, od = self._ensure_overlay()
        full_path = path if os.path.isabs(path) else os.path.join(self.media_base, path)
        if not os.path.isfile(full_path):
            return
        img = Image.open(full_path).convert("RGBA")
        iw, ih = img.size
        target_w = w or iw
        target_h = h or ih
        if w or h:
            scale = min(target_w / max(iw, 1), target_h / max(ih, 1))
            if fit == "cover":
                scale = max(target_w / max(iw, 1), target_h / max(ih, 1))
            new_w, new_h = int(iw * scale), int(ih * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            # Center crop for cover
            if fit == "cover":
                x_off = (new_w - target_w) // 2
                y_off = (new_h - target_h) // 2
                img = img.crop((x_off, y_off, x_off + target_w, y_off + target_h))
        # Apply alpha
        if alpha_mult < 1.0:
            alpha_arr = img.split()[-1]
            alpha_arr = alpha_arr.point(lambda p: int(p * alpha_mult))
            img.putalpha(alpha_arr)
        ov.paste(img, (x, y), img)
        if border:
            iw2, ih2 = img.size
            border_c = alpha_color(self.accent, int(200 * alpha_mult))
            od.rectangle([(x, y), (x + iw2, y + 2)], fill=border_c)
            od.rectangle([(x, y), (x + 2, y + ih2)], fill=border_c)

    def image_ken_burns(self, path: str, x: int, y: int, w: int, h: int,
                        progress: float = 0.0,
                        zoom_range: tuple = (1.0, 1.15),
                        pan_direction: tuple = (0.3, 0.2),
                        alpha_mult: float = 1.0) -> None:
        """Ken Burns effect — slow zoom + pan on a still image.
        progress: 0.0-1.0 over the scene duration.
        zoom_range: (start_scale, end_scale).
        pan_direction: (dx, dy) normalized direction of pan."""
        ov, od = self._ensure_overlay()
        full_path = path if os.path.isabs(path) else os.path.join(self.media_base, path)
        if not os.path.isfile(full_path):
            return
        img = Image.open(full_path).convert("RGBA")

        # Scale to fill the target area at maximum zoom
        max_zoom = max(zoom_range)
        iw, ih = img.size
        scale = max((w * max_zoom) / max(iw, 1), (h * max_zoom) / max(ih, 1))
        scaled_w = int(iw * scale)
        scaled_h = int(ih * scale)
        img = img.resize((scaled_w, scaled_h), Image.LANCZOS)

        # Current zoom and pan offset
        t = max(0.0, min(1.0, progress))
        current_zoom = zoom_range[0] + (zoom_range[1] - zoom_range[0]) * t
        crop_w = int(w / current_zoom)
        crop_h = int(h / current_zoom)
        # Pan offset
        max_pan_x = max(0, scaled_w - crop_w)
        max_pan_y = max(0, scaled_h - crop_h)
        px = int(max_pan_x * pan_direction[0] * t)
        py = int(max_pan_y * pan_direction[1] * t)
        px = min(px, max(0, scaled_w - crop_w))
        py = min(py, max(0, scaled_h - crop_h))

        cropped = img.crop((px, py, px + crop_w, py + crop_h))
        cropped = cropped.resize((w, h), Image.LANCZOS)

        if alpha_mult < 1.0:
            alpha_arr = cropped.split()[-1]
            alpha_arr = alpha_arr.point(lambda p: int(p * alpha_mult))
            cropped.putalpha(alpha_arr)

        ov.paste(cropped, (x, y), cropped)

    # ── Shapes & Decorations ────────────────────────────────────────────────

    def line(self, x1: int, y1: int, x2: int, y2: int,
             color: tuple = (233, 69, 96, 200), width: int = 1) -> None:
        """Draw a line."""
        ov, od = self._ensure_overlay()
        od.line([(x1, y1), (x2, y2)], fill=color, width=width)

    def rect(self, x: int, y: int, w: int, h: int,
             color: tuple = (233, 69, 96, 200), radius: int = 0,
             fill: tuple | None = None) -> None:
        """Draw a rectangle (outline by default, fill if provided).
        If fill is given, draws filled rect with color as border."""
        ov, od = self._ensure_overlay()
        if fill is not None:
            od.rounded_rectangle([(x, y), (x + w, y + h)],
                                 radius=radius, fill=fill)
            od.rounded_rectangle([(x, y), (x + w, y + h)],
                                 radius=radius, outline=color)
        else:
            if radius > 0:
                od.rounded_rectangle([(x, y), (x + w, y + h)],
                                     radius=radius, outline=color)
            else:
                od.rectangle([(x, y), (x + w, y + h)], outline=color)

    def rect_filled(self, x: int, y: int, w: int, h: int,
                    fill: tuple = (0, 0, 0, 180), radius: int = 0) -> None:
        """Draw a filled rectangle (no border)."""
        ov, od = self._ensure_overlay()
        if radius > 0:
            od.rounded_rectangle([(x, y), (x + w, y + h)], radius=radius, fill=fill)
        else:
            od.rectangle([(x, y), (x + w, y + h)], fill=fill)

    def bracket(self, x: int, y: int, size: int,
               color: tuple = (233, 69, 96, 200),
               corner: str = "tl", width: int = 2) -> None:
        """Draw a decorative corner bracket.
        corner: 'tl', 'tr', 'bl', 'br', or 'all'."""
        ov, od = self._ensure_overlay()
        corners = [corner] if corner != "all" else ["tl", "tr", "bl", "br"]
        for c in corners:
            if c == "tl":
                od.line([(x, y), (x + size, y)], fill=color, width=width)
                od.line([(x, y), (x, y + size)], fill=color, width=width)
            elif c == "tr":
                od.line([(x, y), (x - size, y)], fill=color, width=width)
                od.line([(x, y), (x, y + size)], fill=color, width=width)
            elif c == "bl":
                od.line([(x, y), (x + size, y)], fill=color, width=width)
                od.line([(x, y), (x, y - size)], fill=color, width=width)
            elif c == "br":
                od.line([(x, y), (x - size, y)], fill=color, width=width)
                od.line([(x, y), (x, y - size)], fill=color, width=width)

    def ellipse(self, cx: int, cy: int, rx: int, ry: int,
               color: tuple = (233, 69, 96, 200), fill: tuple | None = None) -> None:
        """Draw an ellipse centered at (cx, cy)."""
        ov, od = self._ensure_overlay()
        if fill is not None:
            od.ellipse([(cx - rx, cy - ry), (cx + rx, cy + ry)],
                       fill=fill, outline=color)
        else:
            od.ellipse([(cx - rx, cy - ry), (cx + rx, cy + ry)],
                       outline=color)

    def glow(self, cx: int, cy: int, radius: int,
            color: tuple = (233, 69, 96), alpha: int = 60) -> None:
        """Draw a soft radial glow."""
        ov, od = self._ensure_overlay()
        glow_img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        for r in range(radius, 0, -2):
            a = int(alpha * (r / radius))
            glow_draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                             fill=(*color[:3], a))
        # Blur for softness
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=radius // 4))
        self._overlay = Image.alpha_composite(ov, glow_img)
        self._od = ImageDraw.Draw(self._overlay)

    # ── Particles ────────────────────────────────────────────────────────────

    def init_particles(self, count: int = 20, seed: int = 0,
                       style: str = "warm_glow") -> None:
        """Pre-compute particles for the scene. Call once during prepare().
        style: 'warm_glow', 'embers', 'dust', 'rain', 'snow'."""
        self.particles = precompute_particles(count, self.w, self.h,
                                             seed=seed, style=style)

    def draw_particles(self) -> None:
        """Draw particles onto the current frame overlay."""
        if not self.particles:
            return
        ov, od = self._ensure_overlay()
        draw_particles(od, self.particles, self._frame_idx, self.h)

    # ── Global Overlays ─────────────────────────────────────────────────────

    def progress_bar(self, y: int | None = None, color: tuple | None = None,
                     height: int = 3) -> None:
        """Draw a thin progress bar at the bottom of the frame."""
        ov, od = self._ensure_overlay()
        if y is None:
            y = self.h - height
        if color is None:
            color = alpha_color(self.accent, 200)
        progress = self._frame_idx / max(self._total_frames - 1, 1)
        od.rectangle([(0, y), (self.w, y + height)], fill=(30, 30, 30, 150))
        od.rectangle([(0, y), (int(self.w * progress), y + height)], fill=color)

    def timeline_bar(self, scene_num: int = 1,
                     total_scenes: int = 28) -> None:
        """Draw the historical era timeline bar at the bottom."""
        ov, od = self._ensure_overlay()
        draw_timeline_bar(od, scene_num, total_scenes,
                         self.accent, self.fonts, self.w, self.h)

    def scene_counter(self, x: int | None = None, y: int | None = None,
                     scene_num: int = 1, total_scenes: int = 28,
                     color: tuple = (130, 130, 130, 200)) -> None:
        """Draw 'N / M' scene counter."""
        ov, od = self._ensure_overlay()
        if x is None:
            x = self.w - 40
        if y is None:
            y = 20
        label = f"{scene_num} / {total_scenes}"
        od.text((x, y), label, fill=color, font=self.fonts["tiny"], anchor="rt")

    # ── Animation Helpers ────────────────────────────────────────────────────

    def ease(self, t: float, fn: str = "out_cubic") -> float:
        """Apply easing function to t (0.0-1.0)."""
        return EASING_FNS.get(fn, ease_out_cubic)(max(0.0, min(1.0, t)))

    def alpha(self, base_alpha: float, progress: float,
              fade_in: float = 0.2, fade_out: float = 0.2) -> float:
        """Compute alpha with fade in/out based on progress.
        base_alpha: max alpha (0.0-1.0).
        progress: 0.0-1.0 within the element's visible range.
        fade_in/fade_out: fraction of progress spent fading in/out."""
        a = base_alpha
        if progress < fade_in:
            a *= progress / fade_in
        elif progress > 1.0 - fade_out:
            a *= (1.0 - progress) / fade_out
        return max(0.0, min(1.0, a))

    def slide(self, from_x: float, to_x: float, t: float,
              fn: str = "out_cubic") -> float:
        """Slide position interpolation. Returns interpolated x."""
        eased = EASING_FNS.get(fn, ease_out_cubic)(max(0.0, min(1.0, t)))
        return from_x + (to_x - from_x) * eased

    def pulse(self, base: float, amplitude: float, t: float,
              speed: float = 1.0) -> float:
        """Pulsing value (oscillates around base)."""
        return base + amplitude * math.sin(t * speed * math.tau)

    def lerp(self, a: float, b: float, t: float) -> float:
        """Linear interpolation."""
        t = max(0.0, min(1.0, t))
        return a + (b - a) * t

    def clamp(self, v: float, lo: float = 0.0, hi: float = 1.0) -> float:
        """Clamp value to range."""
        return max(lo, min(hi, v))

    # ── Compositing ────────────────────────────────────────────────────────

    def overlay_image(self, img: Image.Image, x: int = 0, y: int = 0,
                      mask: Image.Image | None = None) -> None:
        """Composite an image onto the current overlay."""
        ov, od = self._ensure_overlay()
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        ov.paste(img, (x, y), mask)

    def frame(self) -> Image.Image:
        """Return the final composited RGB frame.
        Composites: background → overlay (with all drawn content).
        Call this once per frame after all drawing is done."""
        if self._bg_rgba is None:
            self.solid((10, 10, 15))
        if self._overlay is None:
            return self._bg.copy()
        result = Image.alpha_composite(self._bg_rgba, self._overlay)
        return result.convert("RGB")

    # ── Internal Helpers ────────────────────────────────────────────────────

    def _position(self, position: str, content_w: int, content_h: int,
                 margin: int = 30) -> tuple[int, int]:
        """Calculate (x, y) for a named position."""
        if position == "left":
            return margin, (self.h - content_h) // 2
        elif position == "right":
            return self.w - content_w - margin, (self.h - content_h) // 2
        elif position == "center":
            return (self.w - content_w) // 2, (self.h - content_h) // 2
        elif position == "top":
            return (self.w - content_w) // 2, margin + 40
        elif position == "bottom":
            return (self.w - content_w) // 2, self.h - content_h - margin - 50
        elif position == "bottom-left":
            return margin, self.h - content_h - margin - 50
        elif position == "bottom-right":
            return self.w - content_w - margin, self.h - content_h - margin - 50
        elif position == "top-left":
            return margin, margin + 40
        elif position == "top-right":
            return self.w - content_w - margin, margin + 40
        return (self.w - content_w) // 2, (self.h - content_h) // 2

    def _scale_alpha(self, color: tuple, mult: float) -> tuple:
        """Scale alpha channel of an RGBA color."""
        if len(color) == 4:
            return (color[0], color[1], color[2], int(color[3] * max(0, min(1, mult))))
        return (*color, int(255 * max(0, min(1, mult))))

    # ── Prepare (optional convenience) ───────────────────────────────────────

    def prepare(self) -> dict:
        """Convenience prepare: load fonts, parse gradient, compute basic assets.
        Returns a state dict that scene scripts can extend.
        Scene scripts should call this and add their own pre-computed state."""
        scene = self.scene
        # Parse gradient from scene
        gradient_colors = scene.get("gradient", ["#1a1a2e", "#16213e", "#0f3460"])
        parsed = [hex_rgb(c) if isinstance(c, str) else tuple(c[:3])
                  for c in gradient_colors]

        return {
            "gradient_colors": parsed,
            "accent": self.accent,
            "fonts": self.fonts,
            "title": scene.get("title", ""),
            "subtitle": scene.get("subtitle", ""),
            "era": scene.get("era", ""),
            "segments": scene.get("segments", []),
            "scene_num": scene.get("scene_num", 1),
            "total_scenes": scene.get("total_scenes", 28),
        }
