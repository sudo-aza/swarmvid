#!/usr/bin/env python3
"""generate_tts_batch.py — Batch generate Qwen3-TTS audio for all scene segments.

Runs locally on CPU using Qwen3-TTS-12Hz-0.6B-CustomVoice (open weights).
No API key needed. Duration follows content — no atempo.

Memory strategy: Model is loaded and freed PER CHUNK to avoid OOM on 8GB RAM.
The 0.6B model in float32 uses ~4.2GB; generation adds ~1.5GB peak.
Without freeing between chunks, 3rd chunk OOMs.

Segments are auto-split into <=150 char sentence-bounded chunks, each chunk
gets its own model load/generate/free cycle, then chunks are concatenated
per-segment, then per-scene.

Usage:
  python generate_tts_batch.py                        # Generate all scenes
  python generate_tts_batch.py --scene 1               # Generate just scene 1
  python generate_tts_batch.py --scene 1 --seg 0       # Generate just scene 1, seg 0
  python generate_tts_batch.py --from 1 --to 5         # Generate scenes 1-5
  python generate_tts_batch.py --resume               # Skip existing segments
"""

import argparse
import gc
import json
import os
import re
import shutil
import subprocess
import sys
import time


# ── Memory guard ────────────────────────────────────────────────────────────────

# Qwen3-TTS-12Hz-0.6B in float32 needs ~4.2GB model + ~1.5GB generation peak = ~5.7GB.
# We require MIN_FREE_MB of available RAM before spawning a chunk subprocess.
MIN_FREE_MB = 6200  # ~6.2 GB safety margin
MEMORY_CHECK_INTERVAL = 10  # seconds between checks when waiting


def get_available_mb() -> int:
    """Return available memory in MB (from /proc/meminfo or free)."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (OSError, FileNotFoundError):
        pass
    # Fallback: free command
    try:
        out = subprocess.check_output(["free", "-m"], text=True)
        # header line is 'Mem:', data is second line
        lines = out.strip().split("\n")
        if len(lines) >= 2:
            return int(lines[1].split()[6])  # 'available' column
    except Exception:
        pass
    return 0


def wait_for_memory(min_mb: int, label: str = "") -> None:
    """Block until at least min_mb is available. Prints status."""
    avail = get_available_mb()
    if avail >= min_mb:
        return
    print(f"    [MEM] Waiting for memory: {avail}MB available, need {min_mb}MB {label}", flush=True)
    waited = 0
    while avail < min_mb:
        time.sleep(MEMORY_CHECK_INTERVAL)
        waited += MEMORY_CHECK_INTERVAL
        avail = get_available_mb()
        if waited % 60 == 0:
            print(f"    [MEM] Still waiting... {avail}MB available ({waited}s) {label}", flush=True)
    print(f"    [MEM] Memory OK: {avail}MB available (waited {waited}s) {label}", flush=True)

# Add scripts/ to path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)


# ── Config ───────────────────────────────────────────────────────────────────────

MAX_CHUNK_CHARS = 150
MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
LANGUAGE = "German"
SPEAKER = "ryan"


# ── Text chunking ───────────────────────────────────────────────────────────────

def split_text_into_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    sentence_ends = list(re.finditer(r'(?<=[.!?;])\s+', text))
    chunks = []
    current_start = 0

    for match in sentence_ends:
        end_pos = match.end()
        chunk = text[current_start:end_pos].strip()
        if len(chunk) <= max_chars:
            chunks.append(chunk)
            current_start = end_pos
        else:
            sub_chunks = _split_by_clause(text[current_start:end_pos], max_chars)
            chunks.extend(sub_chunks)
            current_start = end_pos

    remaining = text[current_start:].strip()
    if remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
        else:
            chunks.extend(_split_by_clause(remaining, max_chars))

    chunks = [c for c in chunks if c.strip()]
    return chunks if chunks else [text[:max_chars], text[max_chars:]]


def _split_by_clause(text: str, max_chars: int) -> list[str]:
    clause_ends = list(re.finditer(r'(?<=[,:;—–-])\s+', text))
    chunks = []
    current_start = 0

    for match in clause_ends:
        end_pos = match.end()
        chunk = text[current_start:end_pos].strip()
        if chunk and len(chunk) <= max_chars:
            chunks.append(chunk)
            current_start = end_pos
        elif chunk:
            chunks.extend(_hard_split(chunk, max_chars))
            current_start = end_pos

    remaining = text[current_start:].strip()
    if remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
        else:
            chunks.extend(_hard_split(remaining, max_chars))

    return [c for c in chunks if c.strip()]


def _hard_split(text: str, max_chars: int) -> list[str]:
    words = text.split()
    chunks = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = word
        else:
            current += " " + word
    if current.strip():
        chunks.append(current.strip())
    return chunks


# ── Audio utilities ─────────────────────────────────────────────────────────────

def get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def concat_wav_files(file_list: list[str], output_path: str) -> bool:
    if len(file_list) == 0:
        return False
    if len(file_list) == 1:
        shutil.copy2(file_list[0], output_path)
        return True

    concat_list = output_path + ".concat.txt"
    with open(concat_list, "w") as f:
        for path in file_list:
            f.write(f"file '{os.path.abspath(path)}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, "-c:a", "pcm_s16le", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        os.unlink(concat_list)
    except OSError:
        pass
    return result.returncode == 0


# ── TTS generation (subprocess per chunk for memory isolation) ──────────────────

def generate_one_chunk(text: str, output_path: str, speaker: str) -> tuple[float, float]:
    """Generate one TTS chunk by calling generate_tts_chunk.py as a subprocess.

    Each chunk runs in its own process for complete memory isolation.
    Returns (audio_duration, cpu_time).
    """
    chunk_script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "generate_tts_chunk.py")
    cmd = [
        sys.executable, chunk_script,
        text,
        output_path,
        "--speaker", speaker,
        "--language", LANGUAGE,
    ]
    wait_for_memory(MIN_FREE_MB, f"for chunk ({len(text)} chars)")
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    cpu_time = time.time() - t0
    # Force kernel to reclaim pages from exited child
    gc.collect()

    if result.returncode != 0:
        raise RuntimeError(result.stderr[-500:] if result.stderr else "unknown error")

    # Parse JSON output from child
    import json as _json
    stdout = result.stdout.strip()
    # Find last line with JSON
    for line in reversed(stdout.split('\n')):
        line = line.strip()
        if line.startswith('{') and 'audio_dur' in line:
            data = _json.loads(line)
            return data['audio_dur'], cpu_time

    # Fallback: check file size
    if os.path.isfile(output_path) and os.path.getsize(output_path) > 100:
        dur = get_duration(output_path)
        return dur, cpu_time

    raise RuntimeError(f"No audio output from chunk generation. stdout: {stdout[-300:]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch Qwen3-TTS generation (reload-per-chunk)")
    parser.add_argument("--scene", type=int, default=None, help="Scene number")
    parser.add_argument("--seg", type=int, default=None, help="Segment number")
    parser.add_argument("--from", type=int, default=None, dest="from_scene", help="Start scene")
    parser.add_argument("--to", type=int, default=None, dest="to_scene", help="End scene")
    parser.add_argument("--resume", action="store_true", help="Skip existing segments")
    parser.add_argument("--speaker", type=str, default=SPEAKER, help="Speaker name")
    parser.add_argument("--scenes-dir", type=str, default="output/scenes")
    parser.add_argument("--audio-dir", type=str, default="output/audio")
    parser.add_argument("--max-chars", type=int, default=MAX_CHUNK_CHARS,
                        help=f"Max chars per TTS chunk (default: {MAX_CHUNK_CHARS})")
    args = parser.parse_args()

    # Determine which scenes to process
    if args.scene:
        scene_nums = [args.scene]
    elif args.from_scene and args.to_scene:
        scene_nums = list(range(args.from_scene, args.to_scene + 1))
    else:
        scene_nums = sorted([
            int(f.split("_")[1].split(".")[0])
            for f in os.listdir(args.scenes_dir)
            if f.startswith("scene_") and f.endswith(".json")
        ])

    print(f"Qwen3-TTS batch generation (reload-per-chunk, speaker={args.speaker})", flush=True)
    print(f"Scenes: {scene_nums[0] if scene_nums else '?'}-{scene_nums[-1] if scene_nums else '?'} ({len(scene_nums)} total)", flush=True)
    print(f"Max chunk size: {args.max_chars} chars", flush=True)
    print(f"Memory guard: require {MIN_FREE_MB}MB free before each chunk", flush=True)
    initial_mem = get_available_mb()
    print(f"Available memory: {initial_mem}MB", flush=True)

    t_batch_start = time.time()
    total_cpu = 0.0
    total_audio = 0.0
    total_segs = 0
    total_chunks = 0
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

        elapsed_batch = time.time() - t_batch_start
        print(f"\n{'='*60}")
        print(f"Scene {scene_num:02d} ({scene.get('title', '?')}): {len(segments)} segments "
              f"[{elapsed_batch/60:.1f}min elapsed]", flush=True)

        for i, seg in enumerate(segments):
            if args.seg is not None and i != args.seg:
                continue

            text = seg["text"]
            out_path = os.path.join(seg_dir, f"seg_{i:02d}.wav")

            # Skip existing complete segment
            if args.resume and os.path.isfile(out_path) and os.path.getsize(out_path) > 1000:
                dur = get_duration(out_path)
                total_audio += dur
                total_segs += 1
                print(f"  Seg {i}: SKIP (exists, {dur:.1f}s)")
                continue

            # Split into chunks
            chunks = split_text_into_chunks(text, args.max_chars)
            print(f"  Seg {i} ({len(text)} chars -> {len(chunks)} chunks)", flush=True)

            chunk_files = []
            for ci, chunk_text in enumerate(chunks):
                chunk_path = os.path.join(seg_dir, f"seg_{i:02d}_c{ci}.wav")

                # Skip existing chunk
                if args.resume and os.path.isfile(chunk_path) and os.path.getsize(chunk_path) > 1000:
                    chunk_files.append(chunk_path)
                    dur = get_duration(chunk_path)
                    total_audio += dur
                    total_chunks += 1
                    print(f"    c{ci}: SKIP ({len(chunk_text)} chars, {dur:.1f}s)")
                    continue

                print(f"    c{ci} ({len(chunk_text)} chars)...", end=" ", flush=True)
                sys.stdout.flush()

                try:
                    audio_dur, cpu_time = generate_one_chunk(
                        chunk_text, chunk_path, args.speaker
                    )
                    chunk_files.append(chunk_path)
                    total_cpu += cpu_time
                    total_audio += audio_dur
                    total_chunks += 1
                    print(f"OK {audio_dur:.1f}s/{cpu_time:.0f}s")
                except Exception as e:
                    print(f"FAILED ({e})")
                    errors += 1

            # Concat chunks into segment WAV
            if chunk_files:
                if len(chunk_files) == 1:
                    shutil.copy2(chunk_files[0], out_path)
                else:
                    ok = concat_wav_files(chunk_files, out_path)
                    if not ok:
                        print(f"    CONCAT FAILED for seg {i}")
                        errors += 1
                        continue

                seg_dur = get_duration(out_path)
                total_segs += 1
                # Update scene JSON duration_s with actual audio length
                scene["segments"][i]["duration_s"] = round(seg_dur, 2)
                print(f"  Seg {i} DONE: {seg_dur:.1f}s total (JSON updated)")
            else:
                print(f"  Seg {i}: NO chunks generated")

        # Write updated JSON with new durations
        if any(s.get("duration_s", 0) > 0 for s in scene.get("segments", [])):
            with open(scene_path, "w") as f:
                json.dump(scene, f, indent=2, ensure_ascii=False)
            print(f"  >> Scene {scene_num:02d} JSON updated with audio durations")

        # Concat all segments for this scene
        seg_files = sorted([
            os.path.join(seg_dir, f)
            for f in os.listdir(seg_dir)
            if re.match(r'^seg_\d+\.wav$', f) and os.path.getsize(os.path.join(seg_dir, f)) > 1000
        ])
        if seg_files:
            concat_path = os.path.join(args.audio_dir, f"scene_{scene_num:02d}.wav")
            concat_wav_files(seg_files, concat_path)
            final_dur = get_duration(concat_path)
            print(f"  >> Scene {scene_num:02d} audio: {final_dur:.1f}s")

    # ── Summary ──
    elapsed_total = time.time() - t_batch_start
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"  Segments: {total_segs}/{total_segs + errors}")
    print(f"  Chunks:   {total_chunks}")
    print(f"  Errors:   {errors}")
    print(f"  Audio:    {total_audio:.1f}s ({total_audio/60:.1f} min)")
    print(f"  CPU time: {elapsed_total:.0f}s ({elapsed_total/60:.1f} min)")
    if total_audio > 0:
        print(f"  Ratio:    {elapsed_total/total_audio:.1f}x realtime")


if __name__ == "__main__":
    main()
