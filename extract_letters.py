"""
extract_letters.py

One-time helper that pulls every letter-sized blob out of all sample images
and saves them (4x zoomed, so they're easy to inspect) to:

    templates/letters/raw/<color>/blob_NNNN.png

After running this:
  1. Open each colour folder and look through the blobs.
  2. Rename each file to the character it shows, e.g.  blob_0042.png → A.png
  3. Move (or copy) the renamed files into  templates/letters/<color>/
     so that parse_loot.py can use them for matching.

Usage
-----
    python extract_letters.py
"""

import cv2
import os
import glob
from parse_loot import find_blobs

SAMPLES_GLOB = "samples/loot_*.png"
RAW_DIR      = "templates/letters/raw"
ZOOM         = 4   # zoom factor for saved blobs — easier to see at 4x


def main():
    sample_paths = sorted(glob.glob(SAMPLES_GLOB))
    if not sample_paths:
        print("No sample images found in samples/")
        return

    os.makedirs(RAW_DIR, exist_ok=True)
    counters = {}

    for img_path in sample_paths:
        img = cv2.imread(img_path)
        if img is None:
            print(f"  Could not load {img_path}, skipping.")
            continue
        blobs = find_blobs(img)
        print(f"{img_path}: {len(blobs)} blobs found")

        for blob in blobs:
            color_dir = os.path.join(RAW_DIR, blob.color)
            os.makedirs(color_dir, exist_ok=True)

            n = counters.get(blob.color, 0)
            counters[blob.color] = n + 1

            fname  = os.path.join(color_dir, f"blob_{n:04d}.png")
            zoomed = cv2.resize(blob.img, (blob.w * ZOOM, blob.h * ZOOM),
                                interpolation=cv2.INTER_NEAREST)
            cv2.imwrite(fname, zoomed)

    print(f"\nBlobs saved to {RAW_DIR}/")
    for color, count in sorted(counters.items()):
        print(f"  {color:<10} {count:>4} blobs")

    print("""
Next steps:
  1. Browse templates/letters/raw/<color>/ and identify each blob.
  2. Rename blob_NNNN.png → <character>.png  (e.g. A.png, r.png, 7.png)
  3. Move renamed files to  templates/letters/<color>/
  4. Run  python parse_loot.py <sample>  to test recognition.
""")


if __name__ == "__main__":
    main()
