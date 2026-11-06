"""Vocabulary the anonymous auth pages print on their seed-packet scene."""

from apps.core.models import SeedInventory
from apps.core.views import EXPIRY_WINDOW_DAYS


def _label(choices, value, fallback_index=0):
    """Return the human label for a model choice, falling back if it is removed."""
    labels = dict(choices)

    if value in labels:
        return labels[value]
    return list(labels.values())[fallback_index]


def scene_taxonomy(request):
    """Expose SeedInventory's real category/unit vocabulary and expiry window."""
    return {
        "scene_taxonomy": {
            "categories": [label for _, label in SeedInventory.CATEGORY_CHOICES],
            "expiry_window_days": EXPIRY_WINDOW_DAYS,
            "front": {
                "category": _label(SeedInventory.CATEGORY_CHOICES, "vegetable"),
                "unit": _label(SeedInventory.UNIT_CHOICES, "packets"),
            },
            "back": {
                "category": _label(SeedInventory.CATEGORY_CHOICES, "herb"),
                "unit": _label(SeedInventory.UNIT_CHOICES, "grams"),
            },
        },
    }
