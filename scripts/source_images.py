#!/usr/bin/env python3
"""
source_images.py — Download historical images per scene via z-ai image-search CLI.

For each scene, searches for 2-3 historically-relevant images, downloads them
to output/media/, and injects image-type visual events into scene JSONs.

Usage:
    python3 scripts/source_images.py [--scene N] [--dry-run] [--count N]

Queries are tailored to each scene's historical content. Images are saved as
scene_{N}_{idx}.jpg. Events are appended to each scene JSON's visual_events array.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
MEDIA_DIR = os.path.join(OUTPUT_DIR, "media")
SCENES_DIR = os.path.join(OUTPUT_DIR, "scenes")

# Per-scene search queries — historically relevant image descriptions.
# Format: [(query, caption, trigger_time, position, duration), ...]
SCENE_QUERIES = {
    1: [
        ("Battle of Teutoburg Forest 9 AD Varus historical painting",
         "Varusschlacht 9 n. Chr.", 8.0, "left", 12.0),
        ("Germanic tribes ancient Germania map",
         "Germanien — Karte der germanischen Stämme", 25.0, "right", 10.0),
        ("Bronze age urnfield Lower Saxony archaeological finds",
         "Urnengrabfunde in Niedersachsen", 45.0, "bottom-left", 8.0),
    ],
    2: [
        ("medieval Hannover Leine river 12th century illustration",
         "Hannover am Leineufer — 12. Jahrhundert", 5.0, "left", 12.0),
        ("Henry the Lion Duke of Saxony medieval portrait",
         "Heinrich der Löwe — Herzog von Sachsen", 30.0, "right", 10.0),
        ("medieval market town trading post historical",
         "Mittelalterlicher Marktplatz", 55.0, "bottom-right", 8.0),
    ],
    3: [
        ("Black Death plague 1347 Europe medieval painting",
         "Der Schwarze Tod 1347", 10.0, "left", 12.0),
        ("Hanover Marktkirche church tower 97m medieval",
         "Marktkirche Hannover — 97m Turm", 30.0, "right", 10.0),
        ("medieval guild hall German town historical illustration",
         "Gildehaus — Mittelalterliches Hannover", 55.0, "bottom-left", 8.0),
    ],
    4: [
        ("Hildesheim medieval city 15th century historical",
         "Hildesheim — 15. Jahrhundert", 5.0, "left", 12.0),
        ("Gutenberg printing press 1440 historical",
         "Gutenberg-Druckpresse 1440", 25.0, "right", 10.0),
        ("Pre-Reformation Hanover church medieval illustration",
         "Kirche Hannover vor der Reformation", 50.0, "bottom-right", 8.0),
    ],
    5: [
        ("Reformation Martin Luther 1517 Wittenberg historical painting",
         "Martin Luther — 1517 Reformation", 8.0, "left", 12.0),
        ("Renaissance city Hannover 16th century historical",
         "Hannover im 16. Jahrhundert", 30.0, "right", 10.0),
        ("Guelph dynasty coat of arms historical",
         "Wappen der Welfen", 50.0, "bottom-left", 8.0),
    ],
    6: [
        ("Thirty Years War 1618 battle historical painting",
         "Dreißigjähriger Krieg — Schlacht", 8.0, "left", 12.0),
        ("General Tilly Catholic League commander portrait",
         "General Tilly", 28.0, "right", 10.0),
        ("17th century destroyed German city war devastation",
         "Zerstörte deutsche Stadt im Krieg", 50.0, "bottom-left", 8.0),
    ],
    7: [
        ("Duke George William of Calenberg portrait 17th century",
         "Herzog Georg Wilhelm von Calenberg", 8.0, "left", 12.0),
        ("Leineschloss Hannover castle 17th century historical",
         "Leineschloss Hannover", 30.0, "right", 10.0),
        ("17th century Baroque garden Herrenhausen",
         "Barockgarten Herrenhausen", 50.0, "bottom-right", 8.0),
    ],
    8: [
        ("Ernest Augustus Elector of Hanover portrait",
         "Kurfürst Ernst August", 10.0, "left", 12.0),
        ("Herrenhausen Gardens Hanover Baroque garden historical",
         "Großer Garten Herrenhausen", 30.0, "right", 12.0),
        ("Gottfried Wilhelm Leibniz philosopher portrait",
         "Gottfried Wilhelm Leibniz", 50.0, "bottom-left", 10.0),
    ],
    9: [
        ("King George I of Great Britain portrait coronation",
         "König Georg I. — Krönung", 8.0, "left", 12.0),
        ("Hanoverian succession British monarchy 1714 historical",
         "Hannoversche Thronfolge", 30.0, "right", 10.0),
    ],
    10: [
        ("Baroque architecture Hannover 18th century historical",
         "Barockarchitektur Hannover", 8.0, "left", 12.0),
        ("Royal court Hanover 18th century palace",
         "Königlicher Hof Hannover", 28.0, "right", 10.0),
    ],
}


def search_images(query: str, count: int = 1, gl: str = "us") -> list[dict]:
    """Search for images using z-ai image-search CLI. Returns list of results."""
    try:
        cmd = [
            "z-ai", "image-search",
            "--query", query,
            "--count", str(count),
            "--gl", gl,
            "--no-rank",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        stdout = result.stdout
        # CLI outputs progress lines before JSON; find first '{'
        json_start = stdout.find("{")
        if json_start < 0:
            print(f"  ⚠ No JSON in response for: {query[:50]}...")
            return []
        data = json.loads(stdout[json_start:])
        if data.get("success") and data.get("results"):
            return data["results"]
        return []
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"  ⚠ Search failed: {e}")
        return []


def download_image(url: str, dest_path: str) -> bool:
    """Download an image from URL to dest_path. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            with open(dest_path, "wb") as f:
                f.write(resp.read())
        # Verify it's a valid image
        from PIL import Image
        img = Image.open(dest_path)
        img.verify()
        return True
    except Exception as e:
        print(f"  ⚠ Download failed: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False


def ensure_dirs():
    """Create output directories if they don't exist."""
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(SCENES_DIR, exist_ok=True)


def generate_scene_jsons():
    """Generate scene JSONs from narration_v2.md using parse_narration."""
    sys.path.insert(0, SCRIPT_DIR)
    try:
        import parse_narration as pn
    except ImportError:
        print("ERROR: Cannot import parse_narration.py")
        return []

    narration_path = os.path.join(PROJECT_ROOT, "narration_v2.md")
    if not os.path.isfile(narration_path):
        print(f"ERROR: {narration_path} not found")
        return []

    scenes = pn.parse_blackboard(narration_path)
    if not scenes:
        print("ERROR: No scenes parsed from narration")
        return []

    # Write scene JSONs
    for scene in scenes:
        path = os.path.join(SCENES_DIR, f"scene_{scene['scene_num']:02d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(scene, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(scenes)} scene JSONs in {SCENES_DIR}/")
    return scenes


def load_scene_json(scene_num: int) -> dict | None:
    """Load a scene JSON file."""
    path = os.path.join(SCENES_DIR, f"scene_{scene_num:02d}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_scene_json(scene_num: int, data: dict):
    """Save a scene JSON file."""
    path = os.path.join(SCENES_DIR, f"scene_{scene_num:02d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def process_scene(scene_num: int, count: int = 3, dry_run: bool = False):
    """Download images for one scene and inject events into its JSON."""
    queries = SCENE_QUERIES.get(scene_num, [])
    if not queries:
        print(f"Scene {scene_num}: No queries defined, skipping.")
        return 0

    # Load or create scene JSON
    scene = load_scene_json(scene_num)
    if scene is None:
        print(f"Scene {scene_num}: No scene JSON found. Generate first with parse.")
        return 0

    ensure_dirs()
    events = scene.get("visual_events", [])
    downloaded = 0

    for i, (query, caption, trigger_time, position, duration) in enumerate(queries):
        filename = f"scene_{scene_num:02d}_{i}.jpg"
        dest_path = os.path.join(MEDIA_DIR, filename)
        src_path = filename  # filename only; media_base resolves to output/media/

        # Skip if already downloaded
        if os.path.isfile(dest_path):
            print(f"  ✓ [{scene_num}.{i}] Already exists: {filename}")
            downloaded += 1
            # Still add event if not already present
            event_exists = any(
                e.get("type") == "image" and e.get("src") == src_path
                for e in events
            )
            if not event_exists:
                events.append({
                    "type": "image",
                    "trigger_time": trigger_time,
                    "duration": duration,
                    "src": src_path,
                    "caption": caption,
                    "position": position,
                    "anim": "fade_in",
                    "anim_duration": 0.6,
                })
            continue

        if dry_run:
            print(f"  [DRY] Scene {scene_num}, image {i}: {query[:60]}...")
            downloaded += 1
            continue

        print(f"  [{scene_num}.{i}] Searching: {query[:60]}...")
        results = search_images(query, count=1)
        if not results:
            print(f"    ⚠ No results. Skipping.")
            continue

        img_url = results[0].get("original_url", "")
        if not img_url:
            continue

        print(f"    Downloading...")
        if download_image(img_url, dest_path):
            size_kb = os.path.getsize(dest_path) // 1024
            print(f"    ✓ Saved: {filename} ({size_kb} KB)")
            events.append({
                "type": "image",
                "trigger_time": trigger_time,
                "duration": duration,
                "src": src_path,
                "caption": caption,
                "position": position,
                "anim": "fade_in",
                "anim_duration": 0.6,
            })
            downloaded += 1
        else:
            print(f"    ✗ Download failed for {query[:50]}...")

    if downloaded > 0:
        scene["visual_events"] = events
        save_scene_json(scene_num, scene)
        print(f"  Scene {scene_num}: {downloaded} image events added.")

    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Download historical images per scene.")
    parser.add_argument("--scene", "-s", type=int, default=0,
                        help="Process only this scene number (0 = all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without downloading")
    parser.add_argument("--count", "-c", type=int, default=1,
                        help="Number of images to download per query (default 1)")
    args = parser.parse_args()

    ensure_dirs()

    # Ensure scene JSONs exist
    if not os.listdir(SCENES_DIR):
        print("No scene JSONs found. Generating from narration_v2.md...")
        generate_scene_jsons()

    # Determine which scenes to process
    if args.scene > 0:
        scene_nums = [args.scene]
    else:
        # Process all scenes that have queries defined
        scene_nums = sorted(SCENE_QUERIES.keys())

    total = 0
    for sn in scene_nums:
        print(f"\n{'='*60}")
        print(f"Scene {sn}")
        print(f"{'='*60}")
        total += process_scene(sn, count=args.count, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print(f"Done. {total} images {'would be ' if args.dry_run else ''}downloaded.")
    print(f"Images in: {MEDIA_DIR}/")
    print(f"Events in: {SCENES_DIR}/")


if __name__ == "__main__":
    main()
