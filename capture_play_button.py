"""
capture_play_button.py

One-time setup helper. Run this while on the character select screen in D2R
to capture the Play button as a template used by the bot to confirm it's on
the character select screen.

    python capture_play_button.py

Saves: templates/play_button.png
"""

import mss
import numpy as np
import cv2

# Play button centred at (845, 991).
# Wider crop than the UI cross (80x40) to capture the full button shape.
CROP = {
    "left":   805,   # center_x 845 - 40
    "top":    971,   # center_y 991 - 20
    "width":   80,
    "height":  40,
}

OUTPUT = "templates/play_button.png"


def main():
    with mss.mss() as sct:
        raw = sct.grab(CROP)
        img = np.array(raw)[:, :, :3]

    cv2.imwrite(OUTPUT, img)
    print(f"Saved {OUTPUT}  ({img.shape[1]}x{img.shape[0]} px)")

    cv2.imshow("Play button template (press any key to close)", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
