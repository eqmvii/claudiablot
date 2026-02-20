"""
test_charm_pickup.py

Standalone charm-detection + pickup test.

Drop a charm on the ground in the same spot Pindleskin dies, then run this
script. It will:
  1. Count down 3 seconds so you can alt-tab into D2R.
  2. Press Alt to reveal item labels.
  3. Capture the same loot region the bot uses.
  4. Run the charm-detection pipeline (find_charms).
  5. Click any charm found.
  6. Save the screenshot to samples/ for post-mortem inspection.

Usage
-----
    python test_charm_pickup.py
"""

import os
import time
from datetime import datetime

import cv2
import mss
import numpy as np
import pyautogui

from find_charms import find_charms, find_charms_img

# ── same region the bot uses ────────────────────────────────────────────────
LOOT_CENTER_X = 1047
LOOT_CENTER_Y = 536
LOOT_WIDTH    = 700
LOOT_HEIGHT   = 640

SAMPLES_DIR = "samples"
COUNTDOWN   = 3   # seconds before capture


def main():
    # Countdown so the user can switch to D2R
    for i in range(COUNTDOWN, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)

    # Move mouse out of the loot area before pressing Alt
    pyautogui.moveTo(200, 200, duration=0.2)
    time.sleep(0.1)

    # Reveal item labels (same as the bot does after the kill)
    print("Pressing Alt to reveal item labels...")
    pyautogui.press("alt")
    time.sleep(0.5)   # give the game a moment to render labels

    # Capture loot region
    crop = {
        "left":   LOOT_CENTER_X - LOOT_WIDTH  // 2,
        "top":    LOOT_CENTER_Y - LOOT_HEIGHT // 2,
        "width":  LOOT_WIDTH,
        "height": LOOT_HEIGHT,
    }

    with mss.mss() as sct:
        raw = sct.grab(crop)
        img = np.array(raw)[:, :, :3]

    os.makedirs(SAMPLES_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SAMPLES_DIR, f"test_charm_{timestamp}.png")
    cv2.imwrite(path, img)
    print(f"Screenshot saved: {path}")

    # Run charm detection
    hits = find_charms(path)

    if not hits:
        print("No charm detected in screenshot.")
        return

    print(f"{len(hits)} charm label(s) found:")
    for cx, cy in hits:
        screen_x = crop["left"] + cx
        screen_y = crop["top"]  + cy
        print(f"  crop ({cx}, {cy}) → screen ({screen_x}, {screen_y}) — clicking!")
        pyautogui.moveTo(screen_x, screen_y, duration=0.4)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(0.5)

    print("Done.")


if __name__ == "__main__":
    main()
