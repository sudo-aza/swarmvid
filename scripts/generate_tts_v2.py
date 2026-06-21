#!/usr/bin/env python3
"""
generate_tts_v2.py — Generate TTS audio using real Qwen3 TTS via DashScope API.

Architecture: Duration follows content. Generate at natural speed, let audio
length drive video duration. NO ffmpeg atempo, NO duration squeezing.

Uses DashScope Python SDK (dashscope.audio.http_tts.HttpSpeechSynthesizer)
which handles authentication, request formatting, JSON response parsing,
and audio URL download automatically.

Requirements:
  - DASHSCOPE_API_KEY environment variable (Alibaba Cloud DashScope)
  - pip install dashscope

Usage:
  DASHSCOPE_API_KEY=sk-xxx python generate_tts_v2.py output/scenes/scene_01.json
"""

import json
import os
import subprocess
import sys
import time

try:
    from dashscope.audio.http_tts import HttpSpeechSynthesizer
except ImportError:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "dashscope"],
        check=True,
        capture_output=True,
    )
    from dashscope.audio.http_tts import HttpSpeechSynthesizer

SCENE_JSON = sys.argv[1] if len(sys.argv) > 1 else "output/scenes/scene_01.json"
OUTPUT_DIR = "output/audio"

# DashScope API config
# Model options: "cosyvoice-v2", "cosyvoice-v1", "cosyvoice-v3-flash", "cosyvoice-v3-plus"
# Voice options for cosyvoice-v2 (documented): longxiaochun_v2
# For cosyvoice-v1: longxiaochun, longlaotie, longshu, longjing, longmiao, longsui, longfei, longbella, longshuo
MODEL = "cosyvoice-v2"
VOICE = "longxiaochun_v2"  # Documented in DashScope voice list for cosyvoice-v2
FORMAT = "wav"
SAMPLE_RATE = 24000

# Retry config
MAX_RETRIES = 5
BASE_DELAY = 10  # seconds
RETRYABLE_STATUS_CODES = {429, 500, 502, 503}


def get_api_key():
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        print("ERROR: DASHSCOPE_API_KEY environment variable not set.")
        print("Get your key from: https://model-studio.console.aliyun.com/")
        sys.exit(1)
    return key


def generate_segment(text: str, output_path: str, api_key: str) -> bool:
    """Generate TTS for a single text segment via DashScope SDK.

    Uses HttpSpeechSynthesizer.call() which handles:
    - Authentication (Bearer token)
    - Correct endpoint: /services/audio/tts/SpeechSynthesizer
    - Correct request body format (input dict with voice/format/sample_rate inside)
    - Response parsing (JSON with audio URL → download audio data)
    """
    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            delay = BASE_DELAY * (2 ** min(attempt - 1, 4))
            print(f"    retry {attempt} in {delay}s...", flush=True)
            time.sleep(delay)

        try:
            result = HttpSpeechSynthesizer.call(
                model=MODEL,
                text=text,
                voice=VOICE,
                audio_format=FORMAT,
                sample_rate=SAMPLE_RATE,
                api_key=api_key,
            )

            # In non-streaming mode, the SDK always returns audio_url, not audio_data.
            # (audio_data is only populated in streaming mode.)
            if result.audio_url:
                import requests
                resp = requests.get(result.audio_url, timeout=60)
                if resp.status_code == 200 and len(resp.content) > 100:
                    with open(output_path, "wb") as f:
                        f.write(resp.content)
                    return True
            print(f"    no audio data (attempt {attempt})", end="", flush=True)
            time.sleep(5)
            continue

        except Exception as e:
            err_str = str(e).lower()
            # Check for retryable conditions
            is_retryable = any(code in err_str for code in ["429", "500", "502", "503"])
            if is_retryable and attempt < MAX_RETRIES - 1:
                print(f"    server error, will retry", end="", flush=True)
                continue
            print(f"    ERROR: {e}")
            if attempt == MAX_RETRIES - 1:
                return False
            continue

    print("    FAILED after max retries")
    return False


def get_duration(path: str) -> float:
    """Get audio duration in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def main():
    api_key = get_api_key()

    with open(SCENE_JSON) as f:
        scene = json.load(f)

    segments = scene.get("segments", [])
    scene_num = scene.get("scene_num", 1)
    seg_dir = os.path.join(OUTPUT_DIR, f"scene_{scene_num:02d}")
    os.makedirs(seg_dir, exist_ok=True)

    print(f"Qwen3 TTS (DashScope SDK) — Scene {scene_num}: {len(segments)} segments")
    print(f"Model: {MODEL}, Voice: {VOICE}, Speed: natural (1.0)")

    seg_files = []
    total_dur = 0.0
    segment_durations = []

    for i, seg in enumerate(segments):
        text = seg["text"]
        out_path = os.path.join(seg_dir, f"seg_{i:02d}.wav")
        print(f"\n  Segment {i} ({len(text)} chars)...", end=" ", flush=True)

        if os.path.isfile(out_path) and os.path.getsize(out_path) > 1000:
            dur = get_duration(out_path)
            print(f"exists ({dur:.1f}s)")
            seg_files.append(out_path)
            total_dur += dur
            segment_durations.append(dur)
            time.sleep(1)
            continue

        if generate_segment(text, out_path, api_key):
            dur = get_duration(out_path)
            print(f"OK ({dur:.1f}s)")
            seg_files.append(out_path)
            total_dur += dur
            segment_durations.append(dur)
        else:
            print("FAILED")
            segment_durations.append(None)

        # Rate limit buffer
        if i < len(segments) - 1:
            time.sleep(2)

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

    # Save updated scene JSON
    with open(SCENE_JSON, "w") as f:
        json.dump(scene, f, ensure_ascii=False, indent=2)
    print(f"  Updated: {SCENE_JSON}")


if __name__ == "__main__":
    main()
