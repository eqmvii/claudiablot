"""
ocr_items.py

Scan a D2R loot screenshot and return the list of visible items with their
names and classifications (Normal, Magic, Rare, Unique, Set, Grey, Rune).

Approach
--------
1. For each D2R text colour, build an HSV binary mask.
2. Slide each letter template over the mask to find character matches.
3. Group matched characters into lines and words by position.
4. Fuzzy-match the raw OCR text against a known D2 item list using
   Levenshtein distance to correct OCR errors.
5. Map the text colour to a classification and return Item objects.
"""

import cv2
import numpy as np
import os
from collections import Counter
from dataclasses import dataclass

# ───────────────────────────────────────────────────────────
# Public types
# ───────────────────────────────────────────────────────────

@dataclass
class Item:
    name: str
    classification: str
    x: int = 0
    y: int = 0

# ───────────────────────────────────────────────────────────
# Colour definitions (OpenCV HSV)
# ───────────────────────────────────────────────────────────

ITEM_COLORS = {
    "white":  (( 0,   0, 180), (180,  40, 255)),
    "grey":   (( 0,   0, 100), (180,  50, 175)),
    "orange": (( 8, 140, 160), ( 22, 255, 255)),
    "yellow": (( 22, 120, 160), ( 35, 255, 255)),
    "blue":   (( 95,  80, 120), (135, 255, 255)),
    "green":  (( 50, 100,  80), ( 85, 255, 255)),
    "gold":   (( 18,  60, 140), ( 28, 220, 230)),
}

COLOR_TO_CLASS = {
    "white":  "Normal",
    "grey":   "Grey",
    "orange": "Rune",
    "yellow": "Rare",
    "blue":   "Magic",
    "green":  "Set",
    "gold":   "Unique",
}

# ───────────────────────────────────────────────────────────
# Letter template loading
# ───────────────────────────────────────────────────────────

_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "templates", "letters")
_templates = None

def _load_templates():
    """Load all letter templates as binary images (white-on-black)."""
    all_tmpls = []
    for subdir in ("lower", "upper"):
        d = os.path.join(_TEMPLATE_DIR, subdir)
        if not os.path.isdir(d):
            continue
        for fname in os.listdir(d):
            name, ext = os.path.splitext(fname)
            if ext.lower() != ".png":
                continue
            tmpl = cv2.imread(os.path.join(d, fname), cv2.IMREAD_GRAYSCALE)
            if tmpl is not None:
                # Binarize: threshold to get clean white-on-black
                _, tmpl_bin = cv2.threshold(tmpl, 80, 255, cv2.THRESH_BINARY)
                all_tmpls.append((name, tmpl_bin))
    return all_tmpls

def _get_templates():
    global _templates
    if _templates is None:
        _templates = _load_templates()
    return _templates

# ───────────────────────────────────────────────────────────
# Sliding-window template matching on binary masks
# ───────────────────────────────────────────────────────────

MATCH_THRESHOLD = 0.70

def _find_characters_in_mask(mask):
    """Slide each letter template over a binary mask, return matched chars with positions."""
    templates = _get_templates()
    if not templates:
        return []

    hits = []  # (x, y, w, h, char, score)

    for char, tmpl in templates:
        th, tw = tmpl.shape[:2]
        # Skip if template is bigger than the mask
        if th > mask.shape[0] or tw > mask.shape[1]:
            continue

        result = cv2.matchTemplate(mask, tmpl, cv2.TM_CCOEFF_NORMED)
        locs = np.where(result >= MATCH_THRESHOLD)

        for y, x in zip(locs[0], locs[1]):
            score = float(result[y, x])
            hits.append((x, y, tw, th, char, score))

    # Non-max suppression: remove overlapping detections, keep best score
    hits.sort(key=lambda h: -h[5])  # sort by score descending
    kept = []
    for hit in hits:
        x, y, w, h = hit[:4]
        cx, cy = x + w // 2, y + h // 2
        # Check if this overlaps with any already-kept detection
        overlap = False
        for kx, ky, kw, kh, _, _ in kept:
            kcx, kcy = kx + kw // 2, ky + kh // 2
            if abs(cx - kcx) < max(w, kw) * 0.5 and abs(cy - kcy) < max(h, kh) * 0.5:
                overlap = True
                break
        if not overlap:
            kept.append(hit)

    return kept

# ───────────────────────────────────────────────────────────
# Grouping characters → lines → words → text
# ───────────────────────────────────────────────────────────

LINE_Y_GAP =  8   # max vertical center difference for same line
WORD_X_GAP = 10   # horizontal gap between chars to break a word

def _group_into_lines(chars):
    """Group character hits into lines by vertical proximity."""
    if not chars:
        return []
    # Sort by y first
    chars = sorted(chars, key=lambda c: (c[1], c[0]))
    lines, current = [], [chars[0]]
    for c in chars[1:]:
        prev_cy = current[-1][1] + current[-1][3] // 2
        curr_cy = c[1] + c[3] // 2
        if abs(curr_cy - prev_cy) <= LINE_Y_GAP:
            current.append(c)
        else:
            lines.append(sorted(current, key=lambda c: c[0]))
            current = [c]
    lines.append(sorted(current, key=lambda c: c[0]))
    return lines

def _line_to_text(line_chars):
    """Convert a line of character hits into text with spaces between words."""
    if not line_chars:
        return ""
    words = []
    current_word = [line_chars[0]]
    for c in line_chars[1:]:
        prev = current_word[-1]
        gap = c[0] - (prev[0] + prev[2])  # x - (prev_x + prev_w)
        if gap > WORD_X_GAP:
            words.append(current_word)
            current_word = [c]
        else:
            current_word.append(c)
    words.append(current_word)

    parts = []
    for word in words:
        parts.append("".join(c[4] for c in word))
    return " ".join(parts)

def _line_center(line_chars):
    """Return (cx, cy) average center of a line."""
    xs = [c[0] + c[2] // 2 for c in line_chars]
    ys = [c[1] + c[3] // 2 for c in line_chars]
    return sum(xs) // len(xs), sum(ys) // len(ys)

def _word_lengths(line_chars):
    """Return list of word lengths (in chars) for noise filtering."""
    if not line_chars:
        return []
    words = [[line_chars[0]]]
    for c in line_chars[1:]:
        prev = words[-1][-1]
        gap = c[0] - (prev[0] + prev[2])
        if gap > WORD_X_GAP:
            words.append([c])
        else:
            words[-1].append(c)
    return [len(w) for w in words]

# ───────────────────────────────────────────────────────────
# Levenshtein distance
# ───────────────────────────────────────────────────────────

def _levenshtein(s1, s2):
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j+1] + 1, curr[j] + 1,
                            prev[j] + (0 if c1 == c2 else 1)))
        prev = curr
    return prev[-1]

# ───────────────────────────────────────────────────────────
# Known D2 item names
# ───────────────────────────────────────────────────────────

KNOWN_ITEMS = [
    # Potions
    "Super Mana Potion", "Super Healing Potion",
    "Full Rejuvination Potion", "Rejuvenation Potion",
    "Greater Mana Potion", "Greater Healing Potion",
    "Mana Potion", "Healing Potion",
    "Minor Mana Potion", "Minor Healing Potion",
    "Light Mana Potion", "Light Healing Potion",
    # Gems
    "Chipped Topaz", "Chipped Amethyst", "Chipped Sapphire",
    "Chipped Ruby", "Chipped Emerald", "Chipped Diamond",
    "Flawed Topaz", "Flawed Amethyst", "Flawed Sapphire",
    "Flawed Ruby", "Flawed Emerald", "Flawed Diamond",
    "Topaz", "Amethyst", "Sapphire", "Ruby", "Emerald", "Diamond",
    "Flawless Topaz", "Flawless Amethyst", "Flawless Sapphire",
    "Flawless Ruby", "Flawless Emerald", "Flawless Diamond",
    "Perfect Topaz", "Perfect Amethyst", "Perfect Sapphire",
    "Perfect Ruby", "Perfect Emerald", "Perfect Diamond",
    # Runes
    "El Rune", "Eld Rune", "Tir Rune", "Nef Rune", "Eth Rune",
    "Ith Rune", "Tal Rune", "Ral Rune", "Ort Rune", "Thul Rune",
    "Amn Rune", "Sol Rune", "Shael Rune", "Dol Rune", "Hel Rune",
    "Io Rune", "Lum Rune", "Ko Rune", "Fal Rune", "Lem Rune",
    "Pul Rune", "Um Rune", "Mal Rune", "Ist Rune", "Gul Rune",
    "Vex Rune", "Ohm Rune", "Lo Rune", "Sur Rune", "Ber Rune",
    "Jah Rune", "Cham Rune", "Zod Rune",
    # Weapons
    "Pilum", "Halberd", "Claymore", "Scimitar", "Javelin",
    "Short War Bow", "Military Pick", "War Sword", "Battle Axe",
    "Gothic Axe", "Glaive", "Double Bow", "Stiletto", "Knife",
    "Giant Thresher", "Thresher", "Colossus Blade", "Berserker Axe",
    "Cryptic Sword", "Phase Blade", "Hydra Bow", "Unearthed Wand",
    "Ataghan", "Conquest Sword", "Bec-de-Corbin", "War Pike",
    "Lance", "Pike", "Voulge", "Poleaxe", "Bardiche", "Partizan",
    "Spear", "Trident", "Brandistock", "War Fork",
    "Short Sword", "Long Sword", "Broad Sword", "Bastard Sword",
    "Flamberge", "Great Sword", "Zweihander",
    "Hand Axe", "Axe", "Double Axe", "Cleaver",
    "Large Axe", "Broad Axe", "Giant Axe", "Executioner Sword",
    "Dagger", "Dirk", "Kris", "Blade",
    "Short Bow", "Long Bow", "Composite Bow", "Short Battle Bow",
    "Long Battle Bow", "Short War Bow", "Long War Bow",
    "Scepter", "Grand Scepter", "War Scepter",
    "Staff", "Long Staff", "Gnarled Staff", "Battle Staff", "War Staff",
    "Wand", "Yew Wand", "Bone Wand", "Grim Wand",
    "Mace", "Morning Star", "Flail", "War Hammer", "Maul",
    "Great Maul", "Club", "Spiked Club",
    "Luna", "Truncheon", "Mighty Scepter",
    "Scissors Katar", "Suwayyah", "Wrist Sword",
    "Balanced Knife", "Balanced Axe",
    "Hyperion Javelin", "Stygian Pilum", "Matriarchal Javelin",
    "Superior Cestus",
    # Armor / Helms / Shields / Belts / Boots / Gloves
    "Demonhide Sash", "Greaves", "Breast Plate", "Assault Helmet",
    "Mask", "Heraldic Shield", "Ring", "Ornate Plate",
    "Scale Mail", "Chain Mail", "Fanged Helm", "Heavy Belt",
    "Heavy Boots", "Light Plate", "Gothic Shield",
    "Serpentskin Armor", "Archon Plate", "Dusk Shroud",
    "Wyrmhide", "Scarab Husk", "Wire Fleece", "Diamond Mail",
    "Loricated Mail", "Great Hauberk", "Boneweave",
    "Lacquered Plate", "Shadow Plate", "Sacred Armor",
    "Quilted Armor", "Leather Armor", "Hard Leather Armor",
    "Studded Leather", "Ring Mail", "Splint Mail",
    "Plate Mail", "Field Plate", "Gothic Plate", "Full Plate Mail",
    "Ancient Armor",
    "Cap", "Skull Cap", "Helm", "Full Helm", "Great Helm",
    "Crown", "Bone Helm", "War Hat", "Sallet", "Casque",
    "Basinet", "Winged Helm", "Grand Crown", "Death Mask",
    "Bone Visage", "Demonhead", "Corona", "Tiara", "Diadem",
    "Circlet",
    "Buckler", "Small Shield", "Large Shield", "Kite Shield",
    "Tower Shield", "Bone Shield", "Spiked Shield",
    "Monarch", "Ward", "Aegis", "Troll Nest",
    "Sash", "Light Belt", "Belt", "Heavy Belt", "Plated Belt",
    "War Belt", "Mithril Coil", "Troll Belt", "Colossus Girdle",
    "Vampirefang Belt", "Spiderweb Sash",
    "Boots", "Heavy Boots", "Chain Boots", "Light Plated Boots",
    "Greaves", "Mirrored Boots", "War Boots",
    "Scarabshell Boots", "Boneweave Boots", "Myrmidon Greaves",
    "Leather Gloves", "Heavy Gloves", "Chain Gloves",
    "Light Gauntlets", "Gauntlets", "War Gauntlets",
    "Ogre Gauntlets", "Vambraces",
    "Amulet",
    # Misc
    "Jewel", "Key", "Scroll of Town Portal",
    "Scroll of Identify", "Ear",
    # Class items
    "Shrunken Head", "Preserved Head",
    "Hawk Helm", "Antlers", "Falcon Mask", "Spirit Mask",
    "Jawbone Cap", "Jawbone Visor", "Fanged Helm",
    "Horned Helm", "Assault Helmet", "Avenger Guard",
    "Barbed Shield", "Rondache", "Heraldic Shield",
    "Aerin Shield", "Crown Shield", "Akaran Targe",
    "Akaran Rondache", "Protector Shield", "Gilded Shield",
    "Royal Shield", "Sacred Targe", "Sacred Rondache",
    "Kurast Shield", "Zakarum Shield", "Vortex Shield",
    # Charms
    "Small Charm", "Large Charm", "Grand Charm",
]

# ───────────────────────────────────────────────────────────
# Fuzzy matching
# ───────────────────────────────────────────────────────────

def _fuzzy_match(raw_text, max_dist=None):
    """Best-match raw OCR text to a known item name."""
    if not raw_text or len(raw_text) < 2:
        return None
    if max_dist is None:
        max_dist = max(3, len(raw_text) // 3)

    best, best_d = None, max_dist + 1
    raw_lower = raw_text.lower()
    for name in KNOWN_ITEMS:
        d = _levenshtein(raw_lower, name.lower())
        if d < best_d:
            best_d, best = d, name
    return best if best_d <= max_dist else None

def _looks_like_gold(raw_text):
    """Heuristic: does this line look like 'NNN Gold'?"""
    words = raw_text.split()
    if len(words) < 2:
        return False
    return _levenshtein(words[-1].lower(), "gold") <= 2

def _extract_gold_name(raw_text, line_chars):
    """Recover gold amount. We don't have digit templates yet, so use blob count."""
    # Split chars into words
    if not line_chars:
        return None
    words_chars = [[line_chars[0]]]
    for c in line_chars[1:]:
        prev = words_chars[-1][-1]
        gap = c[0] - (prev[0] + prev[2])
        if gap > WORD_X_GAP:
            words_chars.append([c])
        else:
            words_chars[-1].append(c)

    if len(words_chars) < 2:
        return None

    # Count characters before "Gold" word — those are digits
    digit_count = sum(len(w) for w in words_chars[:-1])
    if digit_count == 0:
        return None

    return "?" * digit_count + " Gold"

# ───────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────

def read_items(image_path: str) -> list[Item]:
    """Scan a loot screenshot and return all visible items."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    all_chars = []  # (x, y, w, h, char, score, color_name)

    for color_name, (lo, hi) in ITEM_COLORS.items():
        mask = cv2.inRange(hsv, np.array(lo), np.array(hi))
        # Morphological close to merge dots/serifs
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        chars = _find_characters_in_mask(mask)
        for x, y, w, h, char, score in chars:
            all_chars.append((x, y, w, h, char, score, color_name))

    # Group into lines
    lines = _group_into_lines(all_chars)

    items = []
    for line_chars in lines:
        # Noise filter: need at least one word with >= 3 characters
        wlens = _word_lengths(line_chars)
        if not any(wl >= 3 for wl in wlens):
            continue

        # Determine dominant color for this line
        color_counts = Counter(c[6] for c in line_chars)
        color = color_counts.most_common(1)[0][0]
        cls = COLOR_TO_CLASS.get(color, "Normal")

        raw_text = _line_to_text(line_chars)
        cx, cy = _line_center(line_chars)

        # Gold piles
        if _looks_like_gold(raw_text):
            gold_name = _extract_gold_name(raw_text, line_chars)
            if gold_name:
                items.append(Item(name=gold_name, classification="Normal",
                                  x=cx, y=cy))
            continue

        # Regular items: fuzzy match
        matched = _fuzzy_match(raw_text)
        if matched:
            items.append(Item(name=matched, classification=cls,
                              x=cx, y=cy))

    return items
