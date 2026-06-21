#!/usr/bin/env python3
"""
render_scene_v2.py — Per-scene script renderer (v2).

Renders Pillow frames piped to ffmpeg for H.264 MP4 output at 1280x720.
Uses per-scene scripts from scripts/scenes/ instead of the treatment system.

Usage:
    python3 render_scene_v2.py --scene 1 --audio audio.wav --output scene_01.mp4
    python3 render_scene_v2.py --scene-json scene.json --audio audio.wav --output scene_01.mp4
    python3 render_scene_v2.py --scene 1 --output scene_01.mp4  # no audio (silent)
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
import wave

# Add scripts/ to path so visuals package is importable
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

from PIL import Image

from visuals.colors import hex_rgb
from visuals.fonts import W, H, FPS
from visuals.renderlib import RenderLib


def load_scene_script(scene_num: int):
    """Import the per-scene script module."""
    module_name = f"scenes.scene_{scene_num:02d}"
    try:
        mod = importlib.import_module(module_name)
        return mod
    except ImportError as e:
        print(f"  ERROR: Cannot import {module_name}: {e}")
        print(f"  Ensure scripts/scenes/scene_{scene_num:02d}.py exists.")
        sys.exit(1)


def get_audio_duration(audio_path: str) -> float:
    """Get duration of a WAV file in seconds."""
    with wave.open(audio_path, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def render_scene(scene_num: int, audio_path: str | None, output_path: str,
                 fps: int = FPS) -> None:
    """Render a single scene to MP4 using the per-scene script."""
    # Locate scene JSON
    scenes_dir = os.path.join(SCRIPTS_DIR, "..", "output", "scenes")
    scenes_dir = os.path.abspath(scenes_dir)
    scene_path = os.path.join(scenes_dir, f"scene_{scene_num:02d}.json")

    if not os.path.isfile(scene_path):
        print(f"  ERROR: Scene JSON not found: {scene_path}")
        sys.exit(1)

    with open(scene_path) as f:
        scene = json.load(f)

    # Audio duration (or derive from segments if no audio)
    if audio_path and os.path.isfile(audio_path):
        audio_duration = get_audio_duration(audio_path)
        use_audio = True
    else:
        # Derive duration from segments
        total_seg_dur = sum(s.get("duration_s", 12.0) for s in scene.get("segments", []))
        audio_duration = total_seg_dur
        use_audio = False

    total_frames = int(audio_duration * fps)
    accent_hex = scene.get("accent", "#e94560")
    accent_rgb = hex_rgb(accent_hex)

    # Media base path
    media_base = os.path.join(os.path.dirname(scenes_dir), "media")

    # Load scene script
    mod = load_scene_script(scene_num)
    print(f"  Scene script: scenes/scene_{scene_num:02d}.py")

    # Create RenderLib instance
    rl = RenderLib(
        w=W, h=H, fps=fps,
        scene_data=scene,
        accent=accent_rgb,
        media_base=media_base,
    )

    # Prepare scene
    print("  Preparing scene...", end=" ", flush=True)
    t0 = time.time()
    state = mod.prepare(rl)
    print(f"{time.time() - t0:.1f}s")

    # Build ffmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
    ]
    if use_audio:
        cmd += ["-i", audio_path]

    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-profile:v", "main", "-pix_fmt", "yuv420p",
    ]
    if use_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k"]

    cmd += [
        "-movflags", "+faststart",
    ]
    if use_audio:
        cmd += ["-shortest"]

    cmd += [output_path]

    print(f"Rendering scene {scene_num}: {total_frames} frames, {audio_duration:.1f}s")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    t_start = time.time()

    for frame_idx in range(total_frames):
        try:
            img = mod.render(rl, frame_idx, total_frames, state)
        except Exception as e:
            print(f"\n  ERROR at frame {frame_idx}: {e}")
            # Fill with black and continue
            img = Image.new("RGB", (W, H), (10, 10, 15))

        proc.stdin.write(img.tobytes())

        if frame_idx > 0 and frame_idx % 100 == 0:
            elapsed = time.time() - t_start
            fps_now = frame_idx / elapsed
            eta = (total_frames - frame_idx) / max(fps_now, 0.1)
            pct = frame_idx / total_frames * 100
            print(f"  Frame {frame_idx}/{total_frames} ({pct:.0f}%, {fps_now:.1f} fps, ETA {eta:.0f}s)")

    proc.stdin.close()
    proc.wait()
    err = proc.stderr.read()
    elapsed = time.time() - t_start

    if proc.returncode != 0:
        print(f"ffmpeg error: {err.decode()[-500:]}", file=sys.stderr)
        sys.exit(1)

    size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({size / 1_048_576:.1f} MB, {elapsed:.1f}s, {total_frames / elapsed:.1f} avg fps)")


def main():
    parser = argparse.ArgumentParser(description="Render scene v2 (per-scene scripts)")
    parser.add_argument("--scene", type=int, required=False,
                        help="Scene number (1-28)")
    parser.add_argument("--scene-json", type=str, required=False,
                        help="Path to scene JSON (alternative to --scene)")
    parser.add_argument("--audio", type=str, default=None,
                        help="WAV audio file (optional — silent if omitted)")
    parser.add_argument("--output", required=True, help="Output MP4 path")
    parser.add_argument("--fps", type=int, default=FPS)
    args = parser.parse_args()

    if args.scene_json:
        # Derive scene number from filename
        import re
        m = re.search(r"scene[_-]?(\d+)", os.path.basename(args.scene_json))
        scene_num = int(m.group(1)) if m else 1
    elif args.scene:
        scene_num = args.scene
    else:
        print("ERROR: Provide --scene N or --scene-json path")
        sys.exit(1)

    render_scene(scene_num, args.audio, args.output, args.fps)


if __name__ == "__main__":
    main()
