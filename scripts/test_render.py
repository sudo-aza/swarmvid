#!/usr/bin/env python3
"""Quick test: render a single frame from render_scene.py and save as PNG."""

import json
import sys
import os
import time
import wave

sys.path.insert(0, "/home/z/my-project/swarmvid/scripts")
from render_scene import (
    W, H, FPS, render_frame, hex_rgb, make_gradient, make_vignette,
    precompute_particles, prewrap_text, get_fonts, TEXT_TOP_MARGIN,
    TITLE_CARD_DURATION, TEXT_PANEL_W
)

# Create a minimal test scene JSON
scene = {
    "scene_num": 3,
    "total_scenes": 28,
    "title": "Die Staufenzeit in Hannover",
    "subtitle": "Macht und Glaube im Mittelalter",
    "era": "Mittelalter (1130-1250)",
    "gradient": ["#1a1a2e", "#16213e", "#0f3460"],
    "accent": "#e94560",
    "sources": [],
    "segments": [
        {
            "text": "Wahrend des 12. Jahrhunderts erlebte Hannover eine bedeutende Entwicklung unter den Staufern. Die Stadt wurde zu einem wichtigen Handelsplatz an der Leine und entwickelte sich rasch zu einem Zentrum der Region.",
            "duration_s": 10.0
        },
        {
            "text": "Die Beziehungen zu Hildesheim und Braunschweig pragten die politische Landschaft. Markgraf Heinrich der Lowe baute Braunschweig zu einer michtigen Residenz aus.",
            "duration_s": 10.0
        }
    ]
}

# Create a dummy WAV for audio duration
wav_path = "/tmp/test_audio.wav"
import struct
sample_rate = 22050
duration = 20.0
n_frames = int(sample_rate * duration)
with wave.open(wav_path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(b"\x00\x00" * n_frames)

accent_rgb = hex_rgb(scene["accent"])
gradient_colors = [hex_rgb(c) for c in scene["gradient"]]

fonts = get_fonts()
print("Pre-computing...")
t0 = time.time()
bg_rgb = make_gradient(W, H, gradient_colors)
vignette = make_vignette(W, H, strength=0.5)
particles = precompute_particles(30, W, H, seed=scene["scene_num"] * 137)
wrapped = prewrap_text(scene["segments"], fonts["body"], TEXT_PANEL_W)
print(f"Pre-compute: {time.time() - t0:.1f}s")

# Render a few frames and save
test_frames = [0, 30, 60, 120, 200]
for fi in test_frames:
    print(f"Rendering frame {fi}...")
    # Skip title card (frames 0-84 = first 3.5s at 24fps), test narration frame
    frame = 100  # deep into narration
    if fi > 0:
        frame = fi

    # Calculate segment
    total_dur = sum(s["duration_s"] for s in scene["segments"])
    audio_dur = duration
    time_scale = audio_dur / total_dur if total_dur > 0 else 1.0

    t_sec = frame / FPS * time_scale
    seg_starts = []
    t = 0.0
    for seg in scene["segments"]:
        seg_starts.append(t)
        t += seg["duration_s"]

    seg_idx = len(scene["segments"]) - 1
    for i, start in enumerate(seg_starts):
        if t_sec < (start + scene["segments"][i]["duration_s"]) * time_scale:
            seg_idx = i
            break

    seg_elapsed = t_sec - seg_starts[seg_idx] * time_scale
    seg_dur = scene["segments"][seg_idx]["duration_s"] * time_scale
    seg_progress = seg_elapsed / max(seg_dur, 0.001)

    print(f"  seg_idx={seg_idx}, progress={seg_progress:.2f}")

    img = render_frame(
        frame, int(audio_dur * FPS), scene,
        seg_idx, seg_progress,
        fonts, accent_rgb, gradient_colors,
        bg_rgb, vignette, particles, wrapped,
        scene["scene_num"], scene["total_scenes"]
    )

    out_path = f"/home/z/my-project/download/test_frame_{fi}.png"
    os.makedirs("/home/z/my-project/download", exist_ok=True)
    img.save(out_path)
    print(f"  Saved: {out_path}")

# Also render a title card frame
print("Rendering title card frame (frame 10)...")
frame = 10
total_dur = sum(s["duration_s"] for s in scene["segments"])
time_scale = audio_dur / total_dur if total_dur > 0 else 1.0
t_sec = frame / FPS * time_scale

seg_starts = [0.0]
t = 0.0
for seg in scene["segments"]:
    seg_starts.append(t)
    t += seg["duration_s"]
seg_starts = seg_starts[:-1]

seg_idx = 0
seg_elapsed = t_sec
seg_dur = scene["segments"][0]["duration_s"] * time_scale
seg_progress = seg_elapsed / max(seg_dur, 0.001)

img_title = render_frame(
    frame, int(audio_dur * FPS), scene,
    seg_idx, seg_progress,
    fonts, accent_rgb, gradient_colors,
    bg_rgb, vignette, particles, wrapped,
    scene["scene_num"], scene["total_scenes"]
)
title_path = "/home/z/my-project/download/test_title_card.png"
img_title.save(title_path)
print(f"Saved title card: {title_path}")

print("All test frames saved.")
