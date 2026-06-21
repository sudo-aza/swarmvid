#!/usr/bin/env python3
"""Smoke test for renderlib.py — renders a few test frames to verify API works."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image
from visuals.renderlib import RenderLib

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "output", "test_renderlib")


def test_smoke_frame():
    """Render a single frame using most renderlib primitives."""
    os.makedirs(OUTPUT, exist_ok=True)

    # Create a minimal scene dict
    scene = {
        "title": "Test Scene",
        "subtitle": "RenderLib Smoke Test",
        "era": "2026",
        "gradient": ["#0a0a1a", "#1a1a3e", "#0f3460"],
        "scene_num": 1,
        "total_scenes": 28,
        "segments": [
            {"text": "This is a test segment.", "duration_s": 12.0},
        ],
    }

    rl = RenderLib(scene_data=scene, accent=(233, 69, 96))
    state = rl.prepare()
    total_frames = 24 * 5  # 5 seconds

    # Render a few frames at key moments
    for fi in [0, 36, 72, 119]:  # frame indices at 0s, 1.5s, 3s, 5s
        t = rl.time(fi)
        progress = fi / max(total_frames - 1, 1)

        rl.begin_frame(fi, total_frames)

        # 1. Background gradient
        rl.gradient(state["gradient_colors"], direction="radial", vignette=0.5)

        # 2. Particles
        if fi == 0:
            rl.init_particles(15, seed=42, style="warm_glow")
        rl.draw_particles()

        # 3. Era label (top-left)
        rl.text(state["era"], 60, 40, font="era",
                color=rl._scale_alpha(rl.accent, 220))

        # 4. Title (center)
        rl.text(state["title"], rl.w // 2, rl.h // 2 - 60,
                font="title", color=(255, 255, 255, 255), anchor="mm")

        # 5. Animated accent line
        line_w = int(400 * rl.ease(progress, "out_cubic"))
        rl.line(rl.w // 2 - line_w, rl.h // 2 - 25,
                rl.w // 2 + line_w, rl.h // 2 - 25,
                color=rl._scale_alpha(rl.accent, 200), width=2)

        # 6. Subtitle
        sub_alpha = rl.alpha(1.0, progress, fade_in=0.3)
        rl.text(state["subtitle"], rl.w // 2, rl.h // 2 - 5,
                font="subtitle",
                color=rl._scale_alpha((200, 200, 200), sub_alpha),
                anchor="mt")

        # 7. Callout (bottom-left, faded in)
        call_alpha = rl.alpha(1.0, progress, fade_in=0.4)
        rl.callout("2026", "RenderLib v1.0",
                   position="bottom-left", style="highlight",
                   alpha_mult=call_alpha)

        # 8. Card (bottom-right, faded in)
        rl.card("API Test", body="text()  image()  gradient()\ncallout()  card()  particles()\nease()  pulse()  slide()",
                 position="bottom-right", style="default",
                 alpha_mult=call_alpha)

        # 9. Corner brackets (animated)
        bracket_len = int(80 * rl.ease(progress, "out_cubic"))
        if bracket_len > 0:
            bracket_a = rl._scale_alpha(rl.accent, rl.ease(progress, "out_cubic") * 220)
            rl.bracket(50, 50, bracket_len, bracket_a, corner="tl")
            rl.bracket(rl.w - 50, rl.h - 50, bracket_len, bracket_a, corner="br")

        # 10. Global overlays
        rl.progress_bar()
        rl.timeline_bar(1, 28)
        rl.scene_counter()

        # 11. Get frame
        frame = rl.frame()
        path = os.path.join(OUTPUT, f"smoke_frame_{fi:03d}.png")
        frame.save(path)
        print(f"  Frame {fi} (t={t:.1f}s, progress={progress:.2f}): {path}  [{frame.size[0]}x{frame.size[1]}]")

    print("  Smoke test PASSED — all primitives rendered without errors")
    return True


def test_time_helpers():
    """Test time/segment helpers."""
    rl = RenderLib(scene_data={
        "segments": [
            {"text": "seg0", "duration_s": 12.0},
            {"text": "seg1", "duration_s": 8.0},
            {"text": "seg2", "duration_s": 10.0},
        ]
    })

    # Test time()
    assert rl.time(0) == 0.0, "time(0) should be 0"
    assert rl.time(24) == 1.0, "time(24) at 24fps should be 1.0"

    # Test segment_at_time()
    seg, prog = rl.segment_at_time(0.0)
    assert seg == 0 and prog == 0.0, f"t=0 should be seg0/0.0, got seg{seg}/{prog}"

    seg, prog = rl.segment_at_time(6.0)
    assert seg == 0 and 0.4 <= prog <= 0.6, f"t=6 should be seg0/~0.5, got seg{seg}/{prog}"

    seg, prog = rl.segment_at_time(12.0)
    assert seg == 1 and prog == 0.0, f"t=12 should be seg1/0.0, got seg{seg}/{prog}"

    seg, prog = rl.segment_at_time(15.0)
    assert seg == 1 and 0.3 <= prog <= 0.4, f"t=15 should be seg1/~0.375, got seg{seg}/{prog}"

    seg, prog = rl.segment_at_time(20.0)
    assert seg == 2 and 0.0 <= prog <= 0.01, f"t=20 should be seg2/0.0, got seg{seg}/{prog}"

    seg, prog = rl.segment_at_time(30.0)
    assert seg == 2, f"t=30 should be seg2, got seg{seg}"

    # Test seg_time()
    assert rl.seg_time(0, 3.0) == 3.0, f"seg_time(0,3) should be 3.0, got {rl.seg_time(0, 3.0)}"
    assert rl.seg_time(1, 2.0) == 14.0, f"seg_time(1,2) should be 14.0, got {rl.seg_time(1, 2.0)}"
    assert rl.seg_time(2, 0.0) == 20.0, f"seg_time(2,0) should be 20.0, got {rl.seg_time(2, 0.0)}"

    print("  Time helpers test PASSED")
    return True


def test_easing():
    """Test easing functions."""
    from visuals.renderlib import ease_out_cubic, ease_in_out_cubic, ease_out_back

    assert ease_out_cubic(0.0) == 0.0
    assert abs(ease_out_cubic(1.0) - 1.0) < 0.001
    assert ease_out_cubic(0.5) > 0.5  # ease-out is above linear

    assert ease_in_out_cubic(0.0) == 0.0
    assert abs(ease_in_out_cubic(1.0) - 1.0) < 0.001
    assert ease_in_out_cubic(0.5) == 0.5  # midpoint

    assert abs(ease_out_back(0.0)) < 1e-10
    assert abs(ease_out_back(1.0) - 1.0) < 0.001
    # Overshoot
    assert ease_out_back(0.7) > 1.0  # should overshoot

    rl = RenderLib()
    assert rl.ease(0.0) == 0.0
    assert abs(rl.ease(1.0) - 1.0) < 0.001
    assert abs(rl.ease(0.5, "in_out_cubic") - 0.5) < 0.001

    print("  Easing test PASSED")
    return True


def test_animation_helpers():
    """Test animation helper functions."""
    rl = RenderLib()

    # alpha()
    assert rl.alpha(1.0, 0.0, fade_in=0.2) == 0.0, "alpha at progress=0 should be 0"
    assert abs(rl.alpha(1.0, 0.1, fade_in=0.2) - 0.5) < 0.01, "alpha at half fade-in should be ~0.5"
    assert rl.alpha(1.0, 0.5) == 1.0, "alpha in middle should be full"
    assert abs(rl.alpha(1.0, 0.9, fade_out=0.2) - 0.5) < 0.01, "alpha at half fade-out should be ~0.5"
    assert rl.alpha(1.0, 1.0, fade_out=0.2) == 0.0, "alpha at end should be 0"

    # slide()
    assert rl.slide(100, 500, 0.0) == 100.0
    assert rl.slide(100, 500, 1.0) == 500.0

    # pulse()
    p = rl.pulse(0.5, 0.2, 0.0)
    assert 0.4 < p < 0.6, f"pulse at t=0 should be near base, got {p}"
    p = rl.pulse(0.5, 0.2, 0.25)
    assert p > 0.5, f"pulse at t=0.25 should be above base, got {p}"

    # lerp()
    assert rl.lerp(0, 100, 0.0) == 0.0
    assert rl.lerp(0, 100, 1.0) == 100.0
    assert rl.lerp(0, 100, 0.5) == 50.0

    # clamp()
    assert rl.clamp(-0.5) == 0.0
    assert rl.clamp(1.5) == 1.0
    assert rl.clamp(0.5) == 0.5

    print("  Animation helpers test PASSED")
    return True


if __name__ == "__main__":
    print("RenderLib Smoke Test")
    print("=" * 50)
    test_smoke_frame()
    test_time_helpers()
    test_easing()
    test_animation_helpers()
    print("=" * 50)
    print("ALL TESTS PASSED")
