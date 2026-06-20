"""Scene visual treatments.

Each treatment defines a unique visual style for rendering a scene.
Treatments are registered via the global registry in visuals/__init__.py.

To create a new treatment:
  1. Create a file here (e.g. my_treatment.py)
  2. Define a class that subclasses TreatmentBase
  3. Add it to the TREATMENTS dict below with @registry.register decorator
"""

# Import base first (no circular dep)
from visuals.treatments.base import TreatmentBase, RenderContext, draw_global_overlays


def register_all(reg):
    """Register all treatments with the given registry instance.
    Called from visuals/__init__.py after registry is created."""
    from visuals.treatments.default_split import DefaultSplitTreatment
    from visuals.treatments.title_card_full import TitleCardFullTreatment
    from visuals.treatments.map_focus import MapFocusTreatment
    from visuals.treatments.fullscreen_text import FullscreenTextTreatment
    from visuals.treatments.stark_minimal import StarkMinimalTreatment

    reg.register("default")(DefaultSplitTreatment)
    reg.register("title_card")(TitleCardFullTreatment)
    reg.register("map_focus")(MapFocusTreatment)
    reg.register("fullscreen_text")(FullscreenTextTreatment)
    reg.register("stark")(StarkMinimalTreatment)


__all__ = ["register_all", "TreatmentBase", "RenderContext", "draw_global_overlays"]
