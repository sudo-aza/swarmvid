#!/usr/bin/env python3
"""Scene 01: Vor der Stadt — Siedlung an der Leine (pre-1100).

Bespoke visual composition for the opening scene of the Hannover documentary.
Atmospheric, ancient, primordial — deep navy gradients, drifting dust particles,
fading title card, and visual events rendered from scene JSON.

Design decisions (scene-specific):
- Dark radial gradient background (#1a1a2e -> #16213e -> #0f3460)
- Dust particles throughout (slow, ancient atmosphere)
- Title card: fade in/out over first 5 seconds
- Era tag "pre-1100" persistent in top-left
- Visual events from JSON: images, callouts, cards, diagrams
- Segment transitions: subtle cross-fade via alpha
- Timeline bar at bottom, progress bar above it
- Scene counter top-right

Scene script contract:
    prepare(rl) -> dict    — called once, pre-compute assets
    render(rl, frame_idx, total_frames, state) -> Image — per frame
"""

from __future__ import annotations

import math
from PIL import Image

from visuals.colors import hex_rgb, alpha_color


# ── Timing constants ─────────────────────────────────────────────────────────

TITLE_FADE_IN = 0.8          # seconds to fade title in
TITLE_HOLD = 3.0             # seconds to hold title at full opacity
TITLE_FADE_OUT = 1.2         # seconds to fade title out
TITLE_TOTAL = TITLE_FADE_IN + TITLE_HOLD + TITLE_FADE_OUT  # 5.0s

SEG_CROSS_FADE = 0.12        # cross-fade fraction between segments


# ── prepare() ───────────────────────────────────────────────────────────────

def prepare(rl) -> dict:
    """Pre-compute assets for scene 01. Called once before rendering."""
    scene = rl.scene
    gradient_colors = scene.get("gradient", ["#1a1a2e", "#16213e", "#0f3460"])
    parsed = [hex_rgb(c) if isinstance(c, str) else tuple(c[:3])
              for c in gradient_colors]

    # Pre-compute background (expensive — do once)
    rl.gradient(parsed, direction="radial", vignette=0.5, dark_factor=0.85)

    # Store the pre-computed background image
    precomputed_bg = rl._bg.copy()
    precomputed_bg_rgba = rl._bg_rgba.copy()

    # Init dust particles
    rl.init_particles(count=30, seed=42, style="dust")

    # Parse visual events for the scene
    events = scene.get("visual_events", [])
    media_base = rl.media_base

    return {
        "bg": precomputed_bg,
        "bg_rgba": precomputed_bg_rgba,
        "gradient_colors": parsed,
        "title": scene.get("title", ""),
        "subtitle": scene.get("subtitle", ""),
        "era": scene.get("era", ""),
        "scene_num": scene.get("scene_num", 1),
        "total_scenes": scene.get("total_scenes", 28),
        "events": events,
        "media_base": media_base,
        # Pre-load event images
        "loaded_images": _preload_images(events, media_base),
    }


def _preload_images(events: list, media_base: str, target_w: int = 400,
                     target_h: int = 500, max_zoom: float = 1.1) -> dict:
    """Pre-load and pre-scale all image events for fast per-frame rendering.

    For each image event, we pre-scale to (target_w * max_zoom, target_h * max_zoom)
    so Ken Burns crop+resize can operate on the already-scaled image
    instead of opening/resizeing the original every frame.
    """
    cached = {}
    for ev in events:
        if ev.get("type") != "image" or not ev.get("src"):
            continue
        src = ev["src"]
        path = src if src.startswith("/") else f"{media_base}/{src}"
        try:
            img = Image.open(path).convert("RGBA")
            # Scale to cover the target area at max zoom
            iw, ih = img.size
            scale = max((target_w * max_zoom) / max(iw, 1),
                       (target_h * max_zoom) / max(ih, 1))
            scaled = img.resize((int(iw * scale), int(ih * scale)), Image.LANCZOS)
            cached[src] = {
                "img": scaled,
                "w": scaled.width,
                "h": scaled.height,
            }
        except Exception:
            cached[src] = None
    return cached


# ── render() ────────────────────────────────────────────────────────────────

def render(rl, frame_idx: int, total_frames: int, state: dict) -> Image.Image:
    """Render a single frame of scene 01.

    Composition order (back to front):
        1. Pre-computed gradient background
        2. Title card (first 5 seconds only)
        3. Visual events from JSON
        4. Dust particles
        5. Noise grain (very subtle)
        6. Vignette overlay
        7. Era tag (top-left, persistent)
        8. Scene counter (top-right, persistent)
        9. Progress bar
        10. Timeline bar
    """
    t_sec = rl.time(frame_idx)
    w, h = rl.w, rl.h
    scene = rl.scene
    fonts = rl.fonts

    # ── 1. Background (pre-computed) ──
    rl._bg = state["bg"].copy()
    rl._bg_rgba = state["bg_rgba"].copy()

    rl.begin_frame(frame_idx, total_frames)

    # ── 2. Title card (first ~5 seconds) ──
    _render_title(rl, t_sec, state)

    # ── 3. Visual events from scene JSON ──
    _render_visual_events(rl, t_sec, state)

    # ── 4. Dust particles ──
    # Only draw every other frame for performance (particles move slowly anyway)
    if frame_idx % 2 == 0:
        rl.draw_particles()

    # NOTE: noise and vignette removed — gradient() already bakes in vignette,
    # and noise at 0.015 intensity is imperceptible at 24fps.
    # Saves ~2 alpha_composite calls per frame.

    # ── 5. Era tag (top-left) ──
    _render_era_tag(rl, t_sec, state)

    # ── 6. Scene counter ──
    rl.scene_counter(
        scene_num=state["scene_num"],
        total_scenes=state["total_scenes"],
    )

    # ── 7. Progress bar ──
    rl.progress_bar(y=h - 22, height=2)

    # ── 8. Timeline bar ──
    rl.timeline_bar(
        scene_num=state["scene_num"],
        total_scenes=state["total_scenes"],
    )

    return rl.frame()


# ── Title Card ─────────────────────────────────────────────────────────────

def _render_title(rl, t_sec: float, state: dict) -> None:
    """Render the opening title card with fade in/out."""
    if t_sec > TITLE_TOTAL:
        return

    title = state["title"]
    subtitle = state["subtitle"]
    era = state["era"]

    # Compute overall title alpha
    if t_sec < TITLE_FADE_IN:
        title_alpha = rl.ease(t_sec / TITLE_FADE_IN, "out_cubic")
    elif t_sec < TITLE_FADE_IN + TITLE_HOLD:
        title_alpha = 1.0
    else:
        fade_t = (t_sec - TITLE_FADE_IN - TITLE_HOLD) / TITLE_FADE_OUT
        title_alpha = rl.ease(1.0 - fade_t, "in_quad")

    if title_alpha <= 0.01:
        return

    w, h = rl.w, rl.h
    accent = rl.accent

    # Semi-transparent backdrop for title area
    backdrop_h = 260
    backdrop_y = (h - backdrop_h) // 2 - 20
    rl.rect_filled(
        0, backdrop_y, w, backdrop_h,
        fill=(0, 0, 0, int(120 * title_alpha)),
    )

    # Horizontal accent line below title area
    line_y = backdrop_y + backdrop_h - 10
    rl.line(
        80, line_y, w - 80, line_y,
        color=alpha_color(accent, int(160 * title_alpha)),
        width=1,
    )

    # Decorative corner brackets
    bracket_size = 40
    bracket_c = alpha_color(accent, int(140 * title_alpha))
    # Top-left
    rl.bracket(60, backdrop_y + 20, bracket_size, color=bracket_c, corner="tl", width=2)
    # Top-right
    rl.bracket(w - 60, backdrop_y + 20, bracket_size, color=bracket_c, corner="tr", width=2)
    # Bottom-left
    rl.bracket(60, backdrop_y + backdrop_h - 20, bracket_size, color=bracket_c, corner="bl", width=2)
    # Bottom-right
    rl.bracket(w - 60, backdrop_y + backdrop_h - 20, bracket_size, color=bracket_c, corner="br", width=2)

    # Title text
    title_y = backdrop_y + 55
    rl.text(
        title, w // 2, title_y,
        font="title",
        color=(240, 240, 245, int(255 * title_alpha)),
        anchor="mt",
    )

    # Subtitle
    subtitle_y = title_y + 70
    rl.text(
        subtitle, w // 2, subtitle_y,
        font="subtitle",
        color=(200, 200, 210, int(220 * title_alpha)),
        anchor="mt",
    )

    # Era badge
    era_y = subtitle_y + 50
    rl.text(
        era, w // 2, era_y,
        font="era",
        color=alpha_color(accent, int(200 * title_alpha)),
        anchor="mt",
    )


# ── Visual Events ──────────────────────────────────────────────────────────

def _render_visual_events(rl, t_sec: float, state: dict) -> None:
    """Render active visual events from the scene JSON."""
    events = state["events"]
    loaded = state["loaded_images"]

    for ev in events:
        trigger = ev.get("trigger_time", 0)
        duration = ev.get("duration", 5.0)
        anim_dur = ev.get("anim_duration", 0.5)

        # Check if event is active
        if t_sec < trigger:
            continue
        if duration > 0 and t_sec >= trigger + duration:
            continue

        # Calculate entrance and exit progress
        entrance_t = min(1.0, (t_sec - trigger) / max(anim_dur, 0.01))
        exit_dur = 0.4
        if duration > 0:
            time_left = (trigger + duration) - t_sec
            exit_t = min(1.0, time_left / exit_dur)
        else:
            exit_t = 1.0
        alpha_mult = rl.ease(entrance_t, "out_cubic") * max(0.0, exit_t)

        if alpha_mult <= 0.01:
            continue

        ev_type = ev.get("type", "callout")
        anim = ev.get("anim", "fade_in")
        position = ev.get("position", "center")
        style = ev.get("style", "default")

        if ev_type == "callout":
            _render_callout(rl, ev, alpha_mult, anim, entrance_t)
        elif ev_type == "image":
            cached = loaded.get(ev.get("src", ""))
            _render_image_event(rl, ev, alpha_mult, anim, entrance_t, cached)
        elif ev_type == "card":
            _render_card(rl, ev, alpha_mult, anim, entrance_t)
        elif ev_type == "diagram":
            _render_diagram(rl, ev, alpha_mult, anim, entrance_t)


def _render_callout(rl, ev: dict, alpha_mult: float, anim: str,
                    entrance_t: float) -> None:
    """Render a callout event (date, fact highlight)."""
    text = ev.get("text", ev.get("caption", ""))
    subtext = ev.get("subtext", "")
    position = ev.get("position", "center")
    style = ev.get("style", "default")

    rl.callout(
        text, subtext=subtext,
        position=position, style=style,
        alpha_mult=alpha_mult,
    )


def _render_image_event(rl, ev: dict, alpha_mult: float, anim: str,
                        entrance_t: float, cached: dict | None) -> None:
    """Render an image event with Ken Burns effect using pre-cached image."""
    position = ev.get("position", "left")
    caption = ev.get("caption", "")
    trigger = ev.get("trigger_time", 0)
    duration = ev.get("duration", 8.0)
    src = ev.get("src", "")

    if cached is None or "img" not in cached:
        return

    img = cached["img"]
    scaled_w = cached["w"]
    scaled_h = cached["h"]

    # Determine placement based on position
    w, h = rl.w, rl.h
    if position in ("left",):
        img_x, img_y = 60, 120
        img_w, img_h = w // 3 - 20, h - 240
    elif position in ("right",):
        img_x, img_y = w - (w // 3) - 40, 120
        img_w, img_h = w // 3 - 20, h - 240
    elif position in ("bottom-left",):
        img_x, img_y = 60, h - (h // 2) - 40
        img_w, img_h = w // 3, h // 2 - 20
    else:
        img_x, img_y = (w - w // 2) // 2, 120
        img_w, img_h = w // 2, h - 240

    # Ken Burns: crop from pre-scaled image (no file I/O per frame)
    kb_progress = min(1.0, (rl.time(rl._frame_idx) - trigger) / max(duration, 1.0))
    max_zoom = 1.1
    current_zoom = 1.0 + (max_zoom - 1.0) * kb_progress
    crop_w = int(img_w / current_zoom)
    crop_h = int(img_h / current_zoom)
    # Pan offset
    max_pan_x = max(0, scaled_w - crop_w)
    max_pan_y = max(0, scaled_h - crop_h)
    px = int(max_pan_x * 0.2 * kb_progress)
    py = int(max_pan_y * 0.15 * kb_progress)
    px = min(px, max(0, scaled_w - crop_w))
    py = min(py, max(0, scaled_h - crop_h))
    cropped = img.crop((px, py, px + crop_w, py + crop_h))
    cropped = cropped.resize((img_w, img_h), Image.BILINEAR)

    # Apply alpha
    if alpha_mult < 1.0:
        alpha_arr = cropped.split()[-1]
        alpha_arr = alpha_arr.point(lambda p: int(p * alpha_mult))
        cropped.putalpha(alpha_arr)

    # Paste onto overlay
    ov, od = rl._ensure_overlay()
    ov.paste(cropped, (img_x, img_y), cropped)

    # Caption bar below image
    if caption and alpha_mult > 0.1:
        cap_y = img_y + img_h + 6
        cap_h = 28
        rl.rect_filled(
            img_x, cap_y, img_w, cap_h,
            fill=(0, 0, 0, int(180 * alpha_mult)),
            radius=3,
        )
        rl.text(
            caption, img_x + 10, cap_y + 5,
            font="small",
            color=(210, 210, 215, int(230 * alpha_mult)),
        )

    # Accent border (left and top edges)
    if alpha_mult > 0.1:
        accent_c = alpha_color(rl.accent, int(180 * alpha_mult))
        rl.line(img_x, img_y, img_x, img_y + img_h, color=accent_c, width=2)
        rl.line(img_x, img_y, img_x + img_w, img_y, color=accent_c, width=2)


def _render_card(rl, ev: dict, alpha_mult: float, anim: str,
                 entrance_t: float) -> None:
    """Render an info card event."""
    title = ev.get("title", ev.get("caption", ""))
    body = ev.get("body", ev.get("text", ""))
    position = ev.get("position", "right")

    if not title:
        return

    rl.card(
        title, body=body,
        position=position,
        alpha_mult=alpha_mult,
    )


def _render_diagram(rl, ev: dict, alpha_mult: float, anim: str,
                    entrance_t: float) -> None:
    """Render a diagram/infographic card."""
    title = ev.get("title", ev.get("caption", ""))
    body = ev.get("body", ev.get("subtext", ""))
    position = ev.get("position", "left")

    if not title:
        return

    # Use card style for now (diagrams as structured text blocks)
    rl.card(
        title, body=body,
        position=position,
        style="default",
        alpha_mult=alpha_mult,
    )

    # Add diagram-style decorations (corner markers, grid)
    if alpha_mult > 0.1:
        _add_diagram_decor(rl, position, alpha_mult, entrance_t)


def _add_diagram_decor(rl, position: str, alpha_mult: float,
                       entrance_t: float) -> None:
    """Add diagram-style decorative elements."""
    w, h = rl.w, rl.h
    accent = rl.accent

    # Find approximate card position for decorations
    if position == "left":
        cx, cy = 60, 150
        cw, ch = 400, 200
    elif position == "bottom":
        cx, cy = (w - 400) // 2, h - 220
        cw, ch = 400, 120
    else:
        cx, cy = w - 460, 150
        cw, ch = 400, 200

    # Corner brackets
    bracket_size = 15
    bracket_c = alpha_color(accent, int(120 * alpha_mult))
    rl.bracket(cx + 5, cy + 5, bracket_size, color=bracket_c, corner="tl", width=1)
    rl.bracket(cx + cw - 5, cy + 5, bracket_size, color=bracket_c, corner="tr", width=1)
    rl.bracket(cx + 5, cy + ch - 5, bracket_size, color=bracket_c, corner="bl", width=1)
    rl.bracket(cx + cw - 5, cy + ch - 5, bracket_size, color=bracket_c, corner="br", width=1)

    # Thin grid lines
    grid_c = alpha_color((80, 80, 90), int(30 * alpha_mult))
    for gx in range(cx + 30, cx + cw, 25):
        rl.line(gx, cy + 10, gx, cy + ch - 10, color=grid_c, width=1)
    for gy in range(cy + 30, cy + ch, 25):
        rl.line(cx + 10, gy, cx + cw - 10, gy, color=grid_c, width=1)


# ── Era Tag ─────────────────────────────────────────────────────────────────

def _render_era_tag(rl, t_sec: float, state: dict) -> None:
    """Render the persistent era tag in the top-left corner."""
    era = state.get("era", "")
    if not era:
        return

    # Fade in over first 2 seconds
    alpha = min(1.0, t_sec / 2.0)

    rl.text(
        era, 60, 55,
        font="era",
        color=alpha_color(rl.accent, int(160 * alpha)),
    )
