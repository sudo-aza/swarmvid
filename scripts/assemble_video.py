#!/usr/bin/env python3
"""
assemble_video.py — Concatenate rendered scene MP4s with crossfade transitions.

Usage:
    python3 assemble_video.py --scenes-dir scenes/ --output final.mp4 [--crossfade 1.0]
    python3 assemble_video.py --scenes-dir scenes/ --output final.mp4 --no-crossfade

Expects scenes named scene_01.mp4, scene_02.mp4, ... in --scenes-dir.
Uses ffmpeg xfade filter for smooth scene transitions.
"""

import argparse
import json
import os
import subprocess
import sys
import glob


def get_duration(filepath):
    """Get duration of a video file in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "json", filepath],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ffprobe error for {filepath}: {result.stderr}", file=sys.stderr)
        return 0.0
    try:
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except (KeyError, ValueError):
        return 0.0


def has_audio_stream(filepath):
    """Check if a media file contains an audio stream."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_streams", "-select_streams", "a",
         "-of", "json", filepath],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return False
    try:
        info = json.loads(result.stdout)
        return len(info.get("streams", [])) > 0
    except (KeyError, ValueError):
        return False


def ensure_audio(scene_files, tmp_dir):
    """Add silent audio track to any scene that lacks one.

    Returns a list of file paths (originals or temp copies with audio).
    Caller is responsible for cleaning up tmp_dir.
    """
    os.makedirs(tmp_dir, exist_ok=True)
    result_files = []
    for sf in scene_files:
        if has_audio_stream(sf):
            result_files.append(sf)
        else:
            # Add silent audio matching video duration
            out = os.path.join(tmp_dir, os.path.basename(sf))
            dur = get_duration(sf)
            cmd = [
                "ffmpeg", "-y",
                "-i", sf,
                "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                out,
            ]
            print(f"  {os.path.basename(sf)}: no audio — adding silent track ({dur:.1f}s)")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                print(f"ERROR: failed to add audio to {sf}: {proc.stderr[-300:]}",
                      file=sys.stderr)
                sys.exit(1)
            result_files.append(out)
    return result_files, any(sf != orig for sf, orig in zip(result_files, scene_files))


def assemble_crossfade(scene_files, output_path, crossfade_s=1.0):
    """Concatenate scenes with xfade crossfade transitions.

    Builds a chain of ffmpeg xfade filters. Each consecutive pair of scenes
    gets a video crossfade and an audio crossfade. Requires all scenes to
    have the same resolution and codec parameters.
    """
    if len(scene_files) < 2:
        # Single scene — just copy with re-encode
        cmd = [
            "ffmpeg", "-y",
            "-i", scene_files[0],
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-profile:v", "main", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            output_path,
        ]
        print(f"Single scene — copying {scene_files[0]} → {output_path}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ffmpeg error: {result.stderr[-500:]}", file=sys.stderr)
            sys.exit(1)
        return

    # Get duration of each scene
    durations = []
    for sf in scene_files:
        dur = get_duration(sf)
        durations.append(dur)
        print(f"  {os.path.basename(sf)}: {dur:.1f}s")

    # Verify all scenes are at least crossfade_s long
    for i, (sf, dur) in enumerate(zip(scene_files, durations)):
        if dur < crossfade_s:
            print(f"ERROR: {os.path.basename(sf)} ({dur:.1f}s) is shorter than "
                  f"crossfade duration ({crossfade_s}s)", file=sys.stderr)
            sys.exit(1)

    # Build ffmpeg filter chain
    # Strategy: chain filters sequentially using output labels from previous step.
    # Step 0: [0:v][1:v]xfade → [vt0]; [0:a][1:a]acrossfade → [at0]
    # Step 1: [vt0][2:v]xfade → [vt1]; [at0][2:a]acrossfade → [at1]
    # ...
    # Last step: output has no label, mapped directly.
    n = len(scene_files)

    # Build input arguments
    inputs = []
    for sf in scene_files:
        inputs.extend(["-i", sf])

    # Build filter chains
    v_filters = []
    a_filters = []

    # Current input labels for video and audio
    cur_v_in = "[0:v]"
    cur_a_in = "[0:a]"

    # xfade offset: time into the accumulated output where next crossfade begins
    xfade_offset = durations[0] - crossfade_s

    transitions = ["fade", "slideright", "fadeblack", "smoothleft", "circleopen"]

    for i in range(n - 1):
        is_last = (i == n - 2)
        # Output label: named for intermediate, special final labels for last
        out_v = "[vout]" if is_last else f"[vt{i}]"
        out_a = "[aout]" if is_last else f"[at{i}]"

        transition = transitions[i % len(transitions)]

        # Next input is the raw file index (1, 2, 3, ...)
        next_v = f"[{i+1}:v]"
        next_a = f"[{i+1}:a]"

        # Video xfade
        v_filters.append(
            f"{cur_v_in}{next_v}xfade=transition={transition}"
            f":duration={crossfade_s:.3f}:offset={xfade_offset:.3f}{out_v}"
        )

        # Audio acrossfade
        a_filters.append(
            f"{cur_a_in}{next_a}acrossfade=d={crossfade_s:.3f}"
            f":c1=tri:c2=tri{out_a}"
        )

        # Update current input labels for next iteration
        if not is_last:
            cur_v_in = f"[vt{i}]"
            cur_a_in = f"[at{i}]"

        # Next offset
        if not is_last:
            xfade_offset += durations[i + 1] - crossfade_s

    # Combine all filters
    all_filters = ";".join(v_filters + a_filters)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", all_filters,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-profile:v", "main", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    print(f"\nAssembling {n} scenes with {crossfade_s}s crossfade → {output_path}")
    print(f"Filter chain: {len(v_filters)} video xfade + {len(a_filters)} audio acrossfade")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr[-800:]}", file=sys.stderr)
        sys.exit(1)

    size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({size / 1_048_576:.1f} MB)")

    # Print duration
    dur = get_duration(output_path)
    if dur > 0:
        mins, secs = divmod(int(dur), 60)
        print(f"Duration: {mins}m {secs}s ({dur:.1f}s)")


def assemble_concat(scene_files, output_path):
    """Simple concatenation without crossfade (hard cuts)."""
    concat_file = os.path.join(os.path.dirname(output_path), "concat.txt")
    with open(concat_file, "w") as f:
        for sf in scene_files:
            f.write(f"file '{sf}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-profile:v", "main", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    print(f"Assembling {len(scene_files)} scenes (hard cuts) → {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr[-500:]}", file=sys.stderr)
        sys.exit(1)

    os.remove(concat_file)

    size = os.path.getsize(output_path)
    print(f"Done: {output_path} ({size / 1_048_576:.1f} MB)")

    dur = get_duration(output_path)
    if dur > 0:
        mins, secs = divmod(int(dur), 60)
        print(f"Duration: {mins}m {secs}s ({dur:.1f}s)")


def assemble(scenes_dir, output_path, crossfade_s=1.0, use_crossfade=True):
    """Concatenate scene MP4s into final video.

    Args:
        scenes_dir: Directory containing scene_*.mp4 files
        output_path: Output MP4 path
        crossfade_s: Crossfade duration in seconds (default 1.0)
        use_crossfade: If True, use xfade transitions; if False, hard cuts
    """
    import shutil
    scene_files = sorted(glob.glob(os.path.join(scenes_dir, "scene_*.mp4")))
    if not scene_files:
        print(f"No scene_*.mp4 files found in {scenes_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(scene_files)} scenes")

    # Ensure all scenes have an audio track before assembly
    tmp_dir = os.path.join(os.path.dirname(output_path), ".assemble_tmp")
    safe_files, had_temps = ensure_audio(scene_files, tmp_dir)

    try:
        if use_crossfade and len(safe_files) > 1:
            assemble_crossfade(safe_files, output_path, crossfade_s)
        else:
            assemble_concat(safe_files, output_path)
    finally:
        # Clean up temp files if any were created
        if had_temps and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir)
            print(f"Cleaned up temp audio-fix files")


def main():
    parser = argparse.ArgumentParser(description="Assemble scenes into final video")
    parser.add_argument("--scenes-dir", required=True, help="Directory with scene_*.mp4 files")
    parser.add_argument("--output", required=True, help="Output final MP4 path")
    parser.add_argument("--crossfade", type=float, default=1.0,
                        help="Crossfade duration in seconds (default: 1.0)")
    parser.add_argument("--no-crossfade", action="store_true",
                        help="Disable crossfade transitions (use hard cuts)")
    args = parser.parse_args()
    assemble(args.scenes_dir, args.output, crossfade_s=args.crossfade,
             use_crossfade=not args.no_crossfade)


if __name__ == "__main__":
    main()
