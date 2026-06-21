#!/usr/bin/env python3
"""run_tts_scene.py — Generate TTS for one segment at a time with absolute paths.

Designed to be called from any working directory. Handles chunking, subprocess
TTS generation, concatenation, and JSON duration update.

Usage:
    python3 /absolute/path/run_tts_scene.py --scene 1 --seg 1
    python3 /absolute/path/run_tts_scene.py --scene 1  (all segments, --resume)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def split_text_into_chunks(text, max_chars=150):
    if len(text) <= max_chars:
        return [text]
    sentence_ends = list(re.finditer(r'(?<=[.!?;])\s+', text))
    chunks, current_start = [], 0
    for match in sentence_ends:
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
    return [c for c in chunks if c.strip()] or [text[:max_chars], text[max_chars:]]


def _hard_split(text, max_chars):
    words = text.split()
    chunks, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = word
        else:
            current += " " + word
    if current.strip():
        chunks.append(current.strip())
    return chunks


def get_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def concat_wav_files(file_list, output_path):
    if len(file_list) == 0:
        return False
    if len(file_list) == 1:
        shutil.copy2(file_list[0], output_path)
        return True
    concat_list = output_path + ".concat.txt"
    with open(concat_list, "w") as f:
        for path in file_list:
            f.write(f"file '{os.path.abspath(path)}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
           "-i", concat_list, "-c:a", "pcm_s16le", output_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        os.unlink(concat_list)
    except OSError:
        pass
    return result.returncode == 0


def generate_one_chunk(text, output_path, speaker, language="German"):
    chunk_script = os.path.join(SCRIPT_DIR, "generate_tts_chunk.py")
    cmd = [sys.executable, chunk_script, text, output_path,
           "--speaker", speaker, "--language", language]
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    cpu_time = time.time() - t0
    # Check return code but also check if audio file was created successfully
    if result.returncode != 0:
        # Even if return code is non-zero, the audio may have been generated
        if os.path.isfile(output_path) and os.path.getsize(output_path) > 100:
            return get_duration(output_path), cpu_time
        stderr_snippet = result.stderr[-500:] if result.stderr else "unknown error"
        raise RuntimeError(stderr_snippet)
    stdout = result.stdout.strip()
    for line in reversed(stdout.split('\n')):
        line = line.strip()
        if line.startswith('{') and 'audio_dur' in line:
            data = json.loads(line)
            return data['audio_dur'], cpu_time
    if os.path.isfile(output_path) and os.path.getsize(output_path) > 100:
        return get_duration(output_path), cpu_time
    raise RuntimeError(f"No audio output. stdout: {stdout[-300:]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", type=int, required=True)
    parser.add_argument("--seg", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--speaker", type=str, default="ryan")
    parser.add_argument("--scenes-dir", type=str, default=os.path.join(SCRIPT_DIR, "..", "output", "scenes"))
    parser.add_argument("--audio-dir", type=str, default=os.path.join(SCRIPT_DIR, "..", "output", "audio"))
    args = parser.parse_args()

    scene_path = os.path.join(args.scenes_dir, f"scene_{args.scene:02d}.json")
    with open(scene_path) as f:
        scene = json.load(f)

    segments = scene.get("segments", [])
    seg_dir = os.path.join(args.audio_dir, f"scene_{args.scene:02d}")
    os.makedirs(seg_dir, exist_ok=True)

    seg_indices = range(len(segments)) if args.seg is None else [args.seg]

    for i in seg_indices:
        text = segments[i]["text"]
        out_path = os.path.join(seg_dir, f"seg_{i:02d}.wav")

        if args.resume and os.path.isfile(out_path) and os.path.getsize(out_path) > 1000:
            dur = get_duration(out_path)
            print(f"  Seg {i}: SKIP (exists, {dur:.1f}s)")
            continue

        chunks = split_text_into_chunks(text)
        print(f"  Seg {i} ({len(text)} chars -> {len(chunks)} chunks)", flush=True)

        chunk_files = []
        for ci, chunk_text in enumerate(chunks):
            chunk_path = os.path.join(seg_dir, f"seg_{i:02d}_c{ci}.wav")
            if args.resume and os.path.isfile(chunk_path) and os.path.getsize(chunk_path) > 1000:
                chunk_files.append(chunk_path)
                dur = get_duration(chunk_path)
                print(f"    c{ci}: SKIP ({dur:.1f}s)")
                continue

            print(f"    c{ci} ({len(chunk_text)} chars)...", end=" ", flush=True)
            try:
                audio_dur, cpu_time = generate_one_chunk(chunk_text, chunk_path, args.speaker)
                chunk_files.append(chunk_path)
                print(f"OK {audio_dur:.1f}s/{cpu_time:.0f}s")
            except Exception as e:
                print(f"FAILED ({e})")

        if chunk_files:
            if len(chunk_files) == 1:
                shutil.copy2(chunk_files[0], out_path)
            else:
                concat_wav_files(chunk_files, out_path)
            seg_dur = get_duration(out_path)
            scene["segments"][i]["duration_s"] = round(seg_dur, 2)
            print(f"  Seg {i} DONE: {seg_dur:.1f}s total")

    # Write updated JSON
    with open(scene_path, "w") as f:
        json.dump(scene, f, indent=2, ensure_ascii=False)
    print(f"  JSON updated")


if __name__ == "__main__":
    main()
