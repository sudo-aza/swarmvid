#!/usr/bin/env python3
"""Test: render a narration frame and verify map is visible."""

import json
import sys
import os
import time
import wave

sys.path.insert(0, "/home/z/my-project/swarmvid/scripts")
from render_scene import (
    W, H, FPS, render_frame, hex_rgb, make_gradient, make_vignette,
    precompute_particles, prewrap_text, get_fonts, TEXT_TOP_MARGIN,
    TEXT_PANEL_W
)

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
        {"text": "Wahrend des 12. Jahrhunderts erlebte Hannover eine bedeutende Entwicklung unter den Staufern. Die Stadt wurde zu einem wichtigen Handelsplatz an der Leine.", "duration_s": 10.0},
        {"text": "Die Beziehungen zu Hildesheim und Braunschweig pragten die politische Landschaft.", "duration_s": 10.0}
    ]
}

# Create dummy WAV
wav_path = "/tmp/test_audio.wav"
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
print("Pre-computing...", flush=True)
t0 = time.time()
bg_rgb = make_gradient(W, H, gradient_colors)
vignette = make_vignette(W, H, strength=0.5)
particles = precompute_particles(30, W, H, seed=scene["scene_num"] * 137)
wrapped = prewrap_text(scene["segments"], fonts["body"], TEXT_PANEL_W)
print(f"Pre-compute: {time.time() - t0:.1f}s")

# Render a narration frame (frame 120 = 5s into 20s audio)
frame_idx = 120
total_frames = int(duration * FPS)

seg_dur = scene["segments"][0]["duration_s"]
seg_progress = (frame_idx / FPS) / seg_dur
if seg_progress > 1.0:
    seg_progress = 0.99
seg_idx = 0

print(f"Rendering frame {frame_idx} (seg_progress={seg_progress:.2f})...")
img = render_frame(
    frame_idx, total_frames, scene,
    seg_idx, seg_progress,
    fonts, accent_rgb, gradient_colors,
    bg_rgb, vignette, particles, wrapped,
    scene["scene_num"], scene["total_scenes"]
)

out_path = "/home/z/my-project/download/test_frame_map_fix.png"
os.makedirs("/home/z/my-project/download", exist_ok=True)
img.save(out_path)
print(f"Saved: {out_path}")

# Check that left panel is NOT all-black (map should be visible)
# Sample some pixels in the left 520px
import numpy as np
arr = np.array(img)
left_panel = arr[:, :520, :]
left_mean = left_panel.mean()
print(f"Left panel mean pixel value: {left_mean:.1f}")
if left_mean > 5:
    print("PASS: Left panel has visible content (not all black)")
else:
    print("FAIL: Left panel is still all-black!")
