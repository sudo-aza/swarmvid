#!/usr/bin/env python3
"""generate_tts_batch.py — Batch generate Qwen3-TTS audio for all scene segments.

Runs locally on CPU using Qwen3-TTS-12Hz-0.6B-CustomVoice (open weights).
No API key needed. Duration follows content — no atempo.

Usage:
  python generate_tts_batch.py                    # Generate all scenes
  python generate_tts_batch.py --scene 1           # Generate just scene 1
  python generate_tts_batch.py --scene 1 --seg 0    # Generate just scene 1, seg 0
  python generate_tts_batch.py --from 1 --to 5     # Generate scenes 1-5
  python generate_tts_batch.py --resume            # Skip existing segments
"""

import argparse
import json
import os
import subprocess
import sys
import time


def get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description="Batch Qwen3-TTS generation")
    parser.add_argument("--scene", type=int, default=None, help="Scene number")
    parser.add_argument("--seg", type=int, default=None, help="Segment number")
    parser.add_argument("--from", type=int, default=None, dest="from_scene", help="Start scene")
    parser.add_argument("--to", type=int, default=None, dest="to_scene", help="End scene")
    parser.add_argument("--resume", action="store_true", help="Skip existing segments")
    parser.add_argument("--speaker", type=str, default="ryan", help="Speaker name")
    parser.add_argument("--scenes-dir", type=str, default="output/scenes")
    parser.add_argument("--audio-dir", type=str, default="output/audio")
    args = parser.parse_args()

    # Import and load model
    import torch
    from qwen_tts import Qwen3TTSModel
    import soundfile as sf

    print(f"Loading Qwen3-TTS (speaker={args.speaker})...", flush=True)
    t_load = time.time()
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        device_map=None,
        dtype=torch.float32,
        attn_implementation=None,
    )
    print(f"Model loaded: {time.time() - t_load:.0f}s", flush=True)

    # Determine which scenes to process
    if args.scene:
        scene_nums = [args.scene]
    elif args.from_scene and args.to_scene:
        scene_nums = list(range(args.from_scene, args.to_scene + 1))
    else:
        # All scenes with JSONs
        scene_nums = sorted([
            int(f.split("_")[1].split(".")[0])
            for f in os.listdir(args.scenes_dir)
            if f.startswith("scene_") and f.endswith(".json")
        ])

    total_cpu = 0.0
    total_audio = 0.0
    total_segs = 0
    errors = 0

    for scene_num in scene_nums:
        scene_path = os.path.join(args.scenes_dir, f"scene_{scene_num:02d}.json")
        if not os.path.isfile(scene_path):
            print(f"  Scene {scene_num}: JSON not found, skipping")
            continue

        with open(scene_path) as f:
            scene = json.load(f)

        segments = scene.get("segments", [])
        seg_dir = os.path.join(args.audio_dir, f"scene_{scene_num:02d}")
        os.makedirs(seg_dir, exist_ok=True)

        print(f"\nScene {scene_num} ({scene.get('title', '?')}): {len(segments)} segments")

        for i, seg in enumerate(segments):
            if args.seg is not None and i != args.seg:
                continue

            text = seg["text"]
            out_path = os.path.join(seg_dir, f"seg_{i:02d}.wav")

            # Skip existing
            if args.resume and os.path.isfile(out_path) and os.path.getsize(out_path) > 1000:
                dur = get_duration(out_path)
                total_audio += dur
                total_segs += 1
                continue

            print(f"  Seg {i} ({len(text)} chars)...", end=" ", flush=True)
            sys.stdout.flush()

            t0 = time.time()
            try:
                wavs, sr = model.generate_custom_voice(
                    text=text,
                    language="German",
                    speaker=args.speaker,
                    instruct="",
                )
                dur = len(wavs[0]) / sr
                sf.write(out_path, wavs[0], sr)
                elapsed = time.time() - t0
                total_cpu += elapsed
                total_audio += dur
                total_segs += 1
                print(f"OK audio={dur:.1f}s cpu={elapsed:.0f}s")
            except Exception as e:
                elapsed = time.time() - t0
                print(f"FAILED ({e})")
                errors += 1

        # Concat segments for this scene
        seg_files = sorted([
            os.path.join(seg_dir, f)
            for f in os.listdir(seg_dir)
            if f.startswith("seg_") and f.endswith(".wav") and os.path.getsize(os.path.join(seg_dir, f)) > 1000
        ])
        if len(seg_files) > 1:
            concat_path = os.path.join(args.audio_dir, f"scene_{scene_num:02d}.wav")
            concat_list = os.path.join(seg_dir, "concat.txt")
            with open(concat_list, "w") as f:
                for path in seg_files:
                    f.write(f"file '{os.path.abspath(path)}'\n")
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-c:a", "pcm_s16le", concat_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                final_dur = get_duration(concat_path)
                print(f"  Concatenated: {final_dur:.1f}s ({concat_path})")
            else:
                print(f"  Concat FAILED: {result.stderr[-200:]}")

    print(f"\n{'='*50}")
    print(f"Total: {total_segs} segments, {errors} errors")
    print(f"Audio: {total_audio:.1f}s ({total_audio/60:.1f} min)")
    print(f"CPU time: {total_cpu:.0f}s ({total_cpu/60:.1f} min)")
    if total_audio > 0:
        print(f"Ratio: {total_cpu/total_audio:.1f}x realtime")


if __name__ == "__main__":
    main()
