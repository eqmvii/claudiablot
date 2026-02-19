"""
read_loot.py

Read item names from a Diablo 2 Resurrected loot screenshot using
greyscale template-letter matching.

Pipeline
--------
1. Build colour masks (HSV) for each item-text colour.
2. Project vertically to find horizontal text-line bands; discard
   bands that are too tall (torch/FX blobs) or too narrow.
3. For each band:
   a. Determine the dominant item colour.
   b. Column-project the band's mask to find letter blobs.
   c. Merge tiny intra-letter gaps (≤ 2 px).
   d. Greyscale-match each blob against every letter template.
   e. Insert a space wherever the inter-blob gap exceeds SPACE_GAP_PX.
4. Return LootItem(text, colour, cx, cy) for each readable line.

Usage
-----
    python read_loot.py [screenshot.png]
"""

import cv2
import numpy as np
import os
from dataclasses import dataclass

# ── Item text colour definitions (OpenCV HSV: H 0-180, S 0-255, V 0-255) ────
COLORS = {
    "white":  ((  0,   0, 170), (180,  30, 255)),
    "blue":   ((100,  80, 180), (130, 255, 255)),
    "yellow": (( 22, 100, 180), ( 38, 255, 255)),
    "gold":   (( 15,  40, 130), ( 30, 180, 230)),
    "green":  (( 50, 100,  80), ( 85, 255, 255)),
    "orange": ((  5, 120, 160), ( 20, 255, 255)),
}

TEMPLATE_DIR  = "templates/letters"
MATCH_THRESH  = 0.42   # minimum TM_CCOEFF_NORMED to accept a letter
SPACE_GAP_PX  = 14     # inter-blob gap ≥ this → word space
MERGE_GAP_PX  = 2      # inter-blob gap ≤ this → same letter, merge
MIN_ROW_HITS  = 6      # a text row needs at least this many bright pixels
LINE_V_MERGE  = 4      # rows within this distance belong to the same line
MIN_LINE_H    = 6      # discard lines shorter than this (noise)
MAX_LINE_H    = 22     # discard lines taller than this (torch / FX blobs)
MIN_LINE_W    = 20     # discard lines narrower than this (fragments)


@dataclass
class LootItem:
    text:  str
    color: str
    cx:    int   # x centre of the text span (click target)
    cy:    int   # y centre of the text row  (click target)


# ── Template loading (cached) ─────────────────────────────────────────────────
_templates: dict | None = None

def load_templates() -> dict:
    """Load all letter PNGs from templates/letters/{upper,lower}/ as binary greyscale."""
    global _templates
    if _templates is not None:
        return _templates
    _templates = {}
    for subdir in ("upper", "lower"):
        folder = os.path.join(TEMPLATE_DIR, subdir)
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            char, ext = os.path.splitext(fname)
            if ext.lower() != ".png":
                continue
            raw = cv2.imread(os.path.join(folder, fname), cv2.IMREAD_UNCHANGED)
            if raw is None:
                continue
            # RGBA → grey
            if raw.ndim == 3 and raw.shape[2] == 4:
                gray = cv2.cvtColor(raw[:, :, :3], cv2.COLOR_BGR2GRAY)
            elif raw.ndim == 3:
                gray = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)
            else:
                gray = raw
            _, binary = cv2.threshold(gray, 60, 255, cv2.THRESH_BINARY)
            # upper/ → capital key ('H'), lower/ → lowercase key ('h')
            key = char.upper() if subdir == "upper" else char.lower()
            _templates[key] = binary
    return _templates


# ── Colour masking ────────────────────────────────────────────────────────────
def build_masks(hsv: np.ndarray) -> dict:
    """Return {color_name: binary_mask} for every known item-text colour."""
    return {
        name: cv2.inRange(hsv, np.array(lo, dtype=np.uint8),
                               np.array(hi, dtype=np.uint8))
        for name, (lo, hi) in COLORS.items()
    }


# ── Line detection ────────────────────────────────────────────────────────────
def find_text_lines(combined_mask: np.ndarray) -> list[tuple[int, int]]:
    """Return [(row_top, row_bot), ...] for each plausible text-line band."""
    row_hits = (combined_mask > 0).sum(axis=1)
    bright   = np.where(row_hits >= MIN_ROW_HITS)[0]
    if len(bright) == 0:
        return []

    # Group consecutive bright rows
    bands, cur = [], [bright[0]]
    for y in bright[1:]:
        if y - cur[-1] <= LINE_V_MERGE:
            cur.append(y)
        else:
            bands.append((cur[0], cur[-1]))
            cur = [y]
    bands.append((cur[0], cur[-1]))

    # Discard bands that are clearly not a single text line
    return [
        (top, bot)
        for top, bot in bands
        if MIN_LINE_H <= bot - top + 1 <= MAX_LINE_H
    ]


# ── Letter segmentation ───────────────────────────────────────────────────────
def column_segments(col_bool: np.ndarray) -> list[list[int]]:
    """Segment a 1-D bool array into [[start, end], ...] runs."""
    segs, in_g, start = [], False, 0
    for x, val in enumerate(col_bool):
        if val and not in_g:
            start, in_g = x, True
        elif not val and in_g:
            segs.append([start, x - 1])
            in_g = False
    if in_g:
        segs.append([start, len(col_bool) - 1])
    return segs

def merge_close(segs: list, max_gap: int) -> list:
    if not segs:
        return segs
    out = [segs[0][:]]
    for s in segs[1:]:
        if s[0] - out[-1][1] - 1 <= max_gap:
            out[-1][1] = s[1]
        else:
            out.append(s[:])
    return out

def absorb_narrow(segs: list, min_w: int) -> list:
    """Merge very narrow blobs (likely 'i' dots or serifs) into the nearest blob."""
    if not segs:
        return segs
    changed = True
    while changed:
        changed = False
        out = [segs[0][:]]
        for s in segs[1:]:
            prev = out[-1]
            if s[1] - s[0] + 1 < min_w:
                # merge narrow blob into previous (extend previous rightward)
                prev[1] = s[1]
                changed = True
            elif prev[1] - prev[0] + 1 < min_w:
                # previous was narrow — merge into current
                out[-1] = [prev[0], s[1]]
                changed = True
            else:
                out.append(s[:])
        segs = out
    return segs


# ── Letter matching ───────────────────────────────────────────────────────────
def tight_crop(binary: np.ndarray) -> np.ndarray:
    """Tight-crop a binary image to its non-zero bounding box."""
    rows = np.any(binary, axis=1)
    cols = np.any(binary, axis=0)
    if not rows.any() or not cols.any():
        return np.zeros((1, 1), dtype=np.uint8)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    return binary[r0:r1 + 1, c0:c1 + 1]


# Pre-compute tight-cropped binary templates once at load time
_tc_templates: dict | None = None

def get_tc_templates() -> dict:
    """Return {char: tight_cropped_binary} for all templates."""
    global _tc_templates
    if _tc_templates is not None:
        return _tc_templates
    _tc_templates = {}
    for char, tmpl in load_templates().items():
        _, binary = cv2.threshold(tmpl, 60, 255, cv2.THRESH_BINARY)
        tc = tight_crop(binary)
        if tc.max() > 0:
            _tc_templates[char] = tc
    return _tc_templates


def _fit_to_template(blob_tc: np.ndarray, th: int, tw: int) -> np.ndarray:
    """
    Scale a tight-cropped blob to a canvas of size (th, tw) suitable for
    comparison against a template of that size.

    Strategy:
    - Scale the blob so its HEIGHT matches th (preserving aspect ratio).
    - If the resulting width ≤ tw, centre-pad horizontally with zeros.
    - If the resulting width > tw, crop to tw (centred).
    This keeps narrow letters (like 'i') narrow instead of stretching them.
    """
    bh, bw = blob_tc.shape
    if bh == 0 or bw == 0:
        return np.zeros((th, tw), dtype=np.uint8)

    # Scale height → th, keep aspect ratio
    scaled_w = max(1, round(bw * th / bh))
    scaled = cv2.resize(blob_tc, (scaled_w, th), interpolation=cv2.INTER_AREA)
    _, scaled = cv2.threshold(scaled, 60, 255, cv2.THRESH_BINARY)

    if scaled_w == tw:
        return scaled

    canvas = np.zeros((th, tw), dtype=np.uint8)
    if scaled_w <= tw:
        x_off = (tw - scaled_w) // 2
        canvas[:, x_off:x_off + scaled_w] = scaled
    else:
        x_off = (scaled_w - tw) // 2
        canvas = scaled[:, x_off:x_off + tw]
    return canvas


def match_blob(blob_mask: np.ndarray, tc_templates: dict) -> tuple[str, float]:
    """
    Match a binary blob against every template.
    Both are tight-cropped; the blob is then aspect-ratio-scaled and
    centre-padded (not stretched) to each template's dimensions.
    Returns (char, score); char is '?' if nothing clears MATCH_THRESH.
    """
    _, blob_bin = cv2.threshold(blob_mask, 0, 255, cv2.THRESH_BINARY)
    blob_tc = tight_crop(blob_bin)
    if blob_tc.max() == 0:
        return "?", 0.0

    best_char, best_score = "?", 0.0
    for char, tmpl_tc in tc_templates.items():
        th, tw = tmpl_tc.shape
        fitted = _fit_to_template(blob_tc, th, tw)
        result = cv2.matchTemplate(
            fitted.astype(np.float32),
            tmpl_tc.astype(np.float32),
            cv2.TM_CCOEFF_NORMED,
        )
        score = float(result.max())
        if score > best_score:
            best_score, best_char = score, char
    if best_score >= MATCH_THRESH:
        return best_char, best_score
    return "?", best_score


# ── Line reader ───────────────────────────────────────────────────────────────
def read_line(line_mask: np.ndarray, line_gray: np.ndarray | None = None) -> tuple[str, int, int]:
    """
    Read characters from a binary line-mask (255 = text, 0 = background).
    line_gray: optional grayscale crop of the same row range; when provided
               blobs are extracted from it (wider coverage than the HSV mask).
    Returns (text, x_left, x_right).
    """
    tc_templates = get_tc_templates()

    # Column presence: use HSV mask for segmentation (avoids torch noise),
    # but use grayscale for the actual blob content fed to matching.
    col_bool = (line_mask > 0).any(axis=0)
    segs     = merge_close(column_segments(col_bool), MERGE_GAP_PX)
    if not segs:
        return "", 0, 0

    # Source for blob pixel data
    blob_src = line_gray if line_gray is not None else line_mask

    text, prev_end = "", -1
    for seg in segs:
        x0, x1 = seg[0], seg[1]

        if prev_end >= 0 and x0 - prev_end - 1 >= SPACE_GAP_PX:
            text += " "

        blob_raw = blob_src[:, x0:x1 + 1]
        # Binarize: grayscale uses brightness threshold; binary mask passes through
        if blob_raw.max() > 1:
            thr = 80 if line_gray is not None else 0
            _, blob = cv2.threshold(blob_raw, thr, 255, cv2.THRESH_BINARY)
        else:
            blob = blob_raw
        char, _ = match_blob(blob, tc_templates)
        text += char
        prev_end = x1

    return text, segs[0][0], segs[-1][1]


# ── Top-level parser ──────────────────────────────────────────────────────────
def parse_image(path: str) -> list[LootItem]:
    """
    Parse a loot screenshot and return a list of LootItem, one per text line.
    """
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot load: {path}")

    get_tc_templates()   # warm the cache
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hsv  = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    masks     = build_masks(hsv)

    # Combined mask for line detection
    combined = np.zeros(img.shape[:2], dtype=np.uint8)
    for m in masks.values():
        combined = cv2.bitwise_or(combined, m)

    lines   = find_text_lines(combined)
    results = []

    for row_top, row_bot in lines:
        # Per-colour pixel counts in this band → dominant colour
        band_counts = {
            name: int((masks[name][row_top:row_bot + 1] > 0).sum())
            for name in COLORS
        }
        dominant = max(band_counts, key=band_counts.get)
        if band_counts[dominant] == 0:
            continue

        # Use the dominant-colour mask for letter segmentation
        line_mask = masks[dominant][row_top:row_bot + 1]

        line_gray = gray[row_top:row_bot + 1, :]
        text, x_left, x_right = read_line(line_mask, line_gray)
        span = x_right - x_left
        if span < MIN_LINE_W or not text.strip("? "):
            continue

        cx = (x_left + x_right) // 2
        cy = (row_top + row_bot) // 2
        results.append(LootItem(text=text, color=dominant, cx=cx, cy=cy))

    return results


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys, glob

    targets = sys.argv[1:] or sorted(glob.glob("samples/loot_*.png"))
    for path in targets:
        print(f"\n{'─'*60}\n{path}")
        items = parse_image(path)
        if not items:
            print("  (no items detected)")
            continue
        print(f"  {'COLOR':<8} {'CX':>5} {'CY':>5}  TEXT")
        for item in items:
            print(f"  {item.color:<8} {item.cx:>5} {item.cy:>5}  {item.text!r}")
        print(f"  {len(items)} item lines")
