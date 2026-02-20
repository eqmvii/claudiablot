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

# Templates that are narrow/thin and prone to over-matching.
# These are matched last and only in positions not already claimed.
DEFERRED_CHARS = {"i", "l"}

def _find_characters_in_mask(mask):
    """Slide each letter template over a binary mask, return matched chars with positions."""
    templates = _get_templates()
    if not templates:
        return []

    # Split templates into primary (matched first) and deferred (matched last)
    primary = [(c, t) for c, t in templates if c not in DEFERRED_CHARS]
    deferred = [(c, t) for c, t in templates if c in DEFERRED_CHARS]

    hits = []  # (x, y, w, h, char, score)

    for char, tmpl in primary:
        th, tw = tmpl.shape[:2]
        if th > mask.shape[0] or tw > mask.shape[1]:
            continue
        result = cv2.matchTemplate(mask, tmpl, cv2.TM_CCOEFF_NORMED)
        locs = np.where(result >= MATCH_THRESHOLD)
        for y, x in zip(locs[0], locs[1]):
            score = float(result[y, x])
            hits.append((x, y, tw, th, char, score))

    # Non-max suppression for primary hits
    hits.sort(key=lambda h: -h[5])
    kept = []
    for hit in hits:
        x, y, w, h = hit[:4]
        cx, cy = x + w // 2, y + h // 2
        overlap = False
        for kx, ky, kw, kh, _, _ in kept:
            kcx, kcy = kx + kw // 2, ky + kh // 2
            if abs(cx - kcx) < max(w, kw) * 0.5 and abs(cy - kcy) < max(h, kh) * 0.5:
                overlap = True
                break
        if not overlap:
            kept.append(hit)

    # Now match deferred templates, only keeping hits that don't overlap with primary
    deferred_hits = []
    for char, tmpl in deferred:
        th, tw = tmpl.shape[:2]
        if th > mask.shape[0] or tw > mask.shape[1]:
            continue
        result = cv2.matchTemplate(mask, tmpl, cv2.TM_CCOEFF_NORMED)
        locs = np.where(result >= MATCH_THRESHOLD)
        for y, x in zip(locs[0], locs[1]):
            score = float(result[y, x])
            deferred_hits.append((x, y, tw, th, char, score))

    deferred_hits.sort(key=lambda h: -h[5])
    for hit in deferred_hits:
        x, y, w, h = hit[:4]
        cx, cy = x + w // 2, y + h // 2
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
ITEM_X_GAP = 40   # horizontal gap between chars to split into separate items

def _group_into_lines(chars):
    """Group character hits into lines by vertical proximity,
    then split lines with large horizontal gaps (different items at same height)."""
    if not chars:
        return []
    # Sort by y first
    chars = sorted(chars, key=lambda c: (c[1], c[0]))
    raw_lines, current = [], [chars[0]]
    for c in chars[1:]:
        prev_cy = current[-1][1] + current[-1][3] // 2
        curr_cy = c[1] + c[3] // 2
        if abs(curr_cy - prev_cy) <= LINE_Y_GAP:
            current.append(c)
        else:
            raw_lines.append(sorted(current, key=lambda c: c[0]))
            current = [c]
    raw_lines.append(sorted(current, key=lambda c: c[0]))

    # Split lines that have large horizontal gaps (separate items at same Y)
    lines = []
    for line in raw_lines:
        segment = [line[0]]
        for c in line[1:]:
            prev = segment[-1]
            gap = c[0] - (prev[0] + prev[2])
            if gap > ITEM_X_GAP:
                lines.append(segment)
                segment = [c]
            else:
                segment.append(c)
        lines.append(segment)

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
# Known D2 item names — loaded from item_names.txt plus extras
# ───────────────────────────────────────────────────────────

def _load_item_names():
    """Load known item names from item_names.txt, plus a few extras."""
    names = []
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "item_names.txt")
    try:
        with open(path) as f:
            for line in f:
                name = line.strip()
                if name:
                    names.append(name)
    except FileNotFoundError:
        pass
    # Items not in the reference file
    extras = [
        "Gold", "Key", "Ear", "Knife", "Staff",
        "Full Rejuvination Potion", "Rejuvenation Potion",
        "Minor Mana Potion", "Minor Healing Potion",
        "Light Mana Potion", "Light Healing Potion",
        "Shrunken Head", "Bec-de-Corbin",
    ]
    seen = set(names)
    for e in extras:
        if e not in seen:
            names.append(e)
    return names

KNOWN_ITEMS = _load_item_names()

# ───────────────────────────────────────────────────────────
# Fuzzy matching
# ───────────────────────────────────────────────────────────

def _lcs_length(s1, s2):
    """Length of the longest common subsequence (space-optimized DP)."""
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 0
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    return prev[n]


def _fuzzy_match(raw_text, min_score=0.45):
    """Best-match raw OCR text to a known item name.

    Uses LCS-based Dice coefficient as the primary metric:
        score = 2 * lcs_length / (len_raw + len_name)
    This naturally handles both truncated OCR (missing letters) and
    overlong candidates without biasing toward short or long names.
    Ties broken by edit distance (lower = better).
    """
    if not raw_text or len(raw_text) < 2:
        return None

    raw_compact = raw_text.replace(" ", "").lower()
    if len(raw_compact) < 2:
        return None

    best = None
    best_score = min_score - 0.01
    best_lcs = 0

    for name in KNOWN_ITEMS:
        name_compact = name.replace(" ", "").lower()
        lcs = _lcs_length(raw_compact, name_compact)
        total_len = len(raw_compact) + len(name_compact)
        score = 2 * lcs / total_len if total_len > 0 else 0
        if score < min_score:
            continue
        # Primary: highest Dice score. Tiebreak: highest raw LCS count
        # (prefer the candidate that explains more of the raw text).
        if score > best_score or (score == best_score and lcs > best_lcs):
            best_score = score
            best_lcs = lcs
            best = name

    return best

def _looks_like_gold(raw_text):
    """Heuristic: does this line look like 'NNN Gold'?

    Returns True if the line ends with something close to 'gold'.
    These lines are kept as Item(name='Gold', classification='Normal').
    """
    compact = raw_text.replace(" ", "").lower()
    if len(compact) < 2:
        return False
    # Check if it ends with something close to "gold"
    tail = compact[-4:] if len(compact) >= 4 else compact
    return _levenshtein(tail, "gold") <= 2

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
        raw_text = _line_to_text(line_chars)
        cx, cy = _line_center(line_chars)

        # Gold piles: check before noise filter since "gol" is short
        if _looks_like_gold(raw_text):
            items.append(Item(name="Gold", classification="Normal",
                              x=cx, y=cy))
            continue

        # Noise filter: need at least 3 total characters
        total_chars = len(raw_text.replace(" ", ""))
        if total_chars < 3:
            continue

        # Determine dominant color for this line
        color_counts = Counter(c[6] for c in line_chars)
        color = color_counts.most_common(1)[0][0]
        cls = COLOR_TO_CLASS.get(color, "Normal")

        # Regular items: fuzzy match
        matched = _fuzzy_match(raw_text)
        if matched:
            items.append(Item(name=matched, classification=cls,
                              x=cx, y=cy))

    return items
