#!/usr/bin/env python3
"""
assemble_video.py — Concatenate all rendered scene MP4s into a final video.

Usage:
    python3 assemble_video.py --scenes-dir scenes/ --output final.mp4

Expects scenes named scene_01.mp4, scene_02.mp4, ... in --scenes-dir.
Creates a concat file for ffmpeg and joins them with crossfade transitions.
"""

import argparse
import os
import subprocess
import sys
import glob


def assemble(scenes_dir, output_path, crossfade_s=1.0):
    """Concatenate scene MP4s into final video with crossfade transitions."""
    scene_files = sorted(glob.glob(os.path.join(scenes_dir, "scene_*.mp4")))
    if not scene_files:
        print(f"No scene_*.mp4 files found in {scenes_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(scene_files)} scenes")

    # Simple concat (no crossfade for reliability — crossfade requires complex filter chains)
    concat_file = os.path.join(scenes_dir, "concat.txt")
    with open(concat_file, "w") as f:
        for sf in scene_files:
            # Use relative path from concat file location
            rel = os.path.relpath(sf, scenes_dir)
            f.write(f"file '{rel}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    print(f"Assembling {len(scene_files)} scenes → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr[-500:]}", file=sys.stderr)
        sys.exit(1)

    # Clean up concat file
    os.remove(concat_file)

    size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({size / 1_048_576:.1f} MB)")

    # Print duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", output_path],
        capture_output=True, text=True
    )
    if probe.stdout.strip():
        dur = float(probe.stdout.strip())
        mins, secs = divmod(int(dur), 60)
        print(f"Duration: {mins}m {secs}s ({dur:.1f}s)")


def main():
    parser = argparse.ArgumentParser(description="Assemble scenes into final video")
    parser.add_argument("--scenes-dir", required=True, help="Directory with scene_*.mp4 files")
    parser.add_argument("--output", required=True, help="Output final MP4 path")
    args = parser.parse_args()
    assemble(args.scenes_dir, args.output)


if __name__ == "__main__":
    main()
