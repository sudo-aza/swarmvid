"""Particle systems — floating particles, embers, dust, rain, snow."""

from __future__ import annotations

import math
import random
from PIL import Image, ImageDraw


def precompute_particles(count: int, w: int, h: int,
                        seed: int,
                        style: str = "warm_glow") -> list[dict]:
    """Pre-compute particle data for a scene.
    style: 'warm_glow' (default golden particles), 'embers', 'dust', 'rain', 'snow'
    """
    rng = random.Random(seed)
    particles = []
    for _ in range(count):
        p = {
            "x": rng.randint(0, w),
            "y_base": rng.randint(0, h),
            "speed": rng.uniform(0.2, 0.8),
            "size": rng.randint(2, 5),
            "brightness": rng.randint(80, 200),
            "phase": rng.uniform(0, math.tau),
            "drift": rng.uniform(-0.3, 0.3),
        }
        if style == "embers":
            p.update({
                "color": (rng.randint(200, 255), rng.randint(80, 180), rng.randint(20, 60)),
                "speed": rng.uniform(0.5, 1.5),
                "size": rng.randint(1, 3),
                "brightness": rng.randint(150, 255),
                "drift": rng.uniform(-0.8, 0.8),
            })
        elif style == "dust":
            p.update({
                "color": (rng.randint(180, 220), rng.randint(180, 220), rng.randint(170, 200)),
                "speed": rng.uniform(0.05, 0.2),
                "size": rng.randint(1, 2),
                "brightness": rng.randint(40, 100),
            })
        elif style == "rain":
            p.update({
                "color": (100, 130, 180),
                "speed": rng.uniform(4.0, 8.0),
                "size": rng.randint(1, 2),
                "brightness": rng.randint(60, 120),
                "drift": 0,
            })
        elif style == "snow":
            p.update({
                "color": (220, 225, 235),
                "speed": rng.uniform(0.3, 0.8),
                "size": rng.randint(2, 4),
                "brightness": rng.randint(120, 200),
                "drift": rng.uniform(-0.5, 0.5),
            })
        else:  # warm_glow
            p["color"] = (255, 220, 180)
        particles.append(p)
    return particles


def draw_particles(od: ImageDraw.ImageDraw, particles: list[dict],
                    frame_idx: int, h: int) -> None:
    """Draw particles onto an RGBA overlay. Call on an ImageDraw of an RGBA image."""
    for p in particles:
        py_pos = (p["y_base"] - frame_idx * p["speed"]) % h
        px_pos = p["x"] + math.sin(frame_idx * 0.02 + p["phase"]) * p.get("drift", 0) * 20
        pulse = 0.5 + 0.5 * math.sin(frame_idx * 0.03 + p["phase"])
        color = p.get("color", (255, 220, 180))
        a = int(p["brightness"] * pulse)
        s = int(p["size"] * (0.8 + 0.2 * pulse))
        od.ellipse([px_pos - s, py_pos - s, px_pos + s, py_pos + s],
                   fill=(*color, min(255, a)))
