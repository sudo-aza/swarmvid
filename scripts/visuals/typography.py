"""Typography utilities — text wrapping, word reveal, lower-thirds, title cards."""

from __future__ import annotations

import math
from PIL import Image, ImageDraw, ImageFont


def prewrap_text(segments: list[dict], font: ImageFont.FreeTypeFont,
                 max_width: int) -> list[dict]:
    """Pre-wrap all segment text into word lists. Returns list of dicts with 'words' key."""
    result = []
    dummy = ImageDraw.Draw(Image.new("L", (1, 1)))
    for seg in segments:
        words = seg.get("text", "").split()
        # Also wrap into lines for reference
        lines = []
        current = ""
        for word in words:
            test = current + (" " if current else "") + word
            bbox = dummy.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width:
                if current:
                    lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        result.append({"words": words, "lines": lines})
    return result


def draw_word_reveal(od: ImageDraw.ImageDraw, wrapped_seg: dict,
                     progress: float, x: int, y: int, max_w: int,
                     max_lines: int, line_height: int, font_size: int,
                     font: ImageFont.FreeTypeFont, body_font: ImageFont.FreeTypeFont,
                     text_color: tuple = (240, 240, 240, 255),
                     dummy_draw: ImageDraw.ImageDraw = None) -> int:
    """Draw word-by-word text reveal. Returns the Y position after last drawn line."""
    words = wrapped_seg["words"]
    total_words = len(words)
    words_to_show = max(1, min(total_words, int(progress * total_words * 1.5)))

    # Re-wrap revealed words
    revealed_lines = []
    current = ""
    for word in words[:words_to_show]:
        test = current + (" " if current else "") + word
        bbox = dummy_draw.textbbox((0, 0), test, font=body_font)
        if bbox[2] - bbox[0] > max_w:
            if current:
                revealed_lines.append(current)
            current = word
        else:
            current = test
    if current:
        revealed_lines.append(current)

    # Scroll
    if len(revealed_lines) > max_lines:
        scroll_start = len(revealed_lines) - max_lines
        visible = revealed_lines[scroll_start:]
    else:
        visible = revealed_lines

    for i, line in enumerate(visible):
        ly = y + i * line_height
        od.text((x, ly), line, fill=text_color, font=body_font)

    return y + len(visible) * line_height


def draw_cursor_blink(od: ImageDraw.ImageDraw, wrapped_seg: dict,
                      progress: float, x: int, y: int, max_w: int,
                      max_lines: int, line_height: int, font_size: int,
                      accent: tuple, frame_idx: int,
                      body_font: ImageFont.FreeTypeFont,
                      dummy_draw: ImageDraw.ImageDraw) -> None:
    """Draw blinking cursor at end of revealed text."""
    words = wrapped_seg["words"]
    total_words = len(words)
    words_to_show = max(1, min(total_words, int(progress * total_words * 1.5)))

    if words_to_show >= total_words:
        return

    # Re-wrap
    revealed_lines = []
    current = ""
    for word in words[:words_to_show]:
        test = current + (" " if current else "") + word
        bbox = dummy_draw.textbbox((0, 0), test, font=body_font)
        if bbox[2] - bbox[0] > max_w:
            if current:
                revealed_lines.append(current)
            current = word
        else:
            current = test
    if current:
        revealed_lines.append(current)

    if len(revealed_lines) > max_lines:
        visible = revealed_lines[len(revealed_lines) - max_lines:]
    else:
        visible = revealed_lines

    cursor_visible = int(frame_idx * 0.1) % 2 == 0
    if cursor_visible and visible:
        last_line = visible[-1]
        bbox = dummy_draw.textbbox((0, 0), last_line, font=body_font)
        cursor_x = x + (bbox[2] - bbox[0]) + 4
        cursor_y = y + (len(visible) - 1) * line_height
        od.rectangle([(cursor_x, cursor_y + 2), (cursor_x + 2, cursor_y + font_size)],
                     fill=(*accent[:3], 200))


# ── Lower-Third Banner ──────────────────────────────────────────────────────────
LOWER_THIRD_H = 44
LOWER_THIRD_FONT_SIZE = 20
LOWER_THIRD_SLIDE_FRAMES = 12
LOWER_THIRD_HOLD_FRAMES = 48
LOWER_THIRD_GAP_FRAMES = 24


def get_lower_third_state(frame_idx: int, facts: list[str]):
    """Compute which fact banner to show and animation progress.
    Returns (fact_text, slide_progress, visible)."""
    if not facts:
        return None, None, False

    total_cycle = LOWER_THIRD_SLIDE_FRAMES + LOWER_THIRD_HOLD_FRAMES + LOWER_THIRD_GAP_FRAMES
    fact_idx = (frame_idx // total_cycle) % len(facts)
    cycle_pos = frame_idx % total_cycle

    if cycle_pos < LOWER_THIRD_SLIDE_FRAMES:
        slide_t = cycle_pos / LOWER_THIRD_SLIDE_FRAMES
        slide_t = 1.0 - (1.0 - slide_t) ** 3  # ease-out cubic
        return facts[fact_idx], slide_t, True
    elif cycle_pos < LOWER_THIRD_SLIDE_FRAMES + LOWER_THIRD_HOLD_FRAMES:
        return facts[fact_idx], 1.0, True
    else:
        return None, None, False


def draw_lower_third_banner(od: ImageDraw.ImageDraw, fact_text: str,
                            slide_progress: float, accent: tuple,
                            fonts: dict, x_start: int, y_pos: int,
                            max_width: int = 620) -> None:
    """Draw a slide-in lower-third fact banner."""
    if slide_progress <= 0:
        return
    from visuals.colors import alpha_color
    banner_h = LOWER_THIRD_H

    bbox = od.textbbox((0, 0), fact_text, font=fonts["lower_third"])
    text_w = bbox[2] - bbox[0]
    content_w = min(text_w + 50, max_width)

    offset_x = int((1.0 - slide_progress) * -content_w)
    draw_x = x_start + offset_x

    od.rounded_rectangle(
        [(draw_x, y_pos), (draw_x + content_w, y_pos + banner_h)],
        radius=4, fill=(0, 0, 0, 180)
    )
    od.rectangle(
        [(draw_x, y_pos + 4), (draw_x + 3, y_pos + banner_h - 4)],
        fill=alpha_color(accent, 220)
    )
    od.text((draw_x + 12, y_pos + (banner_h - LOWER_THIRD_FONT_SIZE) // 2 - 1),
            fact_text,
            fill=alpha_color((230, 230, 235), 230),
            font=fonts["lower_third"])


# ── Source Watermark ──────────────────────────────────────────────────────────
SOURCE_WATERMARK_MAX_ALPHA = 150


def draw_source_watermark(od: ImageDraw.ImageDraw, sources: list[str],
                          accent: tuple, fonts: dict,
                          w: int, y_base: int) -> None:
    """Draw persistent semi-transparent source citation watermark in bottom-right."""
    if not sources:
        return
    from visuals.colors import alpha_color
    lines = sources[:2]
    font = fonts["tiny"]

    max_tw = 0
    for line in lines:
        bbox = od.textbbox((0, 0), line, font=font)
        max_tw = max(max_tw, bbox[2] - bbox[0])

    line_h = 16
    box_w = max_tw + 16
    box_h = len(lines) * line_h + 10
    box_x = w - box_w - 10
    box_y = y_base - box_h + 5

    od.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=3, fill=(0, 0, 0, 100)
    )
    od.line([(box_x + 3, box_y), (box_x + box_w - 3, box_y)],
            fill=alpha_color(accent, 100), width=1)

    for i, line in enumerate(lines):
        od.text((box_x + 8, box_y + 5 + i * line_h), line,
                fill=alpha_color((170, 170, 175), SOURCE_WATERMARK_MAX_ALPHA),
                font=font)
