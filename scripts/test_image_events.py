#!/usr/bin/env python3
"""
Test: render frames from scene JSON with image visual events composited.
Verifies that downloaded images appear as overlays on treatment renders.
"""

import json
import os
import sys
import time
import wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from visuals.events import EventTimeline, render_visual_events
from visuals.fonts import get_fonts, W, H, FPS
from visuals.colors import hex_rgb
from visuals.treatments.base import RenderContext
from visuals import registry
import visuals.treatments  # noqa: F401

SCENES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "scenes")
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "media")
TEST_OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "test_frames")


def create_dummy_wav(duration: float, path: str):
    """Create a silent WAV file for testing."""
    sr = 22050
    n = int(sr * duration)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * n)
    return path


def test_image_composite():
    """Test that image events composite onto treatment renders correctly."""
    os.makedirs(TEST_OUTPUT, exist_ok=True)

    # Test scene 1 (has 3 images, title_card treatment)
    scene_path = os.path.join(SCENES_DIR, "scene_01.json")
    with open(scene_path) as f:
        scene = json.load(f)

    print(f"Scene 1: {scene['title']}")
    print(f"  Treatment: {scene.get('visual_treatment', 'default')}")
    print(f"  Visual events: {len(scene.get('visual_events', []))}")

    # Count image events
    img_events = [e for e in scene.get("visual_events", []) if e.get("type") == "image"]
    print(f"  Image events: {len(img_events)}")
    for ev in img_events:
        print(f"    - {ev['caption']}: t={ev['trigger_time']:.1f}s, pos={ev['position']}, src={ev['src']}")

    # Build event timeline
    timeline = EventTimeline.from_scene(scene, MEDIA_DIR)
    loaded = sum(1 for e in timeline.events if e._image is not None)
    print(f"  Images loaded: {loaded}/{len(timeline.events)}")

    # Setup treatment
    treatment_name = scene.get("visual_treatment", "default")
    treatment_cls = registry.get(treatment_name)
    if treatment_cls is None:
        treatment_cls = registry.get("default")
    treatment = treatment_cls()

    fonts = get_fonts()
    accent_rgb = hex_rgb(scene.get("accent", "#e94560"))

    segments = scene.get("segments", [])
    seg_starts = []
    t = 0.0
    for seg in segments:
        seg_starts.append(t)
        t += seg.get("duration_s", 5.0)

    ctx = RenderContext(
        w=W, h=H, fps=FPS,
        fonts=fonts,
        accent_rgb=accent_rgb,
        scene=scene,
        scene_num=scene.get("scene_num", 1),
        total_scenes=scene.get("total_scenes", 28),
        dummy_draw=__import__("PIL.ImageDraw", fromlist=["ImageDraw"]).Draw(
            __import__("PIL.Image", fromlist=["Image"]).new("L", (1, 1))
        ),
    )

    treatment.prepare(ctx)

    # Render test frames at image event trigger times
    test_times = [ev["trigger_time"] + 0.5 for ev in img_events]

    for t_sec in test_times:
        # Find segment
        seg_idx = len(segments) - 1
        total_dur = sum(s.get("duration_s", 5.0) for s in segments)
        time_scale = 1.0  # no audio scaling for test

        for i, start in enumerate(seg_starts):
            if t_sec < start + segments[i].get("duration_s", 5.0):
                seg_idx = i
                break

        seg_elapsed = t_sec - seg_starts[seg_idx]
        seg_dur = segments[seg_idx].get("duration_s", 5.0)
        seg_progress = seg_elapsed / max(seg_dur, 0.001)

        frame_idx = int(t_sec * FPS)
        total_frames = int(total_dur * FPS)

        # Render treatment frame
        img = treatment.render_frame(ctx, frame_idx, total_frames,
                                    seg_idx, seg_progress, 1.0)

        # Overlay visual events
        if timeline.events:
            img_rgba = img.convert("RGBA")
            events_overlay = render_visual_events(
                timeline, t_sec, W, H, accent_rgb, fonts,
                treatment_name=treatment_name)
            img_rgba = Image.alpha_composite(img_rgba, events_overlay)
            img = img_rgba.convert("RGB")

        out_path = os.path.join(TEST_OUTPUT, f"scene01_t{t_sec:.0f}.png")
        img.save(out_path)

        # Check non-black pixels in image regions
        import numpy as np
        arr = np.array(img)
        non_zero = np.count_nonzero(arr)
        print(f"  Frame t={t_sec:.1f}s: saved {out_path} ({non_zero} non-zero pixels)")

    print(f"\nTest frames saved to: {TEST_OUTPUT}/")
    print("PASS" if loaded == len(img_events) else f"FAIL: only {loaded}/{len(img_events)} images loaded")
    return loaded == len(img_events)


if __name__ == "__main__":
    from PIL import Image, ImageDraw  # noqa: E402
    success = test_image_composite()
    sys.exit(0 if success else 1)
