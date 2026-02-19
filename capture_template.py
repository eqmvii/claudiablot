"""
capture_template.py

One-time setup helper. Run this while standing in town in D2R to capture
the health globe as a template image used by the bot to detect game load.

    python capture_template.py

Saves: templates/health_globe.png
"""

import mss
import numpy as np
import cv2

# Health globe sits in the bottom-left of the D2R window.
# These coords are absolute screen pixels assuming the game window is
# 1680x1050 at the upper-left corner (0, 0) of the display.
CROP = {
    "left":   821,   # center_x 846 - 25
    "top":   1041,   # center_y 1066 - 25
    "width":   50,
    "height":  50,
}

OUTPUT = "templates/ui_cross.png"


def main():
    with mss.mss() as sct:
        raw = sct.grab(CROP)
        img = np.array(raw)[:, :, :3]

    cv2.imwrite(OUTPUT, img)
    print(f"Saved {OUTPUT}  ({img.shape[1]}x{img.shape[0]} px)")

    # Show a quick preview so you can confirm it looks right
    cv2.imshow("UI cross template (press any key to close)", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
