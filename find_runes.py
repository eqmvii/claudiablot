"""
find_runes.py

Scan loot screenshots for the word "Rune" using template matching.
The template is matched only on the orange letter pixels, so varying
backgrounds do not affect the result.

Returns (cx, cy) screen-coordinate centres of any matches found.

Usage
-----
    python find_runes.py                   # scans all PNGs under samples/
    python find_runes.py path/to/img.png   # scan specific file(s)
"""

import cv2
import glob
import numpy as np
import os

TEMPLATE_PATH  = os.path.join(os.path.dirname(__file__), "templates", "words", "Rune.png")
SAMPLES_DIR    = os.path.join(os.path.dirname(__file__), "samples")
THRESHOLD      = 0.75  # match score below which we ignore results

# HSV bounds for rune-orange — must match the template mask range.
_ORANGE_LO = np.array([ 5, 120,  80])
_ORANGE_HI = np.array([25, 255, 255])
# Fraction of masked pixels in the matched crop that must be orange.
_MIN_ORANGE_FRACTION = 0.60


def _is_orange_enough(crop: np.ndarray, mask: np.ndarray) -> bool:
    """Return True if enough of the mask pixels in *crop* are rune-orange."""
    hsv         = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    orange_pix  = cv2.inRange(hsv, _ORANGE_LO, _ORANGE_HI)
    mask_count  = int(np.count_nonzero(mask))
    if mask_count == 0:
        return False
    overlap     = int(np.count_nonzero(orange_pix & mask))
    return (overlap / mask_count) >= _MIN_ORANGE_FRACTION


def _load_template():
    """Load template + build an orange-pixel mask (cached on first call)."""
    tmpl = cv2.imread(TEMPLATE_PATH)
    if tmpl is None:
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

    # Build a mask that covers only the orange letter pixels.
    # The background is dark; letters are orange (BGR ~0, 177, 255).
    hsv  = cv2.cvtColor(tmpl, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([5, 120, 80]), np.array([25, 255, 255]))
    return tmpl, mask

_TEMPLATE, _MASK = None, None

def _get_template():
    global _TEMPLATE, _MASK
    if _TEMPLATE is None:
        _TEMPLATE, _MASK = _load_template()
    return _TEMPLATE, _MASK


def _find_runes_core(img: np.ndarray, threshold: float = THRESHOLD) -> list[tuple[int, int]]:
    """Core detection on an already-loaded BGR image array."""
    tmpl, mask = _get_template()
    th, tw = tmpl.shape[:2]

    # Skip images that are smaller than the template
    if img.shape[0] < th or img.shape[1] < tw:
        return []

    result = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED, mask=mask)

    # Collect all positions that exceed the threshold
    ys, xs = np.where(result >= threshold)
    if len(xs) == 0:
        return []

    # Non-maximum suppression: keep only the strongest hit within each
    # template-sized neighbourhood so overlapping hits collapse to one.
    points = sorted(zip(xs.tolist(), ys.tolist()), key=lambda p: -result[p[1], p[0]])
    min_dist = max(tw, th) // 2
    kept = []
    for x, y in points:
        if not any(abs(x - kx) < min_dist and abs(y - ky) < min_dist
                   for kx, ky in kept):
            kept.append((x, y))

    # Reject matches whose pixels aren't actually rune-orange
    kept = [(x, y) for x, y in kept
            if _is_orange_enough(img[y:y+th, x:x+tw], mask)]

    # Convert top-left corners → centres
    return [(x + tw // 2, y + th // 2) for x, y in kept]


def find_runes(image_path: str, threshold: float = THRESHOLD) -> list[tuple[int, int]]:
    """
    Scan a single screenshot for the word "Rune".

    Parameters
    ----------
    image_path : str
        Path to a PNG screenshot.
    threshold : float
        Minimum match score (0–1).  Default 0.75.

    Returns
    -------
    list of (cx, cy) tuples — centre pixel of each match in image coordinates.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")
    return _find_runes_core(img, threshold)


def find_runes_img(img: np.ndarray, threshold: float = THRESHOLD) -> list[tuple[int, int]]:
    """
    Scan an already-loaded BGR numpy array for the word "Rune".
    Same as find_runes() but skips the disk read.
    """
    return _find_runes_core(img, threshold)


def scan_directory(root: str = SAMPLES_DIR, threshold: float = THRESHOLD) -> None:
    """Scan every PNG under *root* (recursively) and print any matches."""
    paths = sorted(glob.glob(os.path.join(root, "**", "*.png"), recursive=True))
    if not paths:
        print(f"No PNG files found under {root}")
        return

    total = 0
    for path in paths:
        hits = find_runes(path, threshold)
        rel  = os.path.relpath(path, root)
        if hits:
            for cx, cy in hits:
                print(f"  RUNE FOUND  {rel}  centre=({cx}, {cy})")
            total += len(hits)
        else:
            print(f"  no match    {rel}")

    print(f"\n{total} rune word(s) found across {len(paths)} image(s).")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            hits = find_runes(path)
            if hits:
                for cx, cy in hits:
                    print(f"RUNE at ({cx}, {cy})  [{path}]")
            else:
                print(f"no match  [{path}]")
    else:
        scan_directory()
