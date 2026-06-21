#!/usr/bin/env python3
"""Generate TTS audio for narration segments.

Delegates to generate_tts_batch.py (local Qwen3-TTS, open weights).

Usage:
  python generate_tts.py output/scenes/scene_01.json
  python generate_tts.py --all    # Generate all scenes
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_SCRIPT = os.path.join(SCRIPT_DIR, "generate_tts_batch.py")

if len(sys.argv) > 1 and sys.argv[1] == "--all":
    result = subprocess.run([sys.executable, BATCH_SCRIPT, "--resume"])
else:
    scene_json = sys.argv[1] if len(sys.argv) > 1 else "output/scenes/scene_01.json"
    scene_num = int(os.path.basename(scene_json).split("_")[1].split(".")[0])
    result = subprocess.run([
        sys.executable, BATCH_SCRIPT,
        "--scene", str(scene_num), "--resume"
    ])

sys.exit(result.returncode)
