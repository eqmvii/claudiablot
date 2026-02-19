"""
parse_loot.py

Scans a loot screenshot and returns a list of detected words with their
text colour (which indicates item type in Diablo II).

Pipeline
--------
1. For each known item-text colour, build an HSV mask.
2. Find connected components (individual letter blobs) inside each mask.
3. Group blobs that are vertically close into rows, then horizontally
   close into words.
4. If letter templates exist in templates/letters/<colour>/ match each
   blob to a character; otherwise the character is left as '?'.
5. Return a list of Word(text, colour, x, y) named tuples.

Usage
-----
    python parse_loot.py samples/loot_20260219_091726.png
"""

import cv2
import numpy as np
import os
from collections import namedtuple

# ─────────────────────────────────────────────────────────────
# Item text colour definitions (OpenCV HSV ranges)
# H: 0-180, S: 0-255, V: 0-255
# ─────────────────────────────────────────────────────────────
ITEM_COLORS = {
    "white":  ((  0,   0, 180), (180,  40, 255)),  # normal items
    "orange": ((  8, 140, 160), ( 22, 255, 255)),  # runes / crafted
    "yellow": (( 22, 120, 160), ( 35, 255, 255)),  # rare items / gold
    "blue":   (( 95,  80, 120), (135, 255, 255)),  # magic items
    "green":  (( 50, 100,  80), ( 85, 255, 255)),  # set items
    "gold":   (( 18,  60, 140), ( 28, 220, 230)),  # unique items
}

TEMPLATE_DIR = "templates/letters"

# ─────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────
Blob = namedtuple("Blob", ["x", "y", "w", "h", "color", "img"])
Word = namedtuple("Word", ["text", "color", "x", "y"])

# ─────────────────────────────────────────────────────────────
# Blob detection
# ─────────────────────────────────────────────────────────────
MIN_BLOB_AREA =   8   # px² — smaller is noise
MAX_BLOB_AREA = 400   # px² — larger is probably not a single letter
MIN_BLOB_H    =   5   # px
MAX_BLOB_H    =  24   # px

def find_blobs(img_bgr):
    """Return a list of Blob for every letter-sized connected component."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    blobs = []
    for color_name, (lo, hi) in ITEM_COLORS.items():
        mask = cv2.inRange(hsv, np.array(lo), np.array(hi))
        # small close to merge dots/serifs into their parent letter
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for i in range(1, n):  # 0 = background
            x, y, w, h, area = stats[i]
            if not (MIN_BLOB_AREA <= area <= MAX_BLOB_AREA):
                continue
            if not (MIN_BLOB_H <= h <= MAX_BLOB_H):
                continue
            blobs.append(Blob(x, y, w, h, color_name, img_bgr[y:y+h, x:x+w]))

    blobs.sort(key=lambda b: (b.y, b.x))
    return blobs

# ─────────────────────────────────────────────────────────────
# Grouping
# ─────────────────────────────────────────────────────────────
LINE_Y_GAP  =  6   # px — vertical centre difference to count as same line
WORD_X_GAP  = 12   # px — horizontal gap between blobs to break a word

def group_into_lines(blobs):
    """Group blobs into lines based on vertical proximity of their centres."""
    if not blobs:
        return []
    lines, current = [], [blobs[0]]
    for b in blobs[1:]:
        prev = current[-1]
        prev_cy = prev.y + prev.h // 2
        curr_cy = b.y   + b.h   // 2
        if abs(curr_cy - prev_cy) <= LINE_Y_GAP:
            current.append(b)
        else:
            lines.append(sorted(current, key=lambda b: b.x))
            current = [b]
    lines.append(sorted(current, key=lambda b: b.x))
    return lines

def group_line_into_words(line_blobs):
    """Split a sorted line of blobs into word groups by horizontal gap."""
    words, current = [], [line_blobs[0]]
    for b in line_blobs[1:]:
        prev = current[-1]
        if b.x - (prev.x + prev.w) <= WORD_X_GAP:
            current.append(b)
        else:
            words.append(current)
            current = [b]
    words.append(current)
    return words

# ─────────────────────────────────────────────────────────────
# Letter matching
# ─────────────────────────────────────────────────────────────
_template_cache: dict = {}

def _load_templates(color):
    """Load letter templates for a colour from disk (cached)."""
    if color in _template_cache:
        return _template_cache[color]
    templates = {}
    path = os.path.join(TEMPLATE_DIR, color)
    if os.path.isdir(path):
        for fname in os.listdir(path):
            char, ext = os.path.splitext(fname)
            if ext.lower() in (".png", ".bmp"):
                tmpl = cv2.imread(os.path.join(path, fname), cv2.IMREAD_GRAYSCALE)
                if tmpl is not None:
                    templates[char] = tmpl
    _template_cache[color] = templates
    return templates

def match_letter(blob_img, color):
    """Return the best-matching character for a blob crop, or '?' if unknown."""
    templates = _load_templates(color)
    if not templates:
        return "?"
    gray = cv2.cvtColor(blob_img, cv2.COLOR_BGR2GRAY)
    best_char, best_score = "?", -1.0
    for char, tmpl in templates.items():
        resized = cv2.resize(gray, (tmpl.shape[1], tmpl.shape[0]),
                             interpolation=cv2.INTER_AREA)
        score = float(cv2.matchTemplate(resized, tmpl, cv2.TM_CCOEFF_NORMED).max())
        if score > best_score:
            best_score, best_char = score, char
    return best_char if best_score > 0.5 else "?"

# ─────────────────────────────────────────────────────────────
# Top-level parser
# ─────────────────────────────────────────────────────────────
def parse_image(path):
    """
    Load a loot screenshot and return a list of Word(text, color, x, y).
    Characters will show as '?' until letter templates are trained.
    """
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {path}")

    blobs = find_blobs(img)
    lines = group_into_lines(blobs)
    results = []
    for line in lines:
        for word_blobs in group_line_into_words(line):
            chars = [match_letter(b.img, b.color) for b in word_blobs]
            text  = "".join(chars)
            color = word_blobs[0].color
            x, y  = word_blobs[0].x, word_blobs[0].y
            results.append(Word(text, color, x, y))
    return results


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "samples/loot_20260219_091726.png"
    words = parse_image(path)
    print(f"\n{'COLOR':<10} {'X':>5} {'Y':>5}  TEXT")
    print("-" * 40)
    for w in words:
        print(f"{w.color:<10} {w.x:>5} {w.y:>5}  {w.text}")
    print(f"\n{len(words)} words detected.")
