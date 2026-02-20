"""
test_ocr.py

TDD tests for the to-be-written ocr_items module.

Expected API
------------
    from ocr_items import read_items

    items = read_items("path/to/screenshot.png")
    # Returns list of Item(name: str, classification: str)
    # classification is one of: Normal, Magic, Rare, Unique, Set, Grey, Rune

These tests will all FAIL until ocr_items.py is implemented. That's the point.
"""

import os
from collections import Counter

import pytest

from ocr_items import read_items  # noqa: E402 — does not exist yet

CASES_DIR = os.path.join(os.path.dirname(__file__), "test_cases")


# ---------------------------------------------------------------------------
# Case 1 — loot_20260219_120326.png
#
# 7 items: 2× Normal potions, 1 Rune, 1 Normal potion, 1 Rare belt,
#          1 Normal gold pile, 1 Rare javelin.
# ---------------------------------------------------------------------------

CASE1_IMAGE = os.path.join(CASES_DIR, "1", "loot_20260219_120326.png")
CASE1_ITEMS = [
    ("Super Mana Potion",        "Normal"),
    ("Full Rejuvination Potion", "Normal"),
    ("Shael Rune",               "Rune"),
    ("Super Mana Potion",        "Normal"),
    ("Demonhide Sash",           "Rare"),
    ("779 Gold",                 "Normal"),
    ("Pilum",                    "Rare"),
]


@pytest.fixture(scope="module")
def case1():
    return read_items(CASE1_IMAGE)


def test_case1_item_count(case1):
    assert len(case1) == len(CASE1_ITEMS)


def test_case1_item_names(case1):
    expected = Counter(name for name, _ in CASE1_ITEMS)
    actual   = Counter(item.name for item in case1)
    assert actual == expected


def test_case1_item_classifications(case1):
    expected = Counter(cls for _, cls in CASE1_ITEMS)
    actual   = Counter(item.classification for item in case1)
    assert actual == expected


def test_case1_rune(case1):
    runes = [item for item in case1 if item.classification == "Rune"]
    assert len(runes) == 1
    assert runes[0].name == "Shael Rune"


def test_case1_rare_items(case1):
    rares = sorted(item.name for item in case1 if item.classification == "Rare")
    assert rares == ["Demonhide Sash", "Pilum"]


# ---------------------------------------------------------------------------
# Case 2 — run_20260219_145645.png
#
# 9 items: 4× Normal (potions/gem/shield), 2× Normal gold piles,
#          1 Magic weapon, 1 Unique armor, 1 Grey armor.
# ---------------------------------------------------------------------------

CASE2_IMAGE = os.path.join(CASES_DIR, "2", "run_20260219_145645.png")
CASE2_ITEMS = [
    ("796 Gold",             "Normal"),
    ("Super Healing Potion", "Normal"),
    ("Flawless Amethyst",    "Normal"),
    ("Super Mana Potion",    "Normal"),
    ("Halberd",              "Magic"),
    ("Luna",                 "Normal"),
    ("Greaves",              "Unique"),
    ("827 Gold",             "Normal"),
    ("Breast Plate",         "Grey"),
]


@pytest.fixture(scope="module")
def case2():
    return read_items(CASE2_IMAGE)


def test_case2_item_count(case2):
    assert len(case2) == len(CASE2_ITEMS)


def test_case2_item_names(case2):
    expected = Counter(name for name, _ in CASE2_ITEMS)
    actual   = Counter(item.name for item in case2)
    assert actual == expected


def test_case2_item_classifications(case2):
    expected = Counter(cls for _, cls in CASE2_ITEMS)
    actual   = Counter(item.classification for item in case2)
    assert actual == expected


def test_case2_unique_item(case2):
    uniques = [item for item in case2 if item.classification == "Unique"]
    assert len(uniques) == 1
    assert uniques[0].name == "Greaves"


def test_case2_magic_item(case2):
    magic = [item for item in case2 if item.classification == "Magic"]
    assert len(magic) == 1
    assert magic[0].name == "Halberd"


def test_case2_grey_item(case2):
    greys = [item for item in case2 if item.classification == "Grey"]
    assert len(greys) == 1
    assert greys[0].name == "Breast Plate"


# ---------------------------------------------------------------------------
# Case 3 — run_20260219_182341.png
#
# 7 items: 2× identical healing potions, 2× gold piles, 1× mana potion,
#          1 Rare helmet, 1 Set mask.
# ---------------------------------------------------------------------------

CASE3_IMAGE = os.path.join(CASES_DIR, "3", "run_20260219_182341.png")
CASE3_ITEMS = [
    ("Super Healing Potion", "Normal"),
    ("Super Healing Potion", "Normal"),
    ("607 Gold",             "Normal"),
    ("871 Gold",             "Normal"),
    ("Super Mana Potion",    "Normal"),
    ("Assault Helmet",       "Rare"),
    ("Mask",                 "Set"),
]


@pytest.fixture(scope="module")
def case3():
    return read_items(CASE3_IMAGE)


def test_case3_item_count(case3):
    assert len(case3) == len(CASE3_ITEMS)


def test_case3_item_names(case3):
    expected = Counter(name for name, _ in CASE3_ITEMS)
    actual   = Counter(item.name for item in case3)
    assert actual == expected


def test_case3_item_classifications(case3):
    expected = Counter(cls for _, cls in CASE3_ITEMS)
    actual   = Counter(item.classification for item in case3)
    assert actual == expected


def test_case3_set_item(case3):
    sets = [item for item in case3 if item.classification == "Set"]
    assert len(sets) == 1
    assert sets[0].name == "Mask"


def test_case3_rare_item(case3):
    rares = [item for item in case3 if item.classification == "Rare"]
    assert len(rares) == 1
    assert rares[0].name == "Assault Helmet"


def test_case3_duplicate_healing_potions(case3):
    healers = [item for item in case3 if item.name == "Super Healing Potion"]
    assert len(healers) == 2
    assert all(item.classification == "Normal" for item in healers)
