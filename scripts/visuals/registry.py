"""Treatment registry — maps treatment names to renderer classes."""

from __future__ import annotations


class TreatmentRegistry:
    """Central registry for scene visual treatments."""

    def __init__(self) -> None:
        self._treatments: dict[str, type] = {}

    def register(self, name: str):
        """Decorator to register a treatment class by name."""
        def decorator(cls):
            self._treatments[name] = cls
            return cls
        return decorator

    def get(self, name: str):
        """Get a treatment class by name. Falls back to 'default'."""
        return self._treatments.get(name, self._treatments.get("default"))

    def list_treatments(self) -> list[str]:
        return list(self._treatments.keys())
