#!/usr/bin/env python3
"""
generate_tts_v2.py — Generate TTS audio using real Qwen3 TTS via DashScope API.

Architecture: Duration follows content. Generate at natural speed, let audio
length drive video duration. NO ffmpeg atempo, NO duration squeezing.

Requirements:
  - DASHSCOPE_API_KEY environment variable (Alibaba Cloud DashScope)
  - pip install dashscope soundfile

Usage:
  DASHSCOPE_API_KEY=sk-xxx python generate_tts_v2.py output/scenes/scene_01.json
"""

import json
import os
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "--user",
                   "--break-system-packages", "requests"], check=True)
    import requests

SCENE_JSON = sys.argv[1] if len(sys.argv) > 1 else "output/scenes/scene_01.json"
OUTPUT_DIR = "output/audio"

# DashScope API config
# Model options: "cosyvoice-v2", "cosyvoice-v3-flash", "qwen3-tts-instruct-flash"
MODEL = "cosyvoice-v2"
# Voice options for CosyVoice v2: longxiaochun_v2, longlaotie_v2, longshuo_v2,
#   longshu_v2, longjing_v2, longmiao_v2, longsui_v2, longfei_v2, etc.
# For German narration, try: longshuo_v2 (clear/standard male)
VOICE = "longshuo_v2"
FORMAT = "wav"       # mp3 or wav
SAMPLE_RATE = 24000

DASHSCOPE_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2audio/generation"


def get_api_key():
    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        print("ERROR: DASHSCOPE_API_KEY environment variable not set.")
        print("Get your key from: https://model-studio.console.aliyun.com/")
        sys.exit(1)
    return key


def generate_segment(text: str, output_path: str, api_key: str) -> bool:
    """Generate TTS for a single text segment via DashScope REST API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "input": {"text": text},
        "parameters": {
            "voice": VOICE,
            "format": FORMAT,
            "sample_rate": SAMPLE_RATE,
        }
    }

    for attempt in range(5):
        if attempt > 0:
            delay = 10 * (2 ** (attempt - 1))
            print(f"    retry {attempt} in {delay}s...", flush=True)
            time.sleep(delay)

        try:
            resp = requests.post(DASHSCOPE_API_URL, json=payload, headers=headers, timeout=120)
            if resp.status_code == 200:
                # DashScope returns audio as binary in the response
                audio_data = resp.content
                if len(audio_data) < 100:
                    print(f"    ERROR: response too small ({len(audio_data)} bytes)")
                    continue
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                return True
            elif resp.status_code == 429:
                print(f"    rate-limited", end="", flush=True)
                continue
            else:
                print(f"    API error {resp.status_code}: {resp.text[:200]}")
                return False
        except requests.exceptions.Timeout:
            print(f"    timeout", end="", flush=True)
            continue
        except Exception as e:
            print(f"    ERROR: {e}")
            return False

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

    print(f"Qwen3 TTS (DashScope) — Scene {scene_num}: {len(segments)} segments")
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
