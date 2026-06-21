"""Per-scene visual events engine.

Allows scene JSONs to declare visual events (images, callouts, diagrams,
popups, animated transitions) that trigger at specific narration timestamps.

Scene JSON format:
    "visual_events": [
        {
            "type": "image",           // event type: image, callout, diagram, card, split_text
            "trigger_time": 5.0,      // seconds into the scene when event activates
            "duration": 8.0,           // how long the event stays visible (0 = until end)
            "src": "path/to/image.jpg", // for image type: file path relative to output/media/
            "caption": "Leinefurt",     // optional caption text
            "position": "left",         // left, right, center, bottom-left, bottom-right, top
            "anim": "fade_in",         // animation: fade_in, slide_left, slide_right, zoom, pop
            "anim_duration": 0.5,       // seconds for entrance animation
        },
        {
            "type": "callout",
            "trigger_time": 12.0,
            "duration": 4.0,
            "text": "9 n. Chr.",
            "subtext": "Varusschlacht",
            "position": "center",
            "anim": "pop",
            "style": "highlight"        // highlight, warning, info
        },
        {
            "type": "card",
            "trigger_time": 20.0,
            "duration": 6.0,
            "title": "Karl der Große",
            "body": "772–804 Sachsenkriege",
            "position": "right",
            "anim": "slide_left",
        }
    ]

Rendering pipeline:
    1. Scene JSON is loaded with visual_events array
    2. EventTimeline.build(events) creates a timeline dispatcher
    3. Each frame: timeline.get_active_events(t_sec) returns currently active events
    4. Each active event is rendered onto an RGBA overlay and composited
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from PIL import Image, ImageDraw, ImageFont


# ── Animation Easing ──────────────────────────────────────────────────────

def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


EASING = {
    "fade_in": ease_out_cubic,
    "slide_left": ease_out_cubic,
    "slide_right": ease_out_cubic,
    "zoom": ease_out_back,
    "pop": ease_out_back,
    "slide_up": ease_out_cubic,
}


# ── Event Data ────────────────────────────────────────────────────────────

@dataclass
class VisualEvent:
    """A single visual event in the scene timeline."""
    type: str = "callout"            # image, callout, card, diagram
    trigger_time: float = 0.0        # seconds into scene
    duration: float = 5.0            # seconds visible (0 = until end)
    # Content
    src: str = ""                     # image file path (for image type)
    caption: str = ""                 # caption text
    text: str = ""                    # callout text
    subtext: str = ""                 # secondary text
    title: str = ""                    # card title
    body: str = ""                    # card body
    # Layout
    position: str = "center"          # left, right, center, bottom-left, etc.
    anim: str = "fade_in"            # animation type
    anim_duration: float = 0.5       # entrance duration in seconds
    style: str = "default"            # highlight, warning, info
    # Computed at runtime
    _image: Image.Image | None = field(default=None, repr=False)
    _loaded: bool = False

    @property
    def end_time(self) -> float:
        return self.trigger_time + self.duration if self.duration > 0 else 1e9

    def is_active(self, t: float) -> bool:
        return self.trigger_time <= t < self.end_time

    def entrance_progress(self, t: float) -> float:
        """Returns 0.0-1.0 entrance animation progress."""
        if t < self.trigger_time:
            return 0.0
        elapsed = t - self.trigger_time
        return min(1.0, elapsed / max(self.anim_duration, 0.01))

    def exit_progress(self, t: float, exit_duration: float = 0.4) -> float:
        """Returns 0.0-1.0 exit animation progress (1.0 = fully visible)."""
        if self.duration <= 0:
            return 1.0
        time_left = self.end_time - t
        if time_left > exit_duration:
            return 1.0
        return max(0.0, time_left / exit_duration)

    def load_image(self, base_path: str) -> bool:
        """Load image from disk. Returns True on success."""
        if self._loaded:
            return self._image is not None
        self._loaded = True
        full_path = os.path.join(base_path, self.src)
        if os.path.isfile(full_path):
            try:
                self._image = Image.open(full_path).convert("RGBA")
                return True
            except Exception:
                return False
        return False


# ── Event Timeline ─────────────────────────────────────────────────────────

class EventTimeline:
    """Manages visual events for a scene. Given current time, returns active events."""

    def __init__(self, events: list[VisualEvent]):
        self.events = sorted(events, key=lambda e: e.trigger_time)

    @classmethod
    def from_scene(cls, scene: dict, media_base: str = "") -> EventTimeline:
        """Build timeline from scene JSON's visual_events array."""
        raw = scene.get("visual_events", [])
        events = []
        for ev in raw:
            events.append(VisualEvent(
                type=ev.get("type", "callout"),
                trigger_time=ev.get("trigger_time", 0.0),
                duration=ev.get("duration", 5.0),
                src=ev.get("src", ""),
                caption=ev.get("caption", ""),
                text=ev.get("text", ""),
                subtext=ev.get("subtext", ""),
                title=ev.get("title", ""),
                body=ev.get("body", ""),
                position=ev.get("position", "center"),
                anim=ev.get("anim", "fade_in"),
                anim_duration=ev.get("anim_duration", 0.5),
                style=ev.get("style", "default"),
            ))
            # Pre-load images
            if events[-1].type == "image" and events[-1].src:
                events[-1].load_image(media_base)
        return cls(events)

    def get_active_events(self, t: float) -> list[VisualEvent]:
        """Return all events active at time t."""
        return [e for e in self.events if e.is_active(t)]


# ── Position Helpers ───────────────────────────────────────────────────────

# Narration text safe zones per treatment name.
# Format: (x1, y1, x2, y2) — rectangle to avoid when placing events.
# Events that overlap get pushed to the nearest safe region.
# Computed from each treatment's actual text rendering coordinates.
TEXT_SAFE_ZONES = {
    # default: right panel, TEXT_PANEL_LEFT=540, TOP_MARGIN=130, 7 lines × 32px + 30px padding
    "default":  (525, 110, 1250, 390),
    # title_card: centered, text_x=80, text_y=100, 9 lines × 32px + 20px padding = y up to 408
    "title_card": (65, 85, 1225, 415),
    # map_focus: floating card, card_x=640, card_y=440, card_h=240 (text starts at +65 inside)
    "map_focus": (630, 435, 1250, 685),
    # fullscreen_text: text_x=120, text_y=140, 10 lines × 36px = up to 500
    "fullscreen_text": (110, 130, 1170, 505),
    # stark: text_x=100, text_y=120, 8 lines × 40px = up to 440
    "stark": (90, 110, 1190, 445),
}


def _position_rect(w: int, h: int, position: str,
                   content_w: int, content_h: int,
                   margin: int = 30,
                   safe_zone: tuple | None = None) -> tuple[int, int]:
    """Calculate top-left (x, y) for content at given position.
    If safe_zone is provided and the positioned rect overlaps it,
    shift the event to the nearest non-overlapping position."""
    x, y = _raw_position(w, h, position, content_w, content_h, margin)

    if safe_zone:
        x, y = _avoid_overlap(x, y, content_w, content_h, safe_zone, w, h, margin)

    return x, y


def _raw_position(w: int, h: int, position: str,
                  content_w: int, content_h: int,
                  margin: int = 30) -> tuple[int, int]:
    """Raw position without overlap avoidance."""
    if position == "left":
        return margin, (h - content_h) // 2
    elif position == "right":
        return w - content_w - margin, (h - content_h) // 2
    elif position == "center":
        return (w - content_w) // 2, (h - content_h) // 2
    elif position == "top":
        return (w - content_w) // 2, margin + 40
    elif position == "bottom":
        return (w - content_w) // 2, h - content_h - margin - 50
    elif position == "bottom-left":
        return margin, h - content_h - margin - 50
    elif position == "bottom-right":
        return w - content_w - margin, h - content_h - margin - 50
    elif position == "top-left":
        return margin, margin + 40
    elif position == "top-right":
        return w - content_w - margin, margin + 40
    else:
        return (w - content_w) // 2, (h - content_h) // 2


def _avoid_overlap(x: int, y: int, cw: int, ch: int,
                  safe_zone: tuple, w: int, h: int,
                  margin: int = 30) -> tuple[int, int]:
    """If the content rect (x, y, x+cw, y+ch) overlaps safe_zone, shift it.

    Strategy: try placing in the safe area with most space:
    1. Left of safe zone (full height)
    2. Right of safe zone (full height)
    3. Above safe zone (full width, top strip)
    4. Below safe zone (full width, bottom strip)
    5. If nothing fits, keep original position
    """
    zx1, zy1, zx2, zy2 = safe_zone

    # Check if overlap exists
    if x + cw <= zx1 or x >= zx2 or y + ch <= zy1 or y >= zy2:
        return x, y  # no overlap

    # Try left of safe zone
    if zx1 - margin - cw >= margin:
        return margin, (h - ch) // 2

    # Try right of safe zone
    if zx2 + margin + cw <= w - margin:
        return zx2 + margin, (h - ch) // 2

    # Try above safe zone (top strip: y 40 to zy1-10)
    strip_h = zy1 - 50
    if ch <= strip_h and cw <= w - 2 * margin:
        return (w - cw) // 2, 40

    # Try below safe zone (bottom strip: zy2+10 to h-60)
    strip_h = h - 60 - zy2 - 10
    if ch <= strip_h and cw <= w - 2 * margin:
        return (w - cw) // 2, zy2 + 10

    # Fallback: try to fit left-of-zone with reduced x
    if zx1 > cw + 10:
        return zx1 - cw - 10, max(40, min(y, h - ch - 60))

    return x, y  # last resort: keep original


# ── Style Palettes ────────────────────────────────────────────────────────

STYLE_COLORS = {
    "default": {"bg": (0, 0, 0, 190), "border": (233, 69, 96, 220),
                "text": (240, 240, 240, 240), "subtext": (180, 180, 185, 200)},
    "highlight": {"bg": (30, 15, 0, 200), "border": (255, 180, 50, 240),
                  "text": (255, 240, 200, 255), "subtext": (220, 200, 160, 220)},
    "warning": {"bg": (40, 0, 0, 200), "border": (255, 60, 60, 240),
                "text": (255, 220, 220, 255), "subtext": (220, 180, 180, 220)},
    "info": {"bg": (0, 10, 30, 200), "border": (80, 160, 255, 240),
             "text": (220, 230, 255, 255), "subtext": (180, 200, 240, 220)},
}


# ── Event Renderers ───────────────────────────────────────────────────────

def render_event(od: ImageDraw.ImageDraw, event: VisualEvent,
                 t: float, w: int, h: int, accent: tuple,
                 fonts: dict, safe_zone: tuple | None = None) -> None:
    """Render a single visual event onto an RGBA overlay's ImageDraw."""

    ep = event.entrance_progress(t)
    xp = event.exit_progress(t)
    # Combined alpha: entrance ramps up, exit ramps down
    alpha_mult = ep * xp

    if alpha_mult <= 0.01:
        return

    easing_fn = EASING.get(event.anim, ease_out_cubic)
    eased = easing_fn(ep)

    style = STYLE_COLORS.get(event.style, STYLE_COLORS["default"])

    if event.type == "callout":
        _render_callout(od, event, eased, alpha_mult, style, w, h, fonts, safe_zone)
    elif event.type == "image":
        _render_image_event(od, event, eased, alpha_mult, style, w, h, accent, fonts, safe_zone)
    elif event.type == "card":
        _render_card(od, event, eased, alpha_mult, style, w, h, fonts, safe_zone)
    elif event.type == "diagram":
        _render_diagram(od, event, eased, alpha_mult, style, w, h, accent, fonts, safe_zone)


def _apply_alpha(color: tuple, alpha_mult: float) -> tuple:
    """Scale the alpha channel of an RGBA color by a multiplier."""
    if len(color) == 4:
        return (color[0], color[1], color[2], int(color[3] * alpha_mult))
    return (*color, int(255 * alpha_mult))


def _render_callout(od: ImageDraw.ImageDraw, event: VisualEvent,
                    eased: float, alpha_mult: float, style: dict,
                    w: int, h: int, fonts: dict,
                    safe_zone: tuple | None = None) -> None:
    """Render a text callout (highlighted date, name, or fact)."""
    text = event.text or event.caption
    subtext = event.subtext

    font = fonts.get("callout", fonts.get("subtitle", fonts.get("body")))
    sub_font = fonts.get("body", fonts.get("small"))

    # Measure text
    bbox = od.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    total_w = tw + 40
    total_h = th + 20
    if subtext:
        sbbox = od.textbbox((0, 0), subtext, font=sub_font)
        total_w = max(total_w, sbbox[2] - sbbox[0] + 40)
        total_h += sbbox[3] - sbbox[1] + 6

    x, y = _position_rect(w, h, event.position, total_w, total_h, margin=50,
                            safe_zone=safe_zone)

    # Animation offset
    if event.anim in ("slide_left", "slide_up"):
        offset = int((1.0 - eased) * -300)
        if event.anim == "slide_left":
            x += offset
        else:
            y += offset
    elif event.anim == "slide_right":
        x += int((1.0 - eased) * 300)
    elif event.anim == "zoom" or event.anim == "pop":
        cx, cy = x + total_w // 2, y + total_h // 2
        scale = 0.5 + 0.5 * eased
        x = cx - int(total_w * scale / 2)
        y = cy - int(total_h * scale / 2)

    bg_c = _apply_alpha(style["bg"], alpha_mult)
    border_c = _apply_alpha(style["border"], alpha_mult)
    text_c = _apply_alpha(style["text"], alpha_mult)
    subtext_c = _apply_alpha(style["subtext"], alpha_mult)

    # Background + border
    od.rounded_rectangle([(x, y), (x + total_w, y + total_h)],
                         radius=6, fill=bg_c)
    od.rectangle([(x, y), (x + 4, y + total_h)],
                 fill=border_c)

    # Text
    od.text((x + 20, y + 10), text, fill=text_c, font=font)
    if subtext:
        od.text((x + 20, y + th + 16), subtext, fill=subtext_c, font=sub_font)


def _render_image_event(od: ImageDraw.ImageDraw, event: VisualEvent,
                       eased: float, alpha_mult: float, style: dict,
                       w: int, h: int, accent: tuple, fonts: dict,
                       safe_zone: tuple | None = None) -> None:
    """Render an image event with optional caption."""
    if event._image is None:
        # No image loaded — render a placeholder
        _render_placeholder(od, event, eased, alpha_mult, accent, w, h, fonts, safe_zone)
        return

    img = event._image
    # Scale image to fit within a reasonable area
    max_img_w = w // 3 if event.position in ("left", "right") else w // 2
    max_img_h = h // 2
    img_w, img_h = img.size
    scale = min(max_img_w / max(img_w, 1), max_img_h / max(img_h, 1), 1.0)
    new_w, new_h = int(img_w * scale), int(img_h * scale)

    # Resize
    img = img.resize((new_w, new_h), Image.LANCZOS)

    caption_h = 0
    caption_font = fonts.get("caption", fonts.get("small"))
    if event.caption:
        cbbox = od.textbbox((0, 0), event.caption, font=caption_font)
        caption_h = cbbox[3] - cbbox[1] + 16

    total_w = new_w
    total_h = new_h + caption_h

    x, y = _position_rect(w, h, event.position, total_w, total_h, margin=40,
                            safe_zone=safe_zone)

    # Animation
    if event.anim == "slide_left":
        x += int((1.0 - eased) * -400)
    elif event.anim == "slide_right":
        x += int((1.0 - eased) * 400)
    elif event.anim == "fade_in":
        pass  # just alpha
    elif event.anim in ("zoom", "pop"):
        cx, cy = x + total_w // 2, y + total_h // 2
        s = 0.3 + 0.7 * eased
        x = cx - int(total_w * s / 2)
        y = cy - int(total_h * s / 2)
        img = img.resize((int(new_w * s), int(new_h * s)), Image.LANCZOS)

    # Apply alpha to image
    img_alpha = int(255 * alpha_mult)
    if img_alpha < 255:
        img.putalpha(img.split()[-1].point(lambda p: int(p * alpha_mult)))

    # Draw image (paste via parent overlay instead of bitmap API)
    overlay = od._image  # ImageDraw stores ref to underlying Image
    overlay.paste(img, (x, y), img)

    # Caption bar
    if event.caption and caption_h > 0:
        cap_y = y + new_h + 4
        cap_c = _apply_alpha((0, 0, 0, 180), alpha_mult)
        od.rounded_rectangle([(x, cap_y), (x + new_w, cap_y + caption_h)],
                             radius=3, fill=cap_c)
        text_c = _apply_alpha((220, 220, 225, 230), alpha_mult)
        od.text((x + 8, cap_y + 6), event.caption, fill=text_c, font=caption_font)

    # Accent border
    border_c = _apply_alpha((*accent, 200), alpha_mult)
    od.rectangle([(x, y), (x + 2, y + new_h)], fill=border_c)
    od.rectangle([(x, y), (x + new_w, y + 2)], fill=border_c)


def _render_placeholder(od: ImageDraw.ImageDraw, event: VisualEvent,
                        eased: float, alpha_mult: float, accent: tuple,
                        w: int, h: int, fonts: dict,
                        safe_zone: tuple | None = None) -> None:
    """Render a placeholder box when image is missing."""
    ph_w, ph_h = 320, 200
    x, y = _position_rect(w, h, event.position, ph_w, ph_h, margin=40,
                            safe_zone=safe_zone)

    if event.anim == "slide_left":
        x += int((1.0 - eased) * -400)
    elif event.anim == "slide_right":
        x += int((1.0 - eased) * 400)

    bg_c = _apply_alpha((20, 20, 30, int(180 * alpha_mult)), 1.0)
    border_c = _apply_alpha((*accent, 180), alpha_mult)
    label_c = _apply_alpha((150, 150, 155, int(180 * alpha_mult)), 1.0)

    od.rounded_rectangle([(x, y), (x + ph_w, y + ph_h)],
                         radius=6, fill=bg_c)
    od.rectangle([(x, y), (x + 3, y + ph_h)], fill=border_c)

    # Diagonal lines (placeholder pattern)
    for i in range(0, ph_w + ph_h, 20):
        x1 = x + min(i, ph_w)
        y1 = y + max(0, i - ph_w)
        x2 = x + max(0, i - ph_h)
        y2 = y + min(i, ph_h)
        od.line([(x1, y1), (x2, y2)], fill=border_c, width=1)

    font = fonts.get("small", fonts.get("body"))
    label = event.caption or event.src or "[Image]"
    od.text((x + ph_w // 2, y + ph_h // 2), label,
            fill=label_c, font=font, anchor="mm")


def _render_card(od: ImageDraw.ImageDraw, event: VisualEvent,
                 eased: float, alpha_mult: float, style: dict,
                 w: int, h: int, fonts: dict,
                 safe_zone: tuple | None = None) -> None:
    """Render an info card with title + body text."""
    title = event.title or event.caption
    body = event.body or event.text
    if not title:
        return

    title_font = fonts.get("subtitle", fonts.get("title"))
    body_font = fonts.get("body", fonts.get("small"))

    # Measure
    tbbox = od.textbbox((0, 0), title, font=title_font)
    tw = tbbox[2] - tbbox[0]
    card_w = max(tw + 40, 280)

    lines = []
    if body:
        words = body.split()
        line = ""
        for word in words:
            test = line + (" " if line else "") + word
            bb = od.textbbox((0, 0), test, font=body_font)
            if bb[2] - bb[0] > card_w - 30:
                if line:
                    lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)

    card_h = 50 + len(lines) * 22
    x, y = _position_rect(w, h, event.position, card_w, card_h, margin=50,
                            safe_zone=safe_zone)

    # Animation
    if event.anim == "slide_left":
        x += int((1.0 - eased) * -400)
    elif event.anim == "slide_right":
        x += int((1.0 - eased) * 400)

    bg_c = _apply_alpha(style["bg"], alpha_mult)
    border_c = _apply_alpha(style["border"], alpha_mult)
    title_c = _apply_alpha(style["text"], alpha_mult)
    body_c = _apply_alpha(style["subtext"], alpha_mult)

    od.rounded_rectangle([(x, y), (x + card_w, y + card_h)],
                         radius=8, fill=bg_c)
    od.rectangle([(x, y), (x + card_w, y + 3)], fill=border_c)

    od.text((x + 15, y + 12), title, fill=title_c, font=title_font)

    for i, line in enumerate(lines[:6]):  # max 6 lines
        od.text((x + 15, y + 42 + i * 22), line, fill=body_c, font=body_font)


def _render_diagram(od: ImageDraw.ImageDraw, event: VisualEvent,
                    eased: float, alpha_mult: float, style: dict,
                    w: int, h: int, accent: tuple, fonts: dict,
                    safe_zone: tuple | None = None) -> None:
    """Render a diagram/infographic card (procedural placeholder)."""
    # For now, diagrams render as styled text blocks with accent decorations
    # Real diagrams will be loaded as images or drawn per-scene
    title = event.title or event.caption or event.text
    body = event.body or event.subtext

    diag_w, diag_h = 400, 250
    x, y = _position_rect(w, h, event.position, diag_w, diag_h, margin=50,
                            safe_zone=safe_zone)

    bg_c = _apply_alpha(style["bg"], alpha_mult)
    border_c = _apply_alpha((*accent, 200), alpha_mult)
    title_c = _apply_alpha((240, 240, 240, 240), alpha_mult)
    body_c = _apply_alpha((200, 200, 205, 200), alpha_mult)

    # Background
    od.rounded_rectangle([(x, y), (x + diag_w, y + diag_h)],
                         radius=6, fill=bg_c)

    # Accent top bar
    od.rectangle([(x, y), (x + diag_w, y + 4)], fill=border_c)

    # Grid pattern (diagram feel)
    grid_c = _apply_alpha((60, 60, 70, 40), alpha_mult)
    for gx in range(x + 30, x + diag_w, 30):
        od.line([(gx, y + 10), (gx, y + diag_h - 10)], fill=grid_c, width=1)
    for gy in range(y + 30, y + diag_h, 30):
        od.line([(x + 10, gy), (x + diag_w - 10, gy)], fill=grid_c, width=1)

    # Corner markers
    marker_c = _apply_alpha((*accent, int(180 * alpha_mult)), 1.0)
    ml = 20
    od.line([(x + 5, y + 10), (x + 5 + ml, y + 10)], fill=marker_c, width=2)
    od.line([(x + 5, y + 10), (x + 5, y + 10 + ml)], fill=marker_c, width=2)
    od.line([(x + diag_w - 5, y + diag_h - 10), (x + diag_w - 5 - ml, y + diag_h - 10)], fill=marker_c, width=2)
    od.line([(x + diag_w - 5, y + diag_h - 10), (x + diag_w - 5, y + diag_h - 10 - ml)], fill=marker_c, width=2)

    font = fonts.get("subtitle", fonts.get("title"))
    small_font = fonts.get("body", fonts.get("small"))
    if title:
        od.text((x + 15, y + 15), title, fill=title_c, font=font)
    if body:
        od.text((x + 15, y + 45), body, fill=body_c, font=small_font)


# ── Main Render Function ──────────────────────────────────────────────────

def render_visual_events(timeline: EventTimeline, t: float,
                          w: int, h: int, accent: tuple,
                          fonts: dict,
                          treatment_name: str = "") -> Image.Image:
    """Render all active visual events at time t onto an RGBA overlay.
    Returns an RGBA PIL Image ready for alpha_composite.

    treatment_name is used to look up the text safe zone so events
    don't overlap the narration text area."""

    safe_zone = TEXT_SAFE_ZONES.get(treatment_name)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    for event in timeline.get_active_events(t):
        render_event(od, event, t, w, h, accent, fonts, safe_zone=safe_zone)

    return overlay
