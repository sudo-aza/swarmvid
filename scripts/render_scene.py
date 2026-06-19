#!/usr/bin/env python3
"""
render_scene.py — Render a single scene's frames and pipe to ffmpeg.

Usage:
    python3 render_scene.py --scene-json scene.json --audio audio.wav --output scene_N.mp4

Scene JSON format:
{
  "scene_num": 1,
  "title": "Vor der Stadt",
  "subtitle": "Siedlung an der Leine",
  "era": "pre-1100",
  "segments": [
    {"text": "Narration text here...", "duration_s": 12.5},
    ...
  ],
  "sources": ["Source citation 1", "Source citation 2"],
  "gradient": ["#1a1a2e", "#16213e", "#0f3460"],
  "accent": "#e94560"
}

Output: H.264 MP4 at 1280x720, matching audio duration.
"""

import argparse
import json
import math
import os
import subprocess
import sys
import wave

from PIL import Image, ImageDraw, ImageFont


# ── Constants ──────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS = 24
BG_PARTICLES = 40  # floating particle count


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def make_gradient(draw, colors, w, h):
    """Vertical gradient with N color stops."""
    n = len(colors)
    for y in range(h):
        t = y / max(h - 1, 1) * (n - 1)
        idx = min(int(t), n - 2)
        frac = t - idx
        c = lerp_color(colors[idx], colors[idx + 1], frac)
        draw.line([(0, y), (w, y)], fill=c)


def draw_particles(overlay, bg_pixels, frame_idx, w, h, count=BG_PARTICLES, seed=42):
    """Floating particles for ambient animation.

    Draws onto an RGBA overlay with proper alpha, then returns the overlay
    so it can be alpha_composite'd onto the base image.
    bg_pixels is a list of (x, y, rgb) tuples from the gradient for blending.
    """
    import random
    rng = random.Random(seed)
    od = ImageDraw.Draw(overlay)
    for _ in range(count):
        px = rng.randint(0, w - 1)
        py_base = rng.randint(0, h - 1)
        speed = rng.uniform(0.2, 1.0)
        size = rng.randint(1, 3)
        alpha_base = rng.randint(40, 120)
        # Move upward slowly
        py = (py_base - frame_idx * speed * 2) % h
        alpha = int(alpha_base * (0.5 + 0.5 * math.sin(frame_idx * 0.05 + px * 0.01)))
        # Blend particle color with background at alpha
        # Background pixel approximate: sample gradient
        bg_rgb = bg_pixels[int(py) % h]
        # White particle blended over bg
        r = int(bg_rgb[0] * (1 - alpha / 255) + 255 * (alpha / 255))
        g = int(bg_rgb[1] * (1 - alpha / 255) + 255 * (alpha / 255))
        b = int(bg_rgb[2] * (1 - alpha / 255) + 255 * (alpha / 255))
        od.ellipse([px - size, py - size, px + size, py + size], fill=(r, g, b, 255))


def build_bg_pixel_row(gradient_colors, h):
    """Pre-compute one row of gradient RGB values for particle blending."""
    n = len(gradient_colors)
    pixels = []
    for y in range(h):
        t = y / max(h - 1, 1) * (n - 1)
        idx = min(int(t), n - 2)
        frac = t - idx
        pixels.append(lerp_color(gradient_colors[idx], gradient_colors[idx + 1], frac))
    return pixels


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


def render_frame(frame_idx, total_frames, scene, seg_idx, seg_text, seg_progress,
                fonts, accent_rgb, gradient_colors, bg_pixels):
    """Render one frame. Returns an RGB PIL Image.

    All semi-transparent elements are drawn onto RGBA overlay images
    and composited via Image.alpha_composite() before final RGB conversion.
    """
    # Base: RGBA with gradient
    img = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(img)
    make_gradient(draw, gradient_colors, W, H)

    # ── Particles (overlay with pre-blended colors) ──
    particle_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_particles(particle_overlay, bg_pixels, frame_idx, W, H, seed=scene.get("scene_num", 0) * 100)
    img = Image.alpha_composite(img, particle_overlay)

    # ── Top bar (overlay) ──
    header_font, title_font, body_font, source_font = fonts
    bar_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar_overlay)
    bd.rectangle([(0, 0), (W, 60)], fill=(0, 0, 0, 100))
    bd.text((30, 12), f"Szene {scene['scene_num']}", fill=(*accent_rgb, 255), font=header_font)
    bd.text((W - 30, 12), scene.get("era", ""), fill=(200, 200, 200, 200), font=header_font, anchor="rt")
    img = Image.alpha_composite(img, bar_overlay)

    # ── Title card (fade in during first segment) ──
    if seg_idx == 0 and seg_progress < 0.15:
        title_alpha = int(255 * min(1.0, seg_progress / 0.05)) if seg_progress < 0.10 else int(255 * max(0, (0.15 - seg_progress) / 0.05))
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        title = scene.get("title", "")
        subtitle = scene.get("subtitle", "")
        ty = 200
        od.text((W // 2, ty), title, fill=(*accent_rgb, title_alpha), font=title_font, anchor="mt")
        if subtitle:
            od.text((W // 2, ty + 60), subtitle, fill=(200, 200, 200, title_alpha), font=body_font, anchor="mt")
        line_w = 200
        od.line([(W // 2 - line_w // 2, ty + 110), (W // 2 + line_w // 2, ty + 110)], fill=(*accent_rgb, title_alpha), width=2)
        img = Image.alpha_composite(img, overlay)

    # ── Narration text (centered, with subtle animation) ──
    if seg_text:
        text_area_x = 100
        text_area_w = W - 200
        text_area_y = 300
        text_area_h = 280

        # Text box overlay (semi-transparent)
        text_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(text_overlay)
        td.rounded_rectangle(
            [(text_area_x - 20, text_area_y - 20), (text_area_x + text_area_w + 20, text_area_y + text_area_h + 20)],
            radius=15, fill=(0, 0, 0, 80)
        )

        # Text with fade-in — use pre-blended colors on the overlay
        lines = wrap_text(td, seg_text, body_font, text_area_w - 40)
        max_lines = 8
        if len(lines) > max_lines:
            scroll_offset = seg_progress * (len(lines) - max_lines)
            visible_start = int(scroll_offset)
            visible_lines = lines[visible_start:visible_start + max_lines]
        else:
            visible_lines = lines

        # Text is drawn with alpha on the overlay — alpha_composite handles the blend
        line_alpha = min(255, int(seg_progress * 600))
        for i, line in enumerate(visible_lines):
            y = text_area_y + i * 36
            td.text((text_area_x, y), line, fill=(240, 240, 240, line_alpha), font=body_font)

        img = Image.alpha_composite(img, text_overlay)

    # ── Progress bar (overlay) ──
    progress = frame_idx / max(total_frames - 1, 1)
    prog_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(prog_overlay)
    bar_y = H - 30
    bar_h = 4
    pd.rectangle([(0, bar_y), (W, bar_y + bar_h)], fill=(50, 50, 50, 150))
    pd.rectangle([(0, bar_y), (int(W * progress), bar_y + bar_h)], fill=(*accent_rgb, 255))
    img = Image.alpha_composite(img, prog_overlay)

    # ── Sources (bottom-right, small text) ──
    sources = scene.get("sources", [])
    if sources and seg_idx == len(scene["segments"]) - 1:
        src_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(src_overlay)
        src_text = " | ".join(sources[:2])
        sd.text((W - 30, H - 60), src_text, fill=(150, 150, 150, 180), font=source_font, anchor="rb")
        img = Image.alpha_composite(img, src_overlay)

    return img.convert("RGB")


def get_fonts():
    """Load fonts — try system fonts, fall back to default."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    base = None
    for p in font_paths:
        if os.path.exists(p):
            base = p
            break
    if base is None:
        base = None  # Use Pillow default

    header_font = ImageFont.truetype(base, 22) if base else ImageFont.load_default()
    title_font = ImageFont.truetype(base, 42) if base else ImageFont.load_default()
    body_font = ImageFont.truetype(base, 26) if base else ImageFont.load_default()
    source_font = ImageFont.truetype(base, 16) if base else ImageFont.load_default()
    return header_font, title_font, body_font, source_font


def render_scene(scene_path, audio_path, output_path, fps=FPS):
    """Render a scene: frames piped to ffmpeg with audio."""
    with open(scene_path) as f:
        scene = json.load(f)

    # Get audio duration
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

    # Scale to match audio duration
    time_scale = audio_duration / total_seg_duration if total_seg_duration > 0 else 1.0

    fonts = get_fonts()
    bg_pixels = build_bg_pixel_row(gradient_colors, H)

    # ffmpeg command: pipe raw RGB frames
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",  # stdin
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    print(f"Rendering scene {scene['scene_num']}: {total_frames} frames, {audio_duration:.1f}s")

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    for frame_idx in range(total_frames):
        t = frame_idx / fps * time_scale

        # Find current segment
        seg_idx = len(segments) - 1
        for i, start in enumerate(seg_starts):
            scaled_start = start * time_scale
            if t < scaled_start + segments[i].get("duration_s", 5.0) * time_scale:
                seg_idx = i
                break

        seg = segments[seg_idx]
        seg_progress = (t - seg_starts[seg_idx] * time_scale) / max(seg.get("duration_s", 5.0) * time_scale, 0.001)

        img = render_frame(
            frame_idx, total_frames, scene,
            seg_idx, seg.get("text", ""), seg_progress,
            fonts, accent_rgb, gradient_colors, bg_pixels,
        )
        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    stderr = proc.stderr.read()

    if proc.returncode != 0:
        print(f"ffmpeg error: {stderr.decode()[-500:]}", file=sys.stderr)
        sys.exit(1)

    file_size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({file_size / 1_048_576:.1f} MB)")


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
