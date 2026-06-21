#!/usr/bin/env python3
"""add_image_events.py — Add image visual events to scene JSONs for scenes 1-10.

Reads existing images from output/media/, analyzes existing text events
to find non-overlapping positions, and inserts image events into scene JSONs.

Images are placed to avoid overlapping with text events:
- If text events are on the right, images go left
- If text events are center/bottom, images go left or right
- Images are spaced evenly across the scene duration
"""

import json
import os
import sys
import glob

SCENES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "scenes")
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output", "media")


def get_scene_images(scene_num: int) -> list[str]:
    """Get image filenames for a scene, sorted by index."""
    pattern = os.path.join(MEDIA_DIR, f"scene_{scene_num:02d}_*.jpg")
    files = sorted(glob.glob(pattern))
    return [os.path.basename(f) for f in files]


def get_occupied_intervals(events: list[dict]) -> list[tuple[float, float, str]]:
    """Get (start, end, position) for each existing event."""
    occupied = []
    for ev in events:
        t = ev.get("trigger_time", 0)
        d = ev.get("duration", 5.0)
        pos = ev.get("position", "center")
        occupied.append((t, t + d, pos))
    return sorted(occupied, key=lambda x: x[0])


def find_best_position(trigger: float, duration: float,
                       occupied: list[tuple[float, float, str]]) -> str:
    """Find the best position for an image that minimizes overlap with text."""
    img_start = trigger
    img_end = trigger + duration

    # Count overlapping events by position
    pos_conflict = {"left": 0, "right": 0, "center": 0, "bottom": 0}
    for occ_start, occ_end, occ_pos in occupied:
        # Check if intervals overlap
        if img_start < occ_end and img_end > occ_start:
            # This event overlaps with our image
            pos = occ_pos if occ_pos in pos_conflict else "center"
            pos_conflict[pos] += 1

    # Pick position with least conflict, preferring left/right for images
    # Images look better on left or right (not center or bottom)
    left_score = -pos_conflict["left"] - pos_conflict["center"] * 0.5
    right_score = -pos_conflict["right"] - pos_conflict["center"] * 0.5

    return "left" if left_score >= right_score else "right"


def compute_trigger_times(n_images: int, total_dur: float,
                           title_duration: float = 5.0) -> list[float]:
    """Compute evenly-spaced trigger times for images.

    Images start after the title card fades out and are spaced
    evenly across the remaining duration.
    """
    # Start images after title card (5s) + small buffer
    usable_start = title_duration + 2.0
    usable_end = total_dur - 3.0  # Leave room before end
    usable_dur = usable_end - usable_start

    if n_images <= 0:
        return []

    if n_images == 1:
        return [usable_start + usable_dur * 0.5]

    # Space evenly
    spacing = usable_dur / (n_images + 1)
    return [usable_start + spacing * (i + 1) for i in range(n_images)]


def main():
    # Process scenes 1-10
    modified = 0
    total_images_added = 0

    for scene_num in range(1, 11):
        scene_path = os.path.join(SCENES_DIR, f"scene_{scene_num:02d}.json")
        if not os.path.isfile(scene_path):
            print(f"Scene {scene_num:02d}: JSON not found, skipping")
            continue

        images = get_scene_images(scene_num)
        if not images:
            print(f"Scene {scene_num:02d}: No images in media/, skipping")
            continue

        with open(scene_path) as f:
            data = json.load(f)

        # Count existing image events
        existing_img = sum(1 for v in data.get("visual_events", [])
                          if v.get("type") == "image")

        if existing_img >= len(images):
            print(f"Scene {scene_num:02d}: Already has {existing_img} image events, skipping")
            continue

        # Compute scene total duration
        total_dur = sum(s.get("duration_s", 12.0) for s in data.get("segments", []))
        events = data.get("visual_events", [])

        # Compute trigger times
        triggers = compute_trigger_times(len(images), total_dur)

        # Get occupied intervals for conflict detection
        occupied = get_occupied_intervals(events)

        # Create image events
        img_events = []
        for i, (img_file, trigger) in enumerate(zip(images, triggers)):
            # 8-10 second duration per image
            img_dur = 8.0 if len(images) <= 2 else min(10.0, total_dur / len(images))

            # Find best position
            position = find_best_position(trigger, img_dur, occupied)

            # Update occupied intervals for next image
            occupied.append((trigger, trigger + img_dur, position))
            occupied.sort(key=lambda x: x[0])

            img_events.append({
                "type": "image",
                "trigger_time": round(trigger, 1),
                "duration": round(img_dur, 1),
                "src": f"scene_{scene_num:02d}_{i}.jpg" if i < len(images) else images[i],
                "position": position,
                "caption": "",
                "anim": "fade_in",
                "anim_duration": 0.6,
            })

        # Add image events to the scene JSON (merge, keeping existing events)
        data["visual_events"].extend(img_events)

        # Sort all events by trigger_time
        data["visual_events"].sort(key=lambda e: e.get("trigger_time", 0))

        # Write back
        with open(scene_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        n_added = len(img_events)
        modified += 1
        total_images_added += n_added

        print(f"Scene {scene_num:02d}: Added {n_added} image events "
              f"({', '.join(e['src'] for e in img_events)})")

    print(f"\nDone: {modified} scenes modified, {total_images_added} image events added")


if __name__ == "__main__":
    main()
