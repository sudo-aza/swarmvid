#!/usr/bin/env python3
"""generic_scene.py — Universal scene renderer for swarmvid.

Provides prepare() and render() functions that work for ANY scene
using the scene JSON's gradient, accent, visual_events, and treatment.
Each scene_XX.py is a thin wrapper that imports these functions.

Rendering pipeline (per frame, back to front):
    1. Pre-computed gradient background
    2. Title card (first ~5 seconds only, fade in/out)
    3. Visual events from JSON (callouts, cards, images, diagrams)
    4. Narration text (word reveal, position depends on treatment)
    5. Particles
    6. Era tag (top-left, persistent after fade-in)
    7. Scene counter (top-right)
    8. Progress bar
    9. Timeline bar
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


# ── prepare() ───────────────────────────────────────────────────────────────

def prepare(rl) -> dict:
    """Pre-compute assets for any scene. Called once before rendering."""
    scene = rl.scene
    treatment = scene.get("visual_treatment", "default")

    # Parse gradient
    gradient_colors = [hex_rgb(c) if isinstance(c, str) else tuple(c[:3])
                      for c in scene.get("gradient", ["#1a1a2e", "#16213e", "#0f3460"])]

    # Pre-compute background
    direction = "radial"
    vignette = 0.5
    dark_factor = 0.85
    if treatment == "fullscreen_text":
        direction = "vertical"
        vignette = 0.3
        dark_factor = 0.7
    elif treatment == "stark":
        vignette = 0.7
        dark_factor = 0.6

    rl.gradient(gradient_colors, direction=direction, vignette=vignette, dark_factor=dark_factor)

    # Save pre-computed background
    precomputed_bg = rl._bg.copy()
    precomputed_bg_rgba = rl._bg_rgba.copy()

    # Init particles based on treatment
    scene_num = scene.get("scene_num", 1)
    if treatment == "stark":
        rl.init_particles(count=8, seed=scene_num * 137, style="dust")
    elif treatment == "fullscreen_text":
        rl.init_particles(count=5, seed=scene_num * 137, style="dust")
    else:
        rl.init_particles(count=25, seed=scene_num * 137, style="warm_glow")

    # Pre-load visual event images
    events = scene.get("visual_events", [])
    media_base = rl.media_base

    return {
        "bg": precomputed_bg,
        "bg_rgba": precomputed_bg_rgba,
        "gradient_colors": gradient_colors,
        "title": scene.get("title", ""),
        "subtitle": scene.get("subtitle", ""),
        "era": scene.get("era", ""),
        "scene_num": scene_num,
        "total_scenes": scene.get("total_scenes", 28),
        "events": events,
        "media_base": media_base,
        "treatment": treatment,
        # Pre-load event images
        "loaded_images": _preload_images(events, media_base),
    }


def _preload_images(events: list, media_base: str, target_w: int = 400,
                     target_h: int = 500, max_zoom: float = 1.1) -> dict:
    """Pre-load and pre-scale all image events for fast per-frame rendering."""
    cached = {}
    for ev in events:
        if ev.get("type") != "image" or not ev.get("src"):
            continue
        src = ev["src"]
        path = src if src.startswith("/") else f"{media_base}/{src}"
        try:
            img = Image.open(path).convert("RGBA")
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


# ── render() ───────────────────────────────────────────────────────────────

def render(rl, frame_idx: int, total_frames: int, state: dict) -> Image.Image:
    """Render a single frame for any scene.

    Composition order (back to front):
        1. Pre-computed gradient background
        2. Title card (first ~5 seconds only)
        3. Visual events from JSON
        4. Narration text (word reveal)
        5. Particles
        6. Era tag (top-left, persistent)
        7. Scene counter (top-right)
        8. Progress bar
        9. Timeline bar
    """
    t_sec = rl.time(frame_idx)
    w, h = rl.w, rl.h
    fonts = rl.fonts
    treatment = state["treatment"]

    # ── 1. Background (pre-computed) ──
    rl._bg = state["bg"].copy()
    rl._bg_rgba = state["bg_rgba"].copy()

    rl.begin_frame(frame_idx, total_frames)

    # ── 2. Title card (first ~5 seconds) ──
    _render_title(rl, t_sec, state)

    # ── 3. Visual events from scene JSON ──
    _render_visual_events(rl, t_sec, state)

    # ── 4. Narration text ──
    _render_narration(rl, t_sec, frame_idx, total_frames, state)

    # ── 5. Particles ──
    if frame_idx % 2 == 0:
        rl.draw_particles()

    # ── 6. Era tag (top-left) ──
    _render_era_tag(rl, t_sec, state)

    # ── 7. Scene counter ──
    rl.scene_counter(
        scene_num=state["scene_num"],
        total_scenes=state["total_scenes"],
    )

    # ── 8. Progress bar ──
    rl.progress_bar(y=h - 22, height=2)

    # ── 9. Timeline bar ──
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
    rl.bracket(60, backdrop_y + 20, bracket_size, color=bracket_c, corner="tl", width=2)
    rl.bracket(w - 60, backdrop_y + 20, bracket_size, color=bracket_c, corner="tr", width=2)
    rl.bracket(60, backdrop_y + backdrop_h - 20, bracket_size, color=bracket_c, corner="bl", width=2)
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
    if subtitle:
        subtitle_y = title_y + 70
        rl.text(
            subtitle, w // 2, subtitle_y,
            font="subtitle",
            color=(200, 200, 210, int(220 * title_alpha)),
            anchor="mt",
        )

    # Era badge
    if era:
        era_y = subtitle_y + 50 if subtitle else title_y + 50
        rl.text(
            era, w // 2, era_y,
            font="era",
            color=alpha_color(accent, int(200 * title_alpha)),
            anchor="mt",
        )


# ── Narration Text ──────────────────────────────────────────────────────────

def _render_narration(rl, t_sec: float, frame_idx: int, total_frames: int,
                     state: dict) -> None:
    """Render word-by-word narration text."""
    if t_sec < TITLE_TOTAL:
        return  # Don't show narration during title card

    segments = rl.scene.get("segments", [])
    if not segments:
        return

    seg_idx, seg_progress = rl.segment_at_time(t_sec)
    if seg_idx >= len(segments):
        return

    seg = segments[seg_idx]
    text = seg.get("text", "")

    treatment = state["treatment"]
    w, h = rl.w, rl.h

    # Determine text layout based on treatment
    if treatment == "fullscreen_text":
        text_x = 80
        text_y = 120
        text_w = w - 160
        max_lines = 14
        line_height = 32
    elif treatment == "stark":
        text_x = (w * 2) // 5 + 40
        text_y = 120
        text_w = (w * 3) // 5 - 80
        max_lines = 8
        line_height = 28
    else:
        # default, map_focus, title_card — text on right portion
        text_x = (w * 2) // 5 + 40
        text_y = 120
        text_w = (w * 3) // 5 - 80
        max_lines = 10
        line_height = 28

    # Text backdrop
    backdrop_h = max_lines * line_height + 30
    rl.rect_filled(
        text_x - 15, text_y - 15,
        text_w + 30, backdrop_h,
        fill=(0, 0, 0, 70),
        radius=6,
    )
    # Accent left edge
    rl.rect_filled(
        text_x - 15, text_y - 15,
        3, backdrop_h,
        fill=alpha_color(rl.accent, 140),
    )

    # Word reveal
    reveal_progress = min(1.0, seg_progress * 1.3)  # Slightly faster than segment
    rl.reveal_text(
        text, reveal_progress,
        text_x, text_y, text_w,
        font="body",
        color=(240, 240, 240, 230),
        max_lines=max_lines,
        line_height=line_height,
    )

    # Segment progress indicator
    bar_y = text_y + backdrop_h + 10
    rl.rect_filled(text_x, bar_y, text_w, 3, fill=(60, 60, 60, 80))
    fill_w = int(text_w * seg_progress)
    rl.rect_filled(text_x, bar_y, fill_w, 3, fill=alpha_color(rl.accent, 160))

    # Scene title in top area of text panel
    if treatment != "fullscreen_text":
        title = state["title"]
        if title:
            rl.text(title, text_x, 50,
                    font="subtitle",
                    color=alpha_color((220, 220, 220), 200))


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
    style = ev.get("style", "default")

    if not title:
        return

    rl.card(
        title, body=body,
        position=position,
        style=style,
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

    # Use card style for diagrams (structured text blocks)
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

    if position == "left":
        cx, cy = 60, 150
        cw, ch = 400, 200
    elif position == "bottom":
        cx, cy = (w - 400) // 2, h - 220
        cw, ch = 400, 120
    else:
        cx, cy = w - 460, 150
        cw, ch = 400, 200

    bracket_size = 15
    bracket_c = alpha_color(accent, int(120 * alpha_mult))
    rl.bracket(cx + 5, cy + 5, bracket_size, color=bracket_c, corner="tl", width=1)
    rl.bracket(cx + cw - 5, cy + 5, bracket_size, color=bracket_c, corner="tr", width=1)
    rl.bracket(cx + 5, cy + ch - 5, bracket_size, color=bracket_c, corner="bl", width=1)
    rl.bracket(cx + cw - 5, cy + ch - 5, bracket_size, color=bracket_c, corner="br", width=1)

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

    alpha = min(1.0, t_sec / 2.0)
    rl.text(
        era, 60, 55,
        font="era",
        color=alpha_color(rl.accent, int(160 * alpha)),
    )
