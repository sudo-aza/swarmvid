#!/usr/bin/env python3
"""Generate TTS audio for all narration segments of a scene, then concatenate."""

import json
import os
import subprocess
import sys

SCENE_JSON = sys.argv[1] if len(sys.argv) > 1 else "output/scenes/scene_01.json"
OUTPUT_DIR = "output/audio"
VOICE = "jam"
SPEED = 1.3


def generate_segment(text: str, output_path: str) -> bool:
    """Generate TTS for a single text segment."""
    cmd = [
        "z-ai", "tts",
        "-i", text,
        "-o", output_path,
        "--voice", VOICE,
        "--speed", str(SPEED),
        "--format", "wav",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:200]}")
        return False
    return True


def get_duration(path: str) -> float:
    """Get WAV duration in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def main():
    with open(SCENE_JSON) as f:
        scene = json.load(f)

    segments = scene.get("segments", [])
    scene_num = scene.get("scene_num", 1)
    seg_dir = os.path.join(OUTPUT_DIR, f"scene_{scene_num:02d}")
    os.makedirs(seg_dir, exist_ok=True)

    print(f"Generating TTS for scene {scene_num}: {len(segments)} segments")
    print(f"Voice: {VOICE}, Speed: {SPEED}")

    seg_files = []
    total_dur = 0.0

    for i, seg in enumerate(segments):
        text = seg["text"]
        out_path = os.path.join(seg_dir, f"seg_{i:02d}.wav")
        print(f"\n  Segment {i} ({len(text)} chars)...", end=" ", flush=True)

        if os.path.isfile(out_path) and os.path.getsize(out_path) > 1000:
            dur = get_duration(out_path)
            print(f"exists ({dur:.1f}s)")
            seg_files.append(out_path)
            total_dur += dur
            continue

        if generate_segment(text, out_path):
            dur = get_duration(out_path)
            print(f"OK ({dur:.1f}s)")
            seg_files.append(out_path)
            total_dur += dur
        else:
            print("FAILED")

    # Concatenate all segments
    concat_path = os.path.join(OUTPUT_DIR, f"scene_{scene_num:02d}.wav")
    print(f"\nConcatenating {len(seg_files)} segments ({total_dur:.1f}s total)...")

    # Create concat file for ffmpeg
    concat_list = os.path.join(seg_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for path in seg_files:
            f.write(f"file '{os.path.abspath(path)}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c:a", "pcm_s16le",
        concat_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg concat error: {result.stderr[-300:]}")
        return

    final_dur = get_duration(concat_path)
    size = os.path.getsize(concat_path)
    print(f"Final audio: {concat_path} ({final_dur:.1f}s, {size / 1_048_576:.1f} MB)")
    print(f"Planned duration was: {sum(s['duration_s'] for s in segments)}s")


if __name__ == "__main__":
    main()
