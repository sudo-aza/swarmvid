#!/usr/bin/env python3
"""
render_scene.py — Documentary motion graphics renderer.

Renders Pillow frames piped to ffmpeg for H.264 MP4 output at 1280x720.

Uses a treatment system: each scene picks a visual treatment (default, title_card,
map_focus, fullscreen_text, stark) from the scene JSON's "visual_treatment" field.
Treatments are defined in visuals/treatments/ and share a common library.

Usage:
    python3 render_scene.py --scene-json scene.json --audio audio.wav --output scene_N.mp4
"""

import argparse
import json
import os
import subprocess
import sys
import time
import wave

# Add scripts/ to path so visuals package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw

from visuals import registry
from visuals.treatments.base import RenderContext
from visuals.colors import hex_rgb
from visuals.events import EventTimeline, render_visual_events
from visuals.fonts import get_fonts, W, H, FPS

# Trigger treatment registration
import visuals.treatments  # noqa: F401


def render_scene(scene_path: str, audio_path: str, output_path: str, fps: int = FPS) -> None:
    """Render a single scene to MP4 using the appropriate visual treatment."""
    with open(scene_path) as f:
        scene = json.load(f)

    with wave.open(audio_path, "rb") as wf:
        audio_duration = wf.getnframes() / wf.getframerate()

    total_frames = int(audio_duration * fps)
    scene_num = scene.get("scene_num", 1)
    total_scenes = scene.get("total_scenes", 28)
    accent_rgb = hex_rgb(scene.get("accent", "#e94560"))

    # Select treatment
    treatment_name = scene.get("visual_treatment", "default")
    treatment_cls = registry.get(treatment_name)
    if treatment_cls is None:
        print(f"  Warning: treatment '{treatment_name}' not found, using 'default'")
        treatment_cls = registry.get("default")

    treatment = treatment_cls()

    # Build render context
    fonts = get_fonts()
    segments = scene.get("segments", [])
    seg_starts = []
    t = 0.0
    for seg in segments:
        seg_starts.append(t)
        t += seg.get("duration_s", 5.0)
    total_seg_duration = t
    time_scale = audio_duration / total_seg_duration if total_seg_duration > 0 else 1.0

    ctx = RenderContext(
        w=W, h=H, fps=fps,
        fonts=fonts,
        accent_rgb=accent_rgb,
        scene=scene,
        scene_num=scene_num,
        total_scenes=total_scenes,
        dummy_draw=ImageDraw.Draw(Image.new("L", (1, 1))),
    )

    # Let treatment pre-compute assets
    print(f"  Treatment: {treatment_name} ({treatment_cls.description})")
    print("  Pre-computing assets...", end=" ", flush=True)
    t0 = time.time()
    treatment.prepare(ctx)
    print(f"{time.time() - t0:.1f}s")

    # Build visual events timeline (per-scene programming)
    media_base = os.path.join(os.path.dirname(scene_path), "media")
    event_timeline = EventTimeline.from_scene(scene, media_base)
    if event_timeline.events:
        print(f"  Visual events: {len(event_timeline.events)} events loaded")

    # FFmpeg pipe
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-profile:v", "main", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        output_path,
    ]

    print(f"Rendering scene {scene_num}: {total_frames} frames, {audio_duration:.1f}s")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t_start = time.time()

    for frame_idx in range(total_frames):
        t_sec = frame_idx / fps * time_scale

        # Determine segment
        seg_idx = len(segments) - 1
        for i, start in enumerate(seg_starts):
            if t_sec < (start + segments[i].get("duration_s", 5.0)) * time_scale:
                seg_idx = i
                break

        seg_elapsed = t_sec - seg_starts[seg_idx] * time_scale
        seg_dur = segments[seg_idx].get("duration_s", 5.0) * time_scale
        seg_progress = seg_elapsed / max(seg_dur, 0.001)

        # Cross-segment fade
        num_segs = len(segments)
        cross_fade_dur = 0.08
        if seg_progress > (1.0 - cross_fade_dur) and seg_idx < num_segs - 1:
            cross_fade = (1.0 - seg_progress) / cross_fade_dur
        elif seg_progress < cross_fade_dur and seg_idx > 0:
            cross_fade = seg_progress / cross_fade_dur
        else:
            cross_fade = 1.0
        cross_fade = max(0.0, min(1.0, cross_fade))

        # Render frame via treatment
        img = treatment.render_frame(ctx, frame_idx, total_frames,
                                   seg_idx, seg_progress, cross_fade)

        # Overlay visual events (per-scene programmed content)
        if event_timeline.events:
            img_rgba = img.convert("RGBA")
            events_overlay = render_visual_events(
                event_timeline, t_sec, W, H, accent_rgb, fonts)
            img_rgba = Image.alpha_composite(img_rgba, events_overlay)
            img = img_rgba.convert("RGB")

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
