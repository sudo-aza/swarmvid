#!/usr/bin/env python3
"""Scene 22 — Generic renderer.

All visual behavior is driven by the scene JSON:
gradient, accent, visual_treatment, visual_events.
"""
import os
import sys

_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from generic_scene import prepare, render  # noqa: F401
