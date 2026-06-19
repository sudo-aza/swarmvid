#!/usr/bin/env python3
"""
pipeline.py — End-to-end video production pipeline for swarmvid.

Orchestrates the full workflow:
  1. Parse narration from BLACKBOARD.md into scene JSONs
  2. Generate TTS audio for each segment (WAV via z-ai CLI)
  3. Concatenate segment WAVs per scene into one audio file
  4. Render each scene (Pillow frames + audio → MP4)
  5. Assemble all scenes into final video with crossfades

Usage:
    python3 pipeline.py --blackboard BLACKBOARD.md --output-dir output/ [options]

Options:
    --voice <voice>          TTS voice name (default: jam)
    --tts-delay <seconds>   Delay between TTS calls (default: 11)
    --crossfade <seconds>   Crossfade duration (default: 1.0)
    --no-crossfade          Disable crossfade transitions
    --start-from <N>        Resume from scene N (skip scenes 1..N-1)
    --tts-only               Only generate TTS audio, skip rendering/assembly
    --render-only            Only render scenes (requires existing audio), skip TTS/assembly
"""

import argparse
import json
import os
import subprocess
import sys
import time

import wave as wave_mod

from parse_narration import parse_blackboard, build_scene_json


def get_wav_duration(filepath):
    """Get duration of a WAV file in seconds."""
    try:
        with wave_mod.open(filepath, "rb") as wf:
            return wf.getnframes() / wf.getframerate()
    except Exception:
        # Fallback to ffprobe for non-standard WAVs
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", filepath],
            capture_output=True, text=True
        )
        try:
            return float(json.loads(result.stdout)["format"]["duration"])
        except (KeyError, ValueError):
            return 0.0



def step_parse_narration(blackboard_path, scenes_dir, default_duration):
    """Step 1: Parse BLACKBOARD.md into scene JSONs."""
    print(f"\n{'='*60}")
    print("STEP 1: Parse narration from BLACKBOARD")
    print(f"{'='*60}")

    os.makedirs(scenes_dir, exist_ok=True)

    # Import and run parse_narration
    scenes = parse_blackboard(blackboard_path)
    total_segments = 0

    for scene in scenes:
        scene_json = build_scene_json(scene, default_duration)
        total_segments += len(scene_json["segments"])

        filename = f"scene_{scene_json['scene_num']:02d}.json"
        outpath = os.path.join(scenes_dir, filename)
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(scene_json, f, ensure_ascii=False, indent=2)

    print(f"  Generated {len(scenes)} scene JSONs with {total_segments} segments")
    return scenes_dir


def step_generate_tts(scenes_dir, audio_dir, voice, tts_delay, start_from=1):
    """Step 2: Generate TTS WAV for each segment using z-ai CLI."""
    print(f"\n{'='*60}")
    print("STEP 2: Generate TTS audio")
    print(f"{'='*60}")

    os.makedirs(audio_dir, exist_ok=True)

    scene_files = sorted(f for f in os.listdir(scenes_dir) if f.endswith(".json"))
    total_segments = 0
    total_duration = 0.0
    errors = 0

    for scene_file in scene_files:
        scene_path = os.path.join(scenes_dir, scene_file)
        with open(scene_path, "r", encoding="utf-8") as f:
            scene = json.load(f)

        scene_num = scene["scene_num"]
        if scene_num < start_from:
            print(f"  Skipping scene {scene_num} (start_from={start_from})")
            continue

        print(f"\n  Scene {scene_num}: {scene['title']}")

        # Track actual durations for JSON update
        actual_durations = []
        scene_dirty = False

        for seg_idx, segment in enumerate(scene["segments"]):
            seg_id = f"S{scene_num}.{seg_idx + 1}"
            out_path = os.path.join(audio_dir, f"scene_{scene_num:02d}_seg_{seg_idx:02d}.wav")

            # Skip if already generated (resume support)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
                print(f"    {seg_id}: exists ({os.path.getsize(out_path)//1024}KB) — skipping")
                total_segments += 1
                continue

            text = segment["text"]
            if len(text) > 1024:
                print(f"    {seg_id}: WARNING — text {len(text)} chars exceeds 1024 limit, truncating")
                text = text[:1020] + "..."

            cmd = [
                "z-ai", "tts",
                "-i", text,
                "-o", out_path,
                "--voice", voice,
                "--format", "wav",
            ]

            print(f"    {seg_id}: generating ({len(text)} chars)...", end=" ", flush=True)
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"FAILED")
                print(f"      {result.stderr[-200:]}")
                errors += 1
                actual_durations.append(segment.get("duration_s", 12.0))
                # Create a silent placeholder so pipeline can continue
                subprocess.run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=channel_layout=stereo:sample_rate=24000",
                    "-t", str(segment.get("duration_s", 12)),
                    "-c:a", "pcm_s16le", out_path
                ], capture_output=True)
            else:
                size = os.path.getsize(out_path)
                # Measure actual duration
                actual_dur = get_wav_duration(out_path)
                actual_durations.append(actual_dur)
                total_duration += actual_dur
                print(f"OK ({size//1024}KB, {actual_dur:.1f}s)")

                # Update JSON duration_s if it differs significantly
                if abs(actual_dur - segment.get("duration_s", 12.0)) > 0.5:
                    scene_dirty = True
                    segment["duration_s"] = round(actual_dur, 2)

            total_segments += 1

            # Rate limiting delay
            if tts_delay > 0:
                time.sleep(tts_delay)

        # Update scene JSON with actual TTS durations
        if scene_dirty:
            with open(scene_path, "w", encoding="utf-8") as f:
                json.dump(scene, f, ensure_ascii=False, indent=2)
            print(f"    Updated scene JSON with actual TTS durations")

    print(f"\n  TTS complete: {total_segments} segments, {errors} errors, {total_duration:.0f}s total audio")
    return audio_dir, errors == 0


def step_concat_audio(scenes_dir, audio_dir, concat_audio_dir):
    """Step 3: Concatenate segment WAVs per scene into single scene audio."""
    print(f"\n{'='*60}")
    print("STEP 3: Concatenate segment audio per scene")
    print(f"{'='*60}")

    os.makedirs(concat_audio_dir, exist_ok=True)

    scene_files = sorted(f for f in os.listdir(scenes_dir) if f.endswith(".json"))

    for scene_file in scene_files:
        scene_path = os.path.join(scenes_dir, scene_file)
        with open(scene_path, "r", encoding="utf-8") as f:
            scene = json.load(f)

        scene_num = scene["scene_num"]
        out_path = os.path.join(concat_audio_dir, f"scene_{scene_num:02d}.wav")

        if os.path.exists(out_path):
            print(f"  Scene {scene_num}: exists — skipping")
            continue

        # Find all segment WAVs for this scene
        seg_files = sorted(
            f for f in os.listdir(audio_dir)
            if f.startswith(f"scene_{scene_num:02d}_seg_") and f.endswith(".wav")
        )

        if not seg_files:
            print(f"  Scene {scene_num}: no segment audio found — skipping")
            continue

        # Create concat list for ffmpeg
        concat_list = os.path.join(concat_audio_dir, f"concat_{scene_num:02d}.txt")
        with open(concat_list, "w") as f:
            for seg_f in seg_files:
                f.write(f"file '{os.path.join(audio_dir, seg_f)}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list,
            "-c:a", "pcm_s16le",
            out_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        os.remove(concat_list)

        if result.returncode != 0:
            print(f"  Scene {scene_num}: concat FAILED — {result.stderr[-200:]}")
            continue

        size = os.path.getsize(out_path)
        print(f"  Scene {scene_num}: {len(seg_files)} segments → {size//1024}KB")

    print(f"  Concatenated audio in {concat_audio_dir}/")
    return concat_audio_dir


def step_render_scenes(scenes_dir, concat_audio_dir, rendered_dir, start_from=1):
    """Step 4: Render each scene (Pillow frames + audio → MP4)."""
    print(f"\n{'='*60}")
    print("STEP 4: Render scenes")
    print(f"{'='*60}")

    os.makedirs(rendered_dir, exist_ok=True)

    scene_files = sorted(f for f in os.listdir(scenes_dir) if f.endswith(".json"))
    errors = 0

    for scene_file in scene_files:
        scene_path = os.path.join(scenes_dir, scene_file)
        with open(scene_path, "r", encoding="utf-8") as f:
            scene = json.load(f)

        scene_num = scene["scene_num"]
        if scene_num < start_from:
            print(f"  Skipping scene {scene_num}")
            continue

        scene_json = os.path.join(scenes_dir, f"scene_{scene_num:02d}.json")
        scene_audio = os.path.join(concat_audio_dir, f"scene_{scene_num:02d}.wav")
        scene_output = os.path.join(rendered_dir, f"scene_{scene_num:02d}.mp4")

        if os.path.exists(scene_output) and os.path.getsize(scene_output) > 10000:
            print(f"  Scene {scene_num}: exists — skipping")
            continue

        if not os.path.exists(scene_audio):
            print(f"  Scene {scene_num}: no audio — skipping")
            continue

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "render_scene.py"),
            "--scene-json", scene_json,
            "--audio", scene_audio,
            "--output", scene_output,
        ]

        print(f"  Scene {scene_num}: rendering...", flush=True)
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"    FAILED: {result.stderr[-300:]}")
            errors += 1
        else:
            size = os.path.getsize(scene_output)
            # Print last few lines of output (includes duration)
            for line in result.stdout.strip().split("\n")[-2:]:
                print(f"    {line}")

    print(f"  Render complete: {len(scene_files)} scenes, {errors} errors")
    return rendered_dir, errors == 0


def step_assemble(rendered_dir, output_path, crossfade_s, use_crossfade):
    """Step 5: Assemble scenes into final video."""
    print(f"\n{'='*60}")
    print("STEP 5: Assemble final video")
    print(f"{'='*60}")

    assemble_script = os.path.join(os.path.dirname(__file__), "assemble_video.py")
    cmd = [
        sys.executable, assemble_script,
        "--scenes-dir", rendered_dir,
        "--output", output_path,
    ]
    if use_crossfade:
        cmd.extend(["--crossfade", str(crossfade_s)])
    else:
        cmd.append("--no-crossfade")

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"  ASSEMBLY FAILED: {result.stderr[-500:]}", file=sys.stderr)
        return False

    return os.path.exists(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end swarmvid pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--blackboard", default="BLACKBOARD.md",
                        help="Path to BLACKBOARD.md (default: BLACKBOARD.md)")
    parser.add_argument("--output-dir", default="output",
                        help="Root output directory (default: output/)")
    parser.add_argument("--voice", default="jam",
                        help="TTS voice name (default: jam)")
    parser.add_argument("--tts-delay", type=float, default=11.0,
                        help="Delay between TTS API calls in seconds (default: 11)")
    parser.add_argument("--crossfade", type=float, default=1.0,
                        help="Crossfade duration in seconds (default: 1.0)")
    parser.add_argument("--no-crossfade", action="store_true",
                        help="Disable crossfade transitions")
    parser.add_argument("--start-from", type=int, default=1,
                        help="Resume from scene N (1-indexed, default: 1)")
    parser.add_argument("--default-duration", type=float, default=12.0,
                        help="Default segment duration in seconds (default: 12.0)")
    parser.add_argument("--tts-only", action="store_true",
                        help="Only generate TTS audio")
    parser.add_argument("--render-only", action="store_true",
                        help="Only render scenes (skip TTS and assembly)")
    args = parser.parse_args()

    # Directory layout
    scenes_dir = os.path.join(args.output_dir, "scenes")
    audio_dir = os.path.join(args.output_dir, "audio_segments")
    concat_audio_dir = os.path.join(args.output_dir, "audio_scenes")
    rendered_dir = os.path.join(args.output_dir, "rendered")
    final_output = os.path.join(args.output_dir, "final.mp4")

    print(f"swarmvid pipeline — output dir: {args.output_dir}/")
    print(f"Voice: {args.voice}, TTS delay: {args.tts_delay}s, Crossfade: {args.crossfade}s")

    start_time = time.time()

    # Step 1: Parse narration
    if not args.render_only:
        step_parse_narration(args.blackboard, scenes_dir, args.default_duration)

    # Step 2: Generate TTS
    if not args.render_only:
        step_generate_tts(scenes_dir, audio_dir, args.voice, args.tts_delay,
                         start_from=args.start_from)

        if args.tts_only:
            elapsed = time.time() - start_time
            print(f"\nTTS-only mode complete. Elapsed: {elapsed:.0f}s")
            return

        # Step 3: Concatenate audio per scene
        step_concat_audio(scenes_dir, audio_dir, concat_audio_dir)

    # Step 4: Render scenes
    step_render_scenes(scenes_dir, concat_audio_dir, rendered_dir,
                      start_from=args.start_from)

    if args.render_only:
        elapsed = time.time() - start_time
        print(f"\nRender-only mode complete. Elapsed: {elapsed:.0f}s")
        return

    # Step 5: Assemble final video
    success = step_assemble(rendered_dir, final_output, args.crossfade,
                           use_crossfade=not args.no_crossfade)

    elapsed = time.time() - start_time
    if success:
        size = os.path.getsize(final_output)
        print(f"\nPipeline complete! {final_output} ({size / 1_048_576:.1f} MB)")
    else:
        print(f"\nPipeline finished with errors.")

    print(f"Total elapsed: {elapsed:.0f}s ({elapsed / 60:.1f}m)")


if __name__ == "__main__":
    main()
