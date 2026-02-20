"""
ocr_items.py — STUB

Real implementation pending.
"""

from dataclasses import dataclass


@dataclass
class Item:
    name: str
    classification: str


def read_items(image_path: str) -> list[Item]:
    """Scan a loot screenshot and return all visible items. NOT YET IMPLEMENTED."""
    return []
