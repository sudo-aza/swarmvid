#!/usr/bin/env python3
"""
parse_narration.py — Extract narration segments from BLACKBOARD.md and generate
scene JSON files for render_scene.py.

Usage:
    python3 parse_narration.py --blackboard BLACKBOARD.md --output-dir scenes/

Parses the BLACKBOARD's narration section (### Szene N: Title — Subtitle format
with [SN.M] segment markers) and writes one scene_NN.json per scene.

Each output JSON matches the format expected by render_scene.py:
{
  "scene_num": 1,
  "title": "...",
  "subtitle": "...",
  "era": "...",
  "segments": [{"text": "...", "duration_s": 12.0}],
  "sources": [],
  "gradient": ["#1a1a2e", "#16213e", "#0f3460"],
  "accent": "#e94560"
}

Duration defaults to 12s per segment (Producer can adjust after TTS generation).
Era is inferred from scene number.
"""

import argparse
import json
import os
import re
import sys

# Era labels for each scene (from original Scene Breakdown)
ERAS = {
    1: "pre-1100",
    2: "1100-1300",
    3: "1300-1400",
    4: "1400-1500",
    5: "1500-1600",
    6: "1618-1648",
    7: "1648-1680",
    8: "1680-1714",
    9: "1714-1727",
    10: "1727-1760",
    11: "1737-1800",
    12: "1789-1813",
    13: "1814-1830",
    14: "1830-1837",
    15: "1837-1851",
    16: "1851-1866",
    17: "1866-1890",
    18: "1890-1914",
    19: "1914-1918",
    20: "1918-1933",
    21: "1933-1938",
    22: "1939-1945",
    23: "1945-1950",
    24: "1950-1970",
    25: "1950-2000",
    26: "1990-2005",
    27: "2005-present",
    28: "present",
}

# Rotating gradient palettes (one per scene, cycling through 8 distinct looks)
GRADIENTS = [
    ["#1a1a2e", "#16213e", "#0f3460"],
    ["#0d1117", "#1a1f2e", "#2d3561"],
    ["#1b1b2f", "#162447", "#1f4068"],
    ["#2c003e", "#3d0066", "#5c0099"],
    ["#0a0a23", "#141452", "#2b2b81"],
    ["#1a1a2e", "#1f3044", "#2a4a5f"],
    ["#191919", "#2d2d3f", "#404060"],
    ["#0f0c29", "#302b63", "#24243e"],
]

# Accent colors (warm reds/oranges that contrast well against dark gradients)
ACCENTS = [
    "#e94560", "#ff6b6b", "#f39c12", "#e74c3c",
    "#ff7979", "#eb4d4b", "#f0932b", "#e55039",
]


def parse_blackboard(blackboard_path):
    """Parse BLACKBOARD.md and return list of scene dicts with segments."""
    with open(blackboard_path, "r", encoding="utf-8") as f:
        content = f.read()

    scenes = []

    # Match scene headers: ### Szene N: Title (— Subtitle)?
    # Some scenes have em-dash subtitles, some don't
    scene_header_re = re.compile(
        r"^### Szene (\d+): (.+?)(?: — (.+))?$", re.MULTILINE
    )

    # Find narration section start
    narration_start = content.find("## Narration Script")
    if narration_start == -1:
        narration_start = content.find("### Szene 1:")
    if narration_start == -1:
        print("ERROR: Could not find narration section in BLACKBOARD.md", file=sys.stderr)
        sys.exit(1)

    narration = content[narration_start:]

    # Find TODO section end (don't parse into task list)
    todo_start = narration.find("## TODO")
    if todo_start != -1:
        narration = narration[:todo_start]

    headers = list(scene_header_re.finditer(narration))

    for idx, match in enumerate(headers):
        scene_num = int(match.group(1))
        title = match.group(2).strip()
        subtitle = (match.group(3) or "").strip()

        # Get text between this header and next header (or end of narration)
        start = match.end()
        if idx + 1 < len(headers):
            end = headers[idx + 1].start()
        else:
            end = len(narration)

        section = narration[start:end]

        # Extract segments: [SN.M] followed by text until next [SN.M] or blank+header
        segment_re = re.compile(r"\[S" + str(scene_num) + r"\.\d+\]")
        seg_markers = list(segment_re.finditer(section))

        segments = []
        for seg_idx, seg_match in enumerate(seg_markers):
            seg_start = seg_match.end()
            if seg_idx + 1 < len(seg_markers):
                seg_end = seg_markers[seg_idx + 1].start()
            else:
                seg_end = len(section)

            text = section[seg_start:seg_end].strip()
            # Remove leading/trailing whitespace and collapse internal newlines
            text = re.sub(r"\s+", " ", text)
            if text:
                segments.append({"text": text})

        if segments:
            scenes.append({
                "scene_num": scene_num,
                "title": title,
                "subtitle": subtitle,
                "segments": segments,
            })

    return scenes


def build_scene_json(scene, default_duration=12.0):
    """Build the full scene JSON dict matching render_scene.py's expected format."""
    scene_num = scene["scene_num"]
    era = ERAS.get(scene_num, "unknown")
    grad_idx = (scene_num - 1) % len(GRADIENTS)
    acc_idx = (scene_num - 1) % len(ACCENTS)

    # Add default duration to each segment
    segments = []
    for seg in scene["segments"]:
        segments.append({
            "text": seg["text"],
            "duration_s": default_duration,
        })

    return {
        "scene_num": scene_num,
        "title": scene["title"],
        "subtitle": scene["subtitle"],
        "era": era,
        "segments": segments,
        "sources": [],
        "gradient": GRADIENTS[grad_idx],
        "accent": ACCENTS[acc_idx],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Parse BLACKBOARD narration into scene JSON files"
    )
    parser.add_argument("--blackboard", required=True,
                        help="Path to BLACKBOARD.md")
    parser.add_argument("--output-dir", required=True,
                        help="Directory to write scene JSON files")
    parser.add_argument("--default-duration", type=float, default=12.0,
                        help="Default segment duration in seconds (default: 12.0)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    scenes = parse_blackboard(args.blackboard)
    print(f"Parsed {len(scenes)} scenes from {args.blackboard}")

    total_segments = 0
    for scene in scenes:
        scene_json = build_scene_json(scene, args.default_duration)
        total_segments += len(scene_json["segments"])

        filename = f"scene_{scene_json['scene_num']:02d}.json"
        outpath = os.path.join(args.output_dir, filename)
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(scene_json, f, ensure_ascii=False, indent=2)

        # Verify segment lengths (TTS API limit: 1024 chars)
        for seg in scene_json["segments"]:
            char_count = len(seg["text"])
            if char_count > 1024:
                print(f"  WARNING: {filename} segment exceeds 1024 chars ({char_count})")

        print(f"  {filename}: {len(scene_json['segments'])} segments, "
              f"era={scene_json['era']}, title=\"{scene_json['title']}\"")

    print(f"\nTotal: {len(scenes)} scenes, {total_segments} segments")
    print(f"Output: {args.output_dir}/")


if __name__ == "__main__":
    main()
