#!/usr/bin/env python3
"""
render_scene.py — Professional documentary scene renderer.

Renders Pillow frames piped to ffmpeg for H.264 MP4 output at 1280x720.

Features:
  - Cinematic title cards with fade-in/out (ZDF/ARD documentary style)
  - Proper narration text: centered, word-wrapped, dark panel backdrop
  - Per-segment cross-dissolve transitions (0.5s)
  - Floating ambient particles
  - Thin progress bar at bottom edge

Usage:
    python3 render_scene.py --scene-json scene.json --audio audio.wav --output scene_N.mp4

Scene JSON format (unchanged):
{
  "scene_num": 1,
  "title": "Vor der Stadt",
  "subtitle": "Siedlung an der Leine",
  "era": "pre-1100",
  "segments": [
    {"text": "Narration text...", "duration_s": 12.5},
    ...
  ],
  "sources": ["Source 1"],
  "gradient": ["#1a1a2e", "#16213e", "#0f3460"],
  "accent": "#e94560"
}
"""

import argparse
import json
import math
import os
import random
import subprocess
import sys
import wave

from PIL import Image, ImageDraw, ImageFont

# ── Constants ──────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 24
PARTICLE_COUNT = 50
TITLE_DURATION_FRAC = 0.08   # fraction of first segment for title card display
TITLE_FADE_FRAC = 0.025      # fraction for fade in/out of title
SEGMENT_FADE_FRAC = 0.02     # fraction of segment duration for cross-dissolve
MAX_TEXT_LINES = 7
TEXT_LINE_HEIGHT = 38
TEXT_AREA_TOP = 260
TEXT_PANEL_MARGIN = 40
TEXT_PANEL_RADIUS = 12
PROGRESS_BAR_H = 3

# Layout zones
TEXT_AREA_LEFT = TEXT_PANEL_MARGIN + 20
TEXT_AREA_WIDTH = W - 2 * (TEXT_PANEL_MARGIN + 20)
TEXT_AREA_HEIGHT = MAX_TEXT_LINES * TEXT_LINE_HEIGHT + 20


# ── Font Loading ──────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _load_font(path, size):
    key = (path, size)
    if key not in _FONT_CACHE:
        try:
            _FONT_CACHE[key] = ImageFont.truetype(path, size)
        except Exception:
            _FONT_CACHE[key] = ImageFont.load_default()
    return _FONT_CACHE[key]


def get_fonts():
    """Return dict of named fonts. Tries DejaVu Sans, falls back to Liberation, then default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    serif_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ]

    base = None
    bold = None
    serif = None
    for p in candidates:
        if os.path.exists(p):
            base = p
            break
    for p in bold_candidates:
        if os.path.exists(p):
            bold = p
            break
    for p in serif_candidates:
        if os.path.exists(p):
            serif = p
            break

    return {
        "title":       _load_font(serif or base, 48),
        "subtitle":    _load_font(base, 28),
        "body":        _load_font(base, 26),
        "body_bold":   _load_font(bold or base, 26),
        "era":         _load_font(serif or base, 20),
        "source":      _load_font(base, 16),
    }


# ── Color Utilities ─────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ── Gradient ──────────────────────────────────────────────────────────────────
def make_gradient_image(w, h, colors):
    """Create a vertical gradient RGB image (not per-line draw for speed)."""
    n = len(colors)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1) * (n - 1)
        idx = min(int(t), n - 2)
        frac = t - idx
        c = lerp_color(colors[idx], colors[idx + 1], frac)
        for x in range(w):
            px[x, y] = c
    return img


# ── Particles ─────────────────────────────────────────────────────────────────
def precompute_particles(count, w, h, seed):
    """Pre-compute particle base positions and properties. Returns list of dicts."""
    rng = random.Random(seed)
    particles = []
    for _ in range(count):
        particles.append({
            "x": rng.randint(0, w - 1),
            "y_base": rng.randint(0, h - 1),
            "speed": rng.uniform(0.3, 1.2),
            "size": rng.randint(1, 3),
            "alpha_base": rng.randint(50, 130),
            "phase": rng.uniform(0, 2 * math.pi),
        })
    return particles


def draw_particles_on_image(img, particles, bg_pixels, frame_idx, h):
    """Draw particles directly onto an RGBA image using pre-computed data."""
    od = ImageDraw.Draw(img)
    for p in particles:
        py = (p["y_base"] - frame_idx * p["speed"] * 1.5) % h
        alpha = int(p["alpha_base"] * (0.5 + 0.5 * math.sin(frame_idx * 0.04 + p["phase"])))
        bg = bg_pixels[int(py) % h]
        r = int(bg[0] * (1 - alpha / 255) + 255 * (alpha / 255))
        g = int(bg[1] * (1 - alpha / 255) + 255 * (alpha / 255))
        b = int(bg[2] * (1 - alpha / 255) + 255 * (alpha / 255))
        s = p["size"]
        x = p["x"]
        od.ellipse([x - s, py - s, x + s, py + s], fill=(r, g, b, 255))


def build_bg_pixel_row(gradient_colors, h):
    """Pre-compute gradient RGB per row for particle blending."""
    n = len(gradient_colors)
    pixels = []
    for y in range(h):
        t = y / max(h - 1, 1) * (n - 1)
        idx = min(int(t), n - 2)
        frac = t - idx
        pixels.append(lerp_color(gradient_colors[idx], gradient_colors[idx + 1], frac))
    return pixels


# ── Text Rendering ───────────────────────────────────────────────────────────
def wrap_text(draw, text, font, max_width):
    """Word-wrap text to fit within max_width. Returns list of lines."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def prewrap_all_segments(segments, font, max_width):
    """Pre-wrap all segment texts so we don't re-wrap every frame."""
    result = []
    for seg in segments:
        lines = wrap_text(ImageDraw.Draw(Image.new("L", (1, 1))), seg.get("text", ""), font, max_width)
        result.append(lines)
    return result


# ── Easing ────────────────────────────────────────────────────────────────────
def ease_in_out(t):
    """Smooth ease in/out (cosine)."""
    return 0.5 * (1 - math.cos(math.pi * max(0, min(1, t))))


# ── Frame Rendering ──────────────────────────────────────────────────────────
def render_frame(frame_idx, total_frames, scene, seg_idx, seg_progress,
                 fonts, accent_rgb, gradient_rgb, bg_rgba, particles, bg_pixels,
                 wrapped_lines):
    """Render one frame. Returns RGB PIL Image."""

    segments = scene.get("segments", [])
    num_segments = len(segments)
    seg_duration_frac = segments[seg_idx].get("duration_s", 5.0)

    # ── Cross-segment dissolve alpha (fade between segments) ──
    # During the last SEGMENT_FADE_FRAC of current segment AND first SEGMENT_FADE_FRAC
    # of next, compute a dissolve. For the last segment, only fade out.
    cross_alpha = 1.0  # 1.0 = fully current segment, 0.0 = transitioning away
    if seg_progress > (1.0 - SEGMENT_FADE_FRAC) and seg_idx < num_segments - 1:
        cross_alpha = (1.0 - seg_progress) / SEGMENT_FADE_FRAC
        cross_alpha = max(0, min(1, cross_alpha))
    elif seg_progress < SEGMENT_FADE_FRAC:
        cross_alpha = seg_progress / SEGMENT_FADE_FRAC
        cross_alpha = max(0, min(1, cross_alpha))

    # Start with cached gradient background (RGBA)
    img = bg_rgba.copy()
    draw = ImageDraw.Draw(img)

    # ── Particles ──
    draw_particles_on_image(img, particles, bg_pixels, frame_idx, H)

    # ── Title Card ──
    title = scene.get("title", "")
    subtitle = scene.get("subtitle", "")
    era_text = scene.get("era", "")

    # Title card shows during first segment
    if seg_idx == 0:
        # Compute title alpha: fade in, hold, fade out
        if seg_progress < TITLE_FADE_FRAC:
            title_alpha = ease_in_out(seg_progress / TITLE_FADE_FRAC)
        elif seg_progress > TITLE_DURATION_FRAC - TITLE_FADE_FRAC:
            title_alpha = ease_in_out((TITLE_DURATION_FRAC - seg_progress) / TITLE_FADE_FRAC)
        else:
            title_alpha = 1.0

        if title_alpha > 0.01:
            # Dark overlay behind title card area
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(overlay)

            # Semi-transparent dark band
            band_alpha = int(160 * title_alpha)
            od.rectangle([(0, 140), (W, 440)], fill=(0, 0, 0, band_alpha))

            # Era label (small, above title)
            if era_text:
                era_bbox = od.textbbox((0, 0), era_text, font=fonts["era"])
                era_w = era_bbox[2] - era_bbox[0]
                od.text((W // 2 - era_w // 2, 165), era_text,
                        fill=(180, 180, 180, int(200 * title_alpha)), font=fonts["era"])

            # Title (large, centered)
            title_bbox = od.textbbox((0, 0), title, font=fonts["title"])
            title_w = title_bbox[2] - title_bbox[0]
            od.text((W // 2 - title_w // 2, 210), title,
                    fill=(*accent_rgb, int(255 * title_alpha)), font=fonts["title"])

            # Accent line below title
            line_w = min(300, title_w + 80)
            line_y = 275
            line_alpha = int(220 * title_alpha)
            od.line([(W // 2 - line_w // 2, line_y), (W // 2 + line_w // 2, line_y)],
                    fill=(*accent_rgb, line_alpha), width=2)

            # Subtitle
            if subtitle:
                sub_bbox = od.textbbox((0, 0), subtitle, font=fonts["subtitle"])
                sub_w = sub_bbox[2] - sub_bbox[0]
                od.text((W // 2 - sub_w // 2, 295), subtitle,
                        fill=(220, 220, 220, int(230 * title_alpha)), font=fonts["subtitle"])

            img = Image.alpha_composite(img, overlay)

    # ── Narration Text Panel ──
    current_text = segments[seg_idx].get("text", "")
    if current_text and title_alpha_if_first(seg_idx, seg_progress) > 0.3:
        lines = wrapped_lines[seg_idx]

        # Compute which lines are visible (scroll)
        if len(lines) > MAX_TEXT_LINES:
            scroll_offset = seg_progress * (len(lines) - MAX_TEXT_LINES)
            vis_start = int(scroll_offset)
            visible = lines[vis_start:vis_start + MAX_TEXT_LINES]
            # Partial scroll blend
            sub_offset = scroll_offset - vis_start
        else:
            visible = lines
            sub_offset = 0

        if visible:
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            td = ImageDraw.Draw(overlay)

            # Dark panel backdrop
            panel_top = TEXT_AREA_TOP - 15
            panel_bottom = TEXT_AREA_TOP + len(visible) * TEXT_LINE_HEIGHT + 15
            td.rounded_rectangle(
                [(TEXT_PANEL_MARGIN, panel_top),
                 (W - TEXT_PANEL_MARGIN, panel_bottom)],
                radius=TEXT_PANEL_RADIUS, fill=(0, 0, 0, 120)
            )

            # Draw each visible line, centered horizontally
            text_alpha = int(255 * min(1.0, cross_alpha))
            for i, line in enumerate(visible):
                line_bbox = td.textbbox((0, 0), line, font=fonts["body"])
                lw = line_bbox[2] - line_bbox[0]
                x = W // 2 - lw // 2
                y = TEXT_AREA_TOP + i * TEXT_LINE_HEIGHT

                # Fade first/last lines during scroll
                line_alpha = text_alpha
                if i == 0 and sub_offset > 0:
                    line_alpha = int(text_alpha * (1.0 - sub_offset))
                if i == len(visible) - 1 and len(lines) > MAX_TEXT_LINES:
                    remaining = scroll_offset - int(scroll_offset)
                    if remaining > 0:
                        line_alpha = int(text_alpha * min(1.0, remaining))

                line_alpha = max(0, min(255, line_alpha))
                td.text((x, y), line, fill=(240, 240, 240, line_alpha), font=fonts["body"])

            img = Image.alpha_composite(img, overlay)

    # ── Progress bar (thin, at very bottom) ──
    progress = frame_idx / max(total_frames - 1, 1)
    prog_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(prog_overlay)
    bar_y = H - PROGRESS_BAR_H
    pd.rectangle([(0, bar_y), (W, bar_y + PROGRESS_BAR_H)], fill=(40, 40, 40, 120))
    pd.rectangle([(0, bar_y), (int(W * progress), bar_y + PROGRESS_BAR_H)], fill=(*accent_rgb, 200))
    img = Image.alpha_composite(img, prog_overlay)

    return img.convert("RGB")


def title_alpha_if_first(seg_idx, seg_progress):
    """Return title alpha if we're in the title card segment, else 1.0."""
    if seg_idx != 0:
        return 1.0
    if seg_progress < TITLE_FADE_FRAC:
        return ease_in_out(seg_progress / TITLE_FADE_FRAC)
    elif seg_progress > TITLE_DURATION_FRAC - TITLE_FADE_FRAC:
        return ease_in_out((TITLE_DURATION_FRAC - seg_progress) / TITLE_FADE_FRAC)
    return 1.0


# ── Main Render Loop ──────────────────────────────────────────────────────────
def render_scene(scene_path, audio_path, output_path, fps=FPS):
    """Render a scene: frames piped to ffmpeg with audio."""
    with open(scene_path) as f:
        scene = json.load(f)

    # Audio duration
    with wave.open(audio_path, "rb") as wf:
        audio_frames = wf.getnframes()
        audio_rate = wf.getframerate()
        audio_duration = audio_frames / audio_rate

    total_frames = int(audio_duration * fps)
    accent_rgb = hex_to_rgb(scene.get("accent", "#e94560"))
    gradient_colors = [hex_to_rgb(c) for c in scene.get("gradient", ["#1a1a2e", "#16213e", "#0f3460"])]

    # Build segment timeline
    segments = scene.get("segments", [])
    seg_starts = []
    t = 0.0
    for seg in segments:
        seg_starts.append(t)
        t += seg.get("duration_s", 5.0)
    total_seg_duration = t
    time_scale = audio_duration / total_seg_duration if total_seg_duration > 0 else 1.0

    # Fonts
    fonts = get_fonts()

    # Pre-compute: gradient background (RGBA), particles, text wraps, bg pixel row
    gradient_rgb = make_gradient_image(W, H, gradient_colors)
    bg_rgba = gradient_rgb.convert("RGBA")
    bg_pixels = build_bg_pixel_row(gradient_colors, H)
    particles = precompute_particles(PARTICLE_COUNT, W, H, seed=scene.get("scene_num", 0) * 137)
    wrapped_lines = prewrap_all_segments(segments, fonts["body"], TEXT_AREA_WIDTH)

    # ffmpeg pipe
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

    print(f"Rendering scene {scene['scene_num']}: {total_frames} frames, {audio_duration:.1f}s")

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    import time
    t_start = time.time()

    for frame_idx in range(total_frames):
        t_sec = frame_idx / fps * time_scale

        # Find current segment
        seg_idx = len(segments) - 1
        for i, start in enumerate(seg_starts):
            scaled_start = start * time_scale
            if t_sec < scaled_start + segments[i].get("duration_s", 5.0) * time_scale:
                seg_idx = i
                break

        seg = segments[seg_idx]
        seg_elapsed = t_sec - seg_starts[seg_idx] * time_scale
        seg_dur = seg.get("duration_s", 5.0) * time_scale
        seg_progress = seg_elapsed / max(seg_dur, 0.001)

        img = render_frame(
            frame_idx, total_frames, scene,
            seg_idx, seg_progress,
            fonts, accent_rgb, gradient_colors, bg_rgba,
            particles, bg_pixels, wrapped_lines,
        )
        proc.stdin.write(img.tobytes())

        # Progress reporting every 100 frames
        if frame_idx > 0 and frame_idx % 100 == 0:
            elapsed = time.time() - t_start
            fps_actual = frame_idx / elapsed
            eta = (total_frames - frame_idx) / max(fps_actual, 0.1)
            print(f"  Frame {frame_idx}/{total_frames} ({fps_actual:.1f} fps, ETA {eta:.0f}s)")

    proc.stdin.close()
    proc.wait()
    stderr_out = proc.stderr.read()

    elapsed_total = time.time() - t_start

    if proc.returncode != 0:
        print(f"ffmpeg error: {stderr_out.decode()[-500:]}", file=sys.stderr)
        sys.exit(1)

    file_size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({file_size / 1_048_576:.1f} MB, {elapsed_total:.1f}s render)")


def main():
    parser = argparse.ArgumentParser(description="Render a scene to MP4")
    parser.add_argument("--scene-json", required=True, help="Path to scene JSON")
    parser.add_argument("--audio", required=True, help="Path to WAV audio file")
    parser.add_argument("--output", required=True, help="Output MP4 path")
    parser.add_argument("--fps", type=int, default=FPS)
    args = parser.parse_args()
    render_scene(args.scene_json, args.audio, args.output, args.fps)


if __name__ == "__main__":
    main()
