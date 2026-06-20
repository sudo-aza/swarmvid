"""swarmvid visual rendering library.

Shared utilities for scene treatments. Each treatment is a module under
visuals/treatments/ that registers itself with the global registry.

Usage in render_scene.py:
    from visuals import registry
    treatment_cls = registry.get(scene.get("visual_treatment", "default"))
    treatment = treatment_cls()
    treatment.prepare(ctx)
    img = treatment.render_frame(ctx, frame_idx, ...)
"""

from visuals.registry import TreatmentRegistry
from visuals.treatments import register_all

# Global singleton
registry = TreatmentRegistry()

# Register all built-in treatments
register_all(registry)

__all__ = ["registry"]
