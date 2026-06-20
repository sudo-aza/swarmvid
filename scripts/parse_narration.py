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
  "facts": ["1150: First mention as Honovere", "772–804: Saxon Wars"],
  "gradient": ["#1a1a2e", "#16213e", "#0f3460"],
  "accent": "#e94560"
}

Duration defaults to 12s per segment (Producer can adjust after TTS generation).
Era is inferred from scene number.
Facts are auto-extracted from narration text for lower-third banners.
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

# Visual treatments per scene — maps scene numbers to treatment names.
# Treatments: default, title_card, map_focus, fullscreen_text, stark
# Unlisted scenes fall back to "default".
VISUAL_TREATMENTS = {
    1: "title_card",     # Opening — dramatic full-screen intro
    2: "default",        # Medieval foundations — map + narration
    3: "map_focus",      # Trade routes geography — full map focus
    4: "default",        # Medieval Hannover — map + narration
    5: "default",        # Medieval trade — map + narration
    6: "default",        # Renaissance — map + narration
    7: "map_focus",      # Infrastructure/rail — full map focus
    8: "title_card",     # Baroque intro — dramatic transition
    9: "stark",          # Thirty Years' War — harsh, dramatic
    10: "stark",         # War aftermath — harsh, dramatic
    11: "fullscreen_text", # Post-war reflection — typographic focus
    12: "default",        # Baroque rebuilding — map + narration
    13: "default",        # Baroque culture — map + narration
    14: "title_card",     # Electorate era intro — dramatic transition
    15: "default",        # Electoral expansion — map + narration
    16: "map_focus",      # Kingdom expansion — full map focus
    17: "fullscreen_text", # Napoleonic era — typographic focus
    18: "title_card",     # Kingdom of Hannover intro — dramatic
    19: "default",        # Kingdom politics — map + narration
    20: "default",        # Industrial era — map + narration
    21: "default",        # Constitutional era — map + narration
    22: "fullscreen_text", # Prussian annexation — typographic focus
    23: "stark",          # WWI impact — harsh, dramatic
    24: "stark",          # Weimar instability — harsh, dramatic
    25: "stark",          # Nazi era — harsh, dramatic
    26: "stark",          # WWII destruction — harsh, dramatic
    27: "title_card",     # Post-war rebirth intro — dramatic
    28: "fullscreen_text", # Modern Hannover — typographic reflection
}


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

        # Extract segments: [SN.M] followed by text until next [SN.M] or SOURCES:
        segment_re = re.compile(r"\[S" + str(scene_num) + r"\.\d+\]")
        seg_markers = list(segment_re.finditer(section))

        segments = []
        sources = []
        for seg_idx, seg_match in enumerate(seg_markers):
            seg_start = seg_match.end()
            if seg_idx + 1 < len(seg_markers):
                seg_end = seg_markers[seg_idx + 1].start()
            else:
                seg_end = len(section)

            text = section[seg_start:seg_end].strip()

            # Strip SOURCES: section and extract source lines
            sources_match = re.search(r"\nSOURCES:\s*\n", text)
            if sources_match:
                sources_block = text[sources_match.end():]
                text = text[:sources_match.start()]
                # Extract source lines (URLs, book citations)
                for src_line in sources_block.strip().split("\n"):
                    src_line = src_line.strip().lstrip("- ")
                    if src_line:
                        # Remove leading citation markers like "[1] "
                        src_line = re.sub(r"^\[\d+\]\s*", "", src_line)
                        if src_line:
                            sources.append(src_line)

            # Remove inline citation markers [1], [2], etc.
            text = re.sub(r"\[\d+\]", "", text)

            # Remove leading/trailing whitespace and collapse internal newlines
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                segments.append({"text": text})

        # Deduplicate sources
        sources = list(dict.fromkeys(sources))

        if segments:
            scenes.append({
                "scene_num": scene_num,
                "title": title,
                "subtitle": subtitle,
                "segments": segments,
                "sources": sources,
            })

    return scenes


def _clean_fact(text):
    """Clean a fact string: remove trailing punctuation, normalize whitespace."""
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.rstrip('.,;:!?')
    text = text.strip()
    # Remove leading articles/conjunctions that look wrong
    text = re.sub(r'^(und|oder|sowie|aber|doch|denn)\s+', '', text)
    return text


def extract_facts(segments_text):
    """Extract concise fact strings from narration text for lower-third banners.

    Looks for sentences containing years, dates, and key events.
    Returns list of fact strings (max 75 chars each, max 8 per scene).
    """
    facts = []
    seen = set()

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', segments_text)

    # Patterns that indicate factual content suitable for lower-third display
    year_patterns = [
        # "Im Jahr YYYY" + nearby text
        re.compile(r'Im\s+Jahr(?:e)?\s+(\d{3,4})[,.]?\s+(.{10,80})', re.IGNORECASE),
        # "Zwischen YYYY und YYYY" date ranges
        re.compile(r'(?:Zwischen|zwischen)\s+(\d{3,4})\s+und\s+(\d{3,4})\s+(.{10,80})'),
        # "von YYYY bis YYYY"
        re.compile(r'von\s+(\d{3,4})\s+bis\s+(\d{3,4})\s+(.{10,80})'),
        # "YYYY wurde/war/erhielt" (year as subject start)
        re.compile(r'(?:^|,\s)(\d{3,4})\s+(wurde|war|erhielt|erschien|folgte|begann|endete|startete|wurden|gründete|baute|errichtete)\s+(.{10,80})', re.MULTILINE),
        # "Am DD. Monat YYYY" full dates
        re.compile(r'Am\s+\d{1,2}\.\s+\w+\s+(\d{3,4})\s+(.{10,80})'),
        # "in YYYY" (generic, lower priority — placed later)
        re.compile(r'(?:^|,\s)in\s+(\d{3,4})\s+(.{10,80})', re.IGNORECASE | re.MULTILINE),
    ]

    # Broad pattern: any sentence with a standalone 3-4 digit year
    year_any = re.compile(r'(?<!\d)(\d{3,4})(?!\d)')

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue

        fact = None

        # Try specific patterns first (higher quality)
        for pat in year_patterns:
            m = pat.search(sentence)
            if m:
                groups = [g for g in m.groups() if g is not None]
                if len(groups) >= 2:
                    date_part = groups[0]
                    desc_part = groups[1].strip()
                    # If second group is also a year (date range), combine
                    if re.match(r'^\d{3,4}$', groups[1]) and len(groups) >= 3:
                        date_part = f"{groups[0]}–{groups[1]}"
                        desc_part = groups[2].strip()
                    # Truncate at sentence/clause boundary
                    desc_part = re.split(r'[,;.]\s', desc_part)[0].strip()
                    # Remove trailing conjunctions
                    desc_part = re.sub(r'\s+(und|oder|sowie|aber|doch)\s+.*$', '', desc_part)
                    desc_part = _clean_fact(desc_part)
                    if len(desc_part) >= 8:
                        fact = f"{date_part}: {desc_part}"
                break

        # Fallback: any sentence with a year, extract a concise version
        if not fact:
            years_in_sent = year_any.findall(sentence)
            if years_in_sent:
                for y in years_in_sent:
                    yr = int(y)
                    if 500 <= yr <= 2100:
                        clauses = re.split(r'[,;]\s', sentence)
                        for clause in clauses:
                            if str(yr) in clause:
                                idx = clause.find(str(yr))
                                start = max(0, idx - 15)
                                end = min(len(clause), idx + 55)
                                fact_base = clause[start:end].strip()
                                # Fix word boundaries: strip leading/trailing partial words
                                if start > 0 and not fact_base[0].isupper():
                                    first_space = fact_base.find(' ')
                                    if first_space > 0:
                                        fact_base = fact_base[first_space + 1:]
                                fact_base = _clean_fact(fact_base)
                                if len(fact_base) > 75:
                                    fact_base = fact_base[:72] + "..."
                                if len(fact_base) >= 25:
                                    fact = fact_base
                                break
                        if fact:
                            break

        if fact:
            fact = _clean_fact(fact)
            # Enforce max length
            if len(fact) > 75:
                fact = fact[:72] + "..."
            # Skip low-quality facts
            if fact.startswith('NOTE:'):
                continue
            # Skip fragments that are just a number or too short
            if len(fact) < 15:
                continue
            # Skip "In den 1920er/1930er Jahren" style (decade ranges without specific info)
            if re.match(r'^In\s+den\s+\d{4}er\s+Jahren', fact):
                continue
            if fact not in seen:
                seen.add(fact)
                facts.append(fact)

    return facts[:8]


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

    # Use sources from parsed narration (or empty if none)
    sources = scene.get("sources", [])

    # Extract facts from all segment texts for lower-third banners
    all_text = " ".join(seg["text"] for seg in scene["segments"])
    facts = extract_facts(all_text)

    # Determine visual treatment
    treatment = VISUAL_TREATMENTS.get(scene_num, "default")

    return {
        "scene_num": scene_num,
        "title": scene["title"],
        "subtitle": scene["subtitle"],
        "era": era,
        "segments": segments,
        "sources": sources,
        "facts": facts,
        "gradient": GRADIENTS[grad_idx],
        "accent": ACCENTS[acc_idx],
        "visual_treatment": treatment,
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
