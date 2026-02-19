"""
capture_loot.py

Captures a 600x600 screenshot centered on the loot area and saves it to
samples/loot_<timestamp>.png. Run this after a Pindleskin kill while items
are on the ground.

    python capture_loot.py
"""

import mss
import numpy as np
import cv2
import os
from datetime import datetime

CENTER_X = 1047
CENTER_Y = 536
WIDTH = 700   # 600 + 50 left + 50 right
HEIGHT = 640  # 600 + 20 up + 20 down

CROP = {
    "left":   CENTER_X - WIDTH // 2,
    "top":    CENTER_Y - HEIGHT // 2,
    "width":  WIDTH,
    "height": HEIGHT,
}

OUTPUT_DIR = "samples"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with mss.mss() as sct:
        raw = sct.grab(CROP)
        img = np.array(raw)[:, :, :3]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"loot_{timestamp}.png")
    cv2.imwrite(filename, img)
    print(f"Saved {filename}  ({img.shape[1]}x{img.shape[0]} px)")


if __name__ == "__main__":
    main()
