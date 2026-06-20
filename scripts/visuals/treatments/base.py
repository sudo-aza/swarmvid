"""Base class for all scene treatments."""

from __future__ import annotations

from dataclasses import dataclass, field
from PIL import Image, ImageDraw


@dataclass
class RenderContext:
    """Shared rendering state passed to every treatment per-frame."""
    w: int = 1280
    h: int = 720
    fps: int = 24
    fonts: dict = field(default_factory=dict)
    accent_rgb: tuple = (233, 69, 96)
    scene: dict = field(default_factory=dict)
    scene_num: int = 1
    total_scenes: int = 28
    # Pre-computed assets (populated by treatment's prepare() or main loop)
    bg_composited: Image.Image | None = None
    bg_rgba: Image.Image | None = None
    particles: list = field(default_factory=list)
    wrapped: list = field(default_factory=list)
    dummy_draw: ImageDraw.ImageDraw = field(
        default_factory=lambda: ImageDraw.Draw(Image.new("L", (1, 1)))
    )
    # Extra per-treatment state
    extra: dict = field(default_factory=dict)


class TreatmentBase:
    """Abstract base for scene visual treatments.

    Subclasses must implement:
      - prepare(ctx) — called once before rendering starts
      - render_frame(ctx, frame_idx, total_frames, seg_idx, seg_progress, cross_fade) — called per frame

    The prepare() method should set up any pre-computed assets on ctx.extra.
    """

    # Treatment metadata
    name: str = "base"
    description: str = ""

    def prepare(self, ctx: RenderContext) -> None:
        """Called once before rendering. Pre-compute expensive assets here."""
        pass

    def render_frame(self, ctx: RenderContext, frame_idx: int,
                     total_frames: int, seg_idx: int,
                     seg_progress: float, cross_fade: float) -> Image.Image:
        """Render one frame. Must return an RGB PIL Image.

        Args:
            ctx: Shared render context with fonts, assets, scene data
            frame_idx: Current frame number (0-based)
            total_frames: Total frames in this scene
            seg_idx: Current narration segment index
            seg_progress: Progress within current segment (0.0-1.0)
            cross_fade: Cross-segment fade alpha (0.0-1.0)
        """
        raise NotImplementedError


def draw_global_overlays(ctx: RenderContext, frame_idx: int,
                         total_frames: int) -> Image.Image:
    """Draw global overlays that appear on every frame regardless of treatment:
    timeline bar, thin progress bar at very bottom."""
    from visuals.colors import alpha_color
    from visuals.timeline import draw_timeline_bar

    progress = frame_idx / max(total_frames - 1, 1)
    overlay = Image.new("RGBA", (ctx.w, ctx.h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(overlay)

    # Historical timeline bar
    draw_timeline_bar(gd, ctx.scene_num, ctx.total_scenes,
                       ctx.accent_rgb, ctx.fonts, ctx.w, ctx.h)

    # Thin progress bar at very bottom
    gd.rectangle([(0, ctx.h - 3), (ctx.w, ctx.h)], fill=(30, 30, 30, 150))
    gd.rectangle([(0, ctx.h - 3), (int(ctx.w * progress), ctx.h)],
                fill=alpha_color(ctx.accent_rgb, 200))

    return overlay
