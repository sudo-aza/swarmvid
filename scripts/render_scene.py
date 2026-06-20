#!/usr/bin/env python3
"""
render_scene.py — Documentary motion graphics renderer.

Renders Pillow frames piped to ffmpeg for H.264 MP4 output at 1280x720.

Visual design:
  - Full-screen dark vignette with gradient backgrounds
  - Geometric accent animations (animated lines, circles, grid)
  - Split layout: left visual panel + right narration panel
  - Word-by-word text reveal animation
  - Cinematic title sequences with animated decorative elements
  - Floating light particles (warm glow, not cold dots)
  - Horizontal progress timeline at bottom

Usage:
    python3 render_scene.py --scene-json scene.json --audio audio.wav --output scene_N.mp4
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
import time
import wave

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Constants ──────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 24

# Layout
VISUAL_PANEL_W = 480      # left visual panel width
TEXT_PANEL_LEFT = 500     # left edge of text panel
TEXT_PANEL_RIGHT = 1240   # right edge of text panel
TEXT_PANEL_W = TEXT_PANEL_RIGHT - TEXT_PANEL_LEFT

# Title card
TITLE_CARD_DURATION = 3.5  # seconds for title card

# Particles
PARTICLE_COUNT = 30

# Typography
BODY_FONT_SIZE = 24
BODY_LINE_HEIGHT = 34
MAX_VISIBLE_LINES = 6
TEXT_TOP_MARGIN = 180

# Animation speeds
WORD_REVEAL_SPEED = 0.03   # fraction of segment duration per word
SEGMENT_CROSS_FADE = 0.08  # fraction of segment for cross-fade


# ── Font Loading ──────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _font(path, size):
    key = (path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]

def get_fonts():
    sans = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    sans_b = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    serif = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
    if not os.path.exists(sans):
        sans = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        sans_b = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        serif = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
    return {
        "title":    _font(serif, 52),
        "subtitle": _font(sans, 26),
        "body":     _font(sans, BODY_FONT_SIZE),
        "bold":     _font(sans_b, BODY_FONT_SIZE),
        "small":    _font(sans, 18),
        "tiny":     _font(sans, 14),
        "era":      _font(serif, 22),
    }


# ── Color Utilities ─────────────────────────────────────────────────────────────
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def lerp(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def alpha_color(rgb, a):
    return (*rgb, int(max(0, min(255, a))))


# ── Gradient ──────────────────────────────────────────────────────────────────
def make_gradient(w, h, colors):
    """Radial-ish gradient: darker edges, lighter center."""
    n = len(colors)
    img = Image.new("RGB", (w, h))
    px = img.load()
    cx, cy = w // 2, h // 2
    max_dist = math.sqrt(cx*cx + cy*cy)
    for y in range(h):
        for x in range(w):
            # Distance from center, normalized
            dx = (x - cx) / cx
            dy = (y - cy) / cy
            d = math.sqrt(dx*dx + dy*dy) / 1.414  # 0..1
            d = min(d, 1.0)
            # Map to color stops
            t = d * (n - 1)
            idx = min(int(t), n - 2)
            frac = t - idx
            c = lerp(colors[idx], colors[idx+1], frac)
            px[x, y] = c
    return img


def make_vignette(w, h, strength=0.6):
    """Dark vignette overlay — edges darker than center."""
    img = Image.new("L", (w, h))
    px = img.load()
    cx, cy = w // 2, h // 2
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / cx
            dy = (y - cy) / cy
            d = math.sqrt(dx*dx + dy*dy)
            brightness = int(255 * max(0, 1.0 - d * strength))
            px[x, y] = brightness
    return img


# ── Pre-computation ──────────────────────────────────────────────────────────
def precompute_particles(count, w, h, seed):
    rng = random.Random(seed)
    particles = []
    for _ in range(count):
        particles.append({
            "x": rng.randint(0, w),
            "y_base": rng.randint(0, h),
            "speed": rng.uniform(0.2, 0.8),
            "size": rng.randint(2, 5),
            "brightness": rng.randint(80, 200),
            "phase": rng.uniform(0, math.tau),
        })
    return particles


def prewrap_text(segments, font, max_width):
    result = []
    for seg in segments:
        lines = []
        text = seg.get("text", "")
        words = text.split()
        current = ""
        dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
        for word in words:
            test = current + (" " if current else "") + word
            bbox = dummy.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        result.append({"lines": lines, "words": text.split()})
    return result


# ── Drawing Helpers ───────────────────────────────────────────────────────────
def draw_accent_line(draw, x1, y1, x2, y2, color, width=2, progress=1.0):
    """Draw a line that animates from left to right."""
    if progress <= 0:
        return
    px = int(x1 + (x2 - x1) * min(progress, 1.0))
    py = int(y1 + (y2 - y1) * min(progress, 1.0))
    draw.line([(x1, y1), (px, py)], fill=color, width=width)


def draw_circle_outline(draw, cx, cy, r, color, width=2, progress=1.0):
    """Draw a circle outline that animates around."""
    if progress <= 0:
        return
    # Draw arc from 0 to progress * 360
    bbox = [cx - r, cy - r, cx + r, cy + r]
    start = 0
    end = progress * 360
    draw.arc(bbox, start, end, fill=color, width=width)


def draw_horizontal_grid(draw, x, y, w, h, color, spacing=40, scroll_offset=0):
    """Draw faint horizontal grid lines (animated scroll)."""
    for gy in range(0, h, spacing):
        ly = y + gy + (scroll_offset % spacing)
        if y <= ly <= y + h:
            draw.line([(x, ly), (x + w, ly)], fill=color, width=1)


# ── Render Frame ─────────────────────────────────────────────────────────────
def render_frame(frame_idx, total_frames, scene, seg_idx, seg_progress,
                 fonts, accent_rgb, gradient_colors, bg_base, vignette,
                 particles, wrapped, scene_num, total_scenes):
    """Render one frame. Returns RGB PIL Image."""
    segments = scene.get("segments", [])
    num_segs = len(segments)
    accent = accent_rgb

    # ── Cross-segment fade ──
    if seg_progress > (1.0 - SEGMENT_CROSS_FADE) and seg_idx < num_segs - 1:
        cross_fade = (1.0 - seg_progress) / SEGMENT_CROSS_FADE
    elif seg_progress < SEGMENT_CROSS_FADE and seg_idx > 0:
        cross_fade = seg_progress / SEGMENT_CROSS_FADE
    else:
        cross_fade = 1.0
    cross_fade = max(0.0, min(1.0, cross_fade))

    # ── Background: cached gradient + vignette ──
    img = bg_base.copy()
    img.paste(Image.new("L", (W, H), int(255 * 0.85)), mask=vignette.point(lambda p: int(p * 0.85)))

    # ── Floating warm particles ──
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for p in particles:
        py = (p["y_base"] - frame_idx * p["speed"]) % H
        pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.03 + p["phase"])
        a = int(p["brightness"] * pulse)
        s = int(p["size"] * (0.8 + 0.2 * pulse))
        # Warm glow particle
        od.ellipse([p["x"]-s, py-s, p["x"]+s, py+s],
                   fill=(255, 220, 180, min(255, a)))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img_rgba = img.convert("RGBA")

    # ── Determine if we're in title card phase ──
    first_seg_dur = segments[0].get("duration_s", 5.0)
    title_card_time = TITLE_CARD_DURATION / first_seg_dur  # as fraction
    in_title = (seg_idx == 0 and seg_progress < title_card_time)

    if in_title:
        # ═══ TITLE CARD ═══
        tp = seg_progress / title_card_time  # 0..1 through title card
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        # Full-screen dark overlay, fading in
        dark_a = int(200 * min(1.0, tp * 4))
        od.rectangle([(0, 0), (W, H)], fill=(0, 0, 0, dark_a))

        # Animated decorative elements
        deco_a = max(0, min(255, int(255 * min(1.0, (tp - 0.1) * 5))))

        # Horizontal accent lines that grow from center
        title = scene.get("title", "")
        title_bbox = od.textbbox((0, 0), title, font=fonts["title"])
        title_w = title_bbox[2] - title_bbox[0]
        cx = W // 2
        cy = H // 2 - 40

        # Top accent line
        if tp > 0.05:
            line_prog = min(1.0, (tp - 0.05) * 3)
            half_w = int(title_w * 0.7 * line_prog)
            od.line([(cx - half_w, cy - 50), (cx + half_w, cy - 50)],
                    fill=alpha_color(accent, deco_a), width=3)

        # Title text
        if tp > 0.1:
            text_a = min(255, int(255 * min(1.0, (tp - 0.1) * 5)))
            od.text((cx - title_w // 2, cy), title,
                    fill=alpha_color((255, 255, 255), text_a), font=fonts["title"])

        # Bottom accent line
        if tp > 0.2:
            line_prog2 = min(1.0, (tp - 0.2) * 3)
            half_w2 = int(title_w * 0.5 * line_prog2)
            od.line([(cx - half_w2, cy + 65), (cx + half_w2, cy + 65)],
                    fill=alpha_color(accent, deco_a), width=2)

        # Subtitle
        subtitle = scene.get("subtitle", "")
        if subtitle and tp > 0.25:
            sub_a = min(255, int(255 * min(1.0, (tp - 0.25) * 4)))
            sub_bbox = od.textbbox((0, 0), subtitle, font=fonts["subtitle"])
            sub_w = sub_bbox[2] - sub_bbox[0]
            od.text((cx - sub_w // 2, cy + 80), subtitle,
                    fill=alpha_color((200, 200, 200), sub_a), font=fonts["subtitle"])

        # Era text (small, top-left)
        era = scene.get("era", "")
        if era and tp > 0.3:
            era_a = min(255, int(255 * min(1.0, (tp - 0.3) * 4)))
            od.text((80, 80), era,
                    fill=alpha_color((150, 150, 150), era_a), font=fonts["era"])

        # Animated corner brackets
        if tp > 0.15:
            bracket_a = min(200, int(200 * min(1.0, (tp - 0.15) * 3)))
            bracket_len = int(60 * min(1.0, (tp - 0.15) * 2))
            bc = alpha_color(accent, bracket_a)
            margin = 60
            # Top-left bracket
            od.line([(margin, margin), (margin + bracket_len, margin)], fill=bc, width=2)
            od.line([(margin, margin), (margin, margin + bracket_len)], fill=bc, width=2)
            # Bottom-right bracket
            od.line([(W - margin, H - margin), (W - margin - bracket_len, H - margin)], fill=bc, width=2)
            od.line([(W - margin, H - margin), (W - margin, H - margin - bracket_len)], fill=bc, width=2)

        # Scene number indicator (bottom-right)
        if tp > 0.4:
            num_a = min(180, int(180 * min(1.0, (tp - 0.4) * 3)))
            num_text = f"{scene_num} / {total_scenes}"
            od.text((W - 80, H - 60), num_text,
                    fill=alpha_color((120, 120, 120), num_a), font=fonts["tiny"],
                    anchor="rb")

        img_rgba = Image.alpha_composite(img_rgba, overlay)

    else:
        # ═══ NARRATION MODE ═══
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)

        # ── Left visual panel: decorative geometric area ──
        # Dark panel with accent border
        od.rounded_rectangle(
            [(30, 80), (VISUAL_PANEL_W + 30, H - 80)],
            radius=8, fill=(0, 0, 0, 100), outline=alpha_color(accent, 60), width=1
        )

        # Animated grid inside visual panel
        grid_scroll = frame_idx * 0.5
        draw_horizontal_grid(od, 45, 90, VISUAL_PANEL_W, H - 170,
                              alpha_color(accent, 25), spacing=50, scroll_offset=grid_scroll)

        # Animated accent circle in visual panel
        circle_y = 200 + int(30 * math.sin(frame_idx * 0.02))
        circle_r = 60 + int(10 * math.sin(frame_idx * 0.015))
        draw_circle_outline(od, 30 + VISUAL_PANEL_W // 2, circle_y,
                           circle_r, alpha_color(accent, 80), width=2,
                           progress=min(1.0, seg_progress * 3))

        # Animated horizontal lines in visual panel
        if seg_progress > 0.1:
            line_prog = min(1.0, (seg_progress - 0.1) * 2)
            draw_accent_line(od, 50, 320, 50 + int(380 * line_prog), 320,
                              alpha_color(accent, 60), width=1)
        if seg_progress > 0.2:
            line_prog2 = min(1.0, (seg_progress - 0.2) * 2)
            draw_accent_line(od, 50, 380, 50 + int(300 * line_prog2), 380,
                              alpha_color(accent, 40), width=1)

        # Small decorative dots in visual panel
        dot_y = 440
        for dx in range(0, VISUAL_PANEL_W - 40, 30):
            dot_x = 50 + dx
            dot_pulse = 0.3 + 0.7 * abs(math.sin(frame_idx * 0.02 + dx * 0.05))
            od.ellipse([dot_x - 2, dot_y - 2, dot_x + 2, dot_y + 2],
                       fill=alpha_color(accent, int(60 * dot_pulse)))

        # ── Right narration panel ──
        seg_data = wrapped[seg_idx]
        words = seg_data["words"]
        lines = seg_data["lines"]

        # Dark backdrop for text area
        od.rounded_rectangle(
            [(TEXT_PANEL_LEFT - 20, TEXT_TOP_MARGIN - 20),
             (TEXT_PANEL_RIGHT + 20, TEXT_TOP_MARGIN + MAX_VISIBLE_LINES * BODY_LINE_HEIGHT + 30)],
            radius=8, fill=(0, 0, 0, 100)
        )

        # Accent left border
        od.rectangle(
            [(TEXT_PANEL_LEFT - 20, TEXT_TOP_MARGIN - 10),
             (TEXT_PANEL_LEFT - 17, TEXT_TOP_MARGIN + MAX_VISIBLE_LINES * BODY_LINE_HEIGHT + 20)],
            fill=alpha_color(accent, 180)
        )

        # Word-by-word reveal
        total_words = len(words)
        words_to_show = int(seg_progress * total_words * 1.5)  # speed factor
        words_to_show = max(1, min(total_words, words_to_show))

        # Build revealed text and figure out which lines to show
        revealed = " ".join(words[:words_to_show])
        revealed_lines = []
        dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
        current = ""
        for word in words[:words_to_show]:
            test = current + (" " if current else "") + word
            bbox = dummy.textbbox((0, 0), test, font=fonts["body"])
            if bbox[2] - bbox[0] > TEXT_PANEL_W:
                if current:
                    revealed_lines.append(current)
                current = word
            else:
                current = test
        if current:
            revealed_lines.append(current)

        # Scroll if too many lines
        if len(revealed_lines) > MAX_VISIBLE_LINES:
            scroll_start = len(revealed_lines) - MAX_VISIBLE_LINES
            visible = revealed_lines[scroll_start:]
        else:
            visible = revealed_lines

        # Draw text lines
        text_a = int(255 * cross_fade)
        for i, line in enumerate(visible):
            y = TEXT_TOP_MARGIN + i * BODY_LINE_HEIGHT
            od.text((TEXT_PANEL_LEFT, y), line,
                    fill=(240, 240, 240, text_a), font=fonts["body"])

        # Cursor blink on last word
        if words_to_show < total_words:
            cursor_visible = int(frame_idx * 0.1) % 2 == 0
            if cursor_visible and visible:
                last_line = visible[-1]
                bbox = dummy.textbbox((0, 0), last_line, font=fonts["body"])
                cursor_x = TEXT_PANEL_LEFT + (bbox[2] - bbox[0]) + 4
                cursor_y = TEXT_TOP_MARGIN + (len(visible) - 1) * BODY_LINE_HEIGHT
                od.rectangle([(cursor_x, cursor_y + 2), (cursor_x + 2, cursor_y + BODY_FONT_SIZE)],
                              fill=alpha_color(accent, 200))

        # ── Bottom: segment progress indicator ──
        bar_y = H - 50
        bar_h = 3
        od.rectangle([(TEXT_PANEL_LEFT, bar_y), (TEXT_PANEL_RIGHT, bar_y + bar_h)],
                      fill=(60, 60, 60, 100))
        fill_w = int(TEXT_PANEL_W * seg_progress)
        od.rectangle([(TEXT_PANEL_LEFT, bar_y), (TEXT_PANEL_LEFT + fill_w, bar_y + bar_h)],
                      fill=alpha_color(accent, 180))

        # ── Bottom-right: source citations ──
        sources = scene.get("sources", [])
        if sources:
            src_text = " | ".join(sources[:2])
            od.text((W - 40, H - 45), src_text,
                    fill=(130, 130, 130, 140), font=fonts["tiny"], anchor="rb")

        # ── Top-right: scene number ──
        num_text = f"{scene_num} / {total_scenes}"
        od.text((W - 40, 20), num_text,
                fill=(100, 100, 100, 120), font=fonts["tiny"], anchor="rt")

        # ── Top-left: era ──
        era = scene.get("era", "")
        if era:
            od.text((50, 20), era,
                    fill=(140, 140, 140, 140), font=fonts["small"])

        img_rgba = Image.alpha_composite(img_rgba, overlay)

    # ── Global: thin progress bar at very bottom ──
    progress = frame_idx / max(total_frames - 1, 1)
    bar_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar_overlay)
    bd.rectangle([(0, H - 3), (W, H)], fill=(30, 30, 30, 150))
    bd.rectangle([(0, H - 3), (int(W * progress), H)], fill=alpha_color(accent, 200))
    img_rgba = Image.alpha_composite(img_rgba, bar_overlay)

    return img_rgba.convert("RGB")


# ── Main Render ─────────────────────────────────────────────────────────────
def render_scene(scene_path, audio_path, output_path, fps=FPS):
    with open(scene_path) as f:
        scene = json.load(f)

    with wave.open(audio_path, "rb") as wf:
        audio_duration = wf.getnframes() / wf.getframerate()

    total_frames = int(audio_duration * fps)
    accent_rgb = hex_rgb(scene.get("accent", "#e94560"))
    gradient_colors = [hex_rgb(c) for c in scene.get("gradient", ["#1a1a2e", "#16213e", "#0f3460"])]

    segments = scene.get("segments", [])
    seg_starts = []
    t = 0.0
    for seg in segments:
        seg_starts.append(t)
        t += seg.get("duration_s", 5.0)
    total_seg_duration = t
    time_scale = audio_duration / total_seg_duration if total_seg_duration > 0 else 1.0

    fonts = get_fonts()

    # Pre-compute
    print("  Pre-computing assets...", end=" ", flush=True)
    t0 = time.time()
    bg_rgb = make_gradient(W, H, gradient_colors)
    vignette = make_vignette(W, H, strength=0.5)
    particles = precompute_particles(PARTICLE_COUNT, W, H, seed=scene.get("scene_num", 0) * 137)
    wrapped = prewrap_text(segments, fonts["body"], TEXT_PANEL_W)
    scene_num = scene.get("scene_num", 1)
    total_scenes = scene.get("total_scenes", 28)
    print(f"{time.time() - t0:.1f}s")

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    print(f"Rendering scene {scene_num}: {total_frames} frames, {audio_duration:.1f}s")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t_start = time.time()

    for frame_idx in range(total_frames):
        t_sec = frame_idx / fps * time_scale

        seg_idx = len(segments) - 1
        for i, start in enumerate(seg_starts):
            if t_sec < (start + segments[i].get("duration_s", 5.0)) * time_scale:
                seg_idx = i
                break

        seg_elapsed = t_sec - seg_starts[seg_idx] * time_scale
        seg_dur = segments[seg_idx].get("duration_s", 5.0) * time_scale
        seg_progress = seg_elapsed / max(seg_dur, 0.001)

        img = render_frame(
            frame_idx, total_frames, scene,
            seg_idx, seg_progress,
            fonts, accent_rgb, gradient_colors,
            bg_rgb, vignette, particles, wrapped,
            scene_num, total_scenes,
        )
        proc.stdin.write(img.tobytes())

        if frame_idx > 0 and frame_idx % 100 == 0:
            elapsed = time.time() - t_start
            fps_now = frame_idx / elapsed
            eta = (total_frames - frame_idx) / max(fps_now, 0.1)
            print(f"  Frame {frame_idx}/{total_frames} ({fps_now:.1f} fps, ETA {eta:.0f}s)")

    proc.stdin.close()
    proc.wait()
    err = proc.stderr.read()
    elapsed = time.time() - t_start

    if proc.returncode != 0:
        print(f"ffmpeg error: {err.decode()[-500:]}", file=sys.stderr)
        sys.exit(1)

    size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({size / 1_048_576:.1f} MB, {elapsed:.1f}s)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-json", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--fps", type=int, default=FPS)
    args = parser.parse_args()
    render_scene(args.scene_json, args.audio, args.output, args.fps)


if __name__ == "__main__":
    main()
