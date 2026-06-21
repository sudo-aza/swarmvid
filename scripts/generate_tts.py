#!/usr/bin/env python3
"""Generate TTS audio for narration segments.

This is a wrapper that delegates to generate_tts_v2.py (DashScope Qwen3 TTS).

Usage:
  DASHSCOPE_API_KEY=sk-xxx python generate_tts.py output/scenes/scene_01.json
"""

import os
import subprocess
import sys

# Delegate to v2 (real Qwen3 TTS via DashScope)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
V2_SCRIPT = os.path.join(SCRIPT_DIR, "generate_tts_v2.py")

scene_json = sys.argv[1] if len(sys.argv) > 1 else "output/scenes/scene_01.json"
result = subprocess.run([sys.executable, V2_SCRIPT, scene_json])
sys.exit(result.returncode)
