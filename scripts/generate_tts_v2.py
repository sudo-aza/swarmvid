#!/usr/bin/env python3
"""
generate_tts_v2.py — Generate TTS audio using Qwen3-TTS (local, open weights).

Architecture: Duration follows content. Generate at natural speed, let audio
length drive video duration. NO ffmpeg atempo, NO duration squeezing.

Uses Qwen3-TTS-12Hz-0.6B-CustomVoice (open weights from Alibaba/Qwen).
Runs locally on CPU — no API key, no cloud service, no network required
after initial model download.

Requirements:
  pip install qwen-tts torch torchaudio soundfile

Usage:
  python generate_tts_v2.py output/scenes/scene_01.json
  python generate_tts_v2.py output/scenes/scene_01.json --speaker ryan
"""

import json
import os
import subprocess
import sys
import time

# ── Config ────────────────────────────────────────────────────────────────────

SCENE_JSON = sys.argv[1] if len(sys.argv) > 1 else "output/scenes/scene_01.json"
OUTPUT_DIR = "output/audio"

# Qwen3-TTS model config
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
LANGUAGE = "German"
SPEAKER = "ryan"  # English native speaker, speaks German well
# Other speakers: aiden, dylan, eric, ono_anna, serena, sohee, uncle_fu, vivian


# ── Model loading ─────────────────────────────────────────────────────────────

_model = None


def load_model(speaker=None):
    """Load Qwen3-TTS model (cached after first call)."""
    global _model
    if _model is not None:
        return _model

    import torch
    from qwen_tts import Qwen3TTSModel

    print(f"Loading Qwen3-TTS: {MODEL_ID} ...", flush=True)
    t0 = time.time()
    _model = Qwen3TTSModel.from_pretrained(
        MODEL_ID,
        device_map=None,  # CPU
        dtype=torch.float32,
        attn_implementation=None,  # No flash attention on CPU
    )
    print(f"Model loaded in {time.time() - t0:.1f}s", flush=True)
    print(f"Languages: {sorted(_model.get_supported_languages())}")
    print(f"Speakers: {sorted(_model.get_supported_speakers())}")
    return _model


# ── TTS generation ─────────────────────────────────────────────────────────────

def generate_segment(text: str, output_path: str, speaker: str) -> bool:
    """Generate TTS for a single text segment using local Qwen3-TTS."""
    import soundfile as sf

    model = load_model()

    try:
        wavs, sr = model.generate_custom_voice(
            text=text,
            language=LANGUAGE,
            speaker=speaker,
            instruct="",
        )

        # wavs is a list of arrays; take the first
        if wavs and len(wavs[0]) > 0:
            sf.write(output_path, wavs[0], sr)
            return True
        else:
            print("empty audio", end="", flush=True)
            return False

    except Exception as e:
        print(f"ERROR: {e}", end="", flush=True)
        return False


# ── Audio utilities ───────────────────────────────────────────────────────────

def get_duration(path: str) -> float:
    """Get audio duration in seconds via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Parse optional speaker arg
    speaker = SPEAKER
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    if args:
        speaker = args[0].lower()

    with open(SCENE_JSON) as f:
        scene = json.load(f)

    segments = scene.get("segments", [])
    scene_num = scene.get("scene_num", 1)
    seg_dir = os.path.join(OUTPUT_DIR, f"scene_{scene_num:02d}")
    os.makedirs(seg_dir, exist_ok=True)

    print(f"Qwen3-TTS (local, CPU) — Scene {scene_num}: {len(segments)} segments")
    print(f"Model: {MODEL_ID}, Speaker: {speaker}, Language: {LANGUAGE}")
    print(f"Speed: natural (1.0) — duration follows content")

    # Load model once
    load_model()
    print()

    seg_files = []
    total_dur = 0.0
    segment_durations = []

    for i, seg in enumerate(segments):
        text = seg["text"]
        out_path = os.path.join(seg_dir, f"seg_{i:02d}.wav")
        print(f"  Segment {i} ({len(text)} chars)...", end=" ", flush=True)

        # Skip if already generated (resume support)
        if os.path.isfile(out_path) and os.path.getsize(out_path) > 1000:
            dur = get_duration(out_path)
            print(f"exists ({dur:.1f}s)")
            seg_files.append(out_path)
            total_dur += dur
            segment_durations.append(dur)
            continue

        t0 = time.time()
        if generate_segment(text, out_path, speaker):
            dur = get_duration(out_path)
            elapsed = time.time() - t0
            print(f"OK ({dur:.1f}s, {elapsed:.1f}s CPU)")
            seg_files.append(out_path)
            total_dur += dur
            segment_durations.append(dur)
        else:
            print("FAILED")
            segment_durations.append(None)

    # Concatenate all segments (NO atempo — natural speed only)
    if not seg_files:
        print("\nNo segments generated!")
        return

    concat_path = os.path.join(OUTPUT_DIR, f"scene_{scene_num:02d}.wav")
    print(f"\nConcatenating {len(seg_files)} segments ({total_dur:.1f}s total)...")

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
    print(f"\nFinal audio: {concat_path}")
    print(f"  Duration: {final_dur:.1f}s ({final_dur / 60:.1f} min)")
    print(f"  Size: {size / 1_048_576:.1f} MB")

    # Update scene JSON with actual segment durations
    print(f"\nUpdating scene JSON with actual segment durations...")
    scene["segments_original_duration"] = [s["duration_s"] for s in segments]
    for i, seg in enumerate(segments):
        if segment_durations[i] is not None:
            seg["duration_s"] = round(segment_durations[i], 1)

    planned = sum(s["duration_s"] for s in scene["segments_original_duration"])
    print(f"  Planned: {planned:.1f}s → Actual: {final_dur:.1f}s")
    print(f"  Duration follows content — NO atempo applied.")

    with open(SCENE_JSON, "w") as f:
        json.dump(scene, f, ensure_ascii=False, indent=2)
    print(f"  Updated: {SCENE_JSON}")


if __name__ == "__main__":
    main()
