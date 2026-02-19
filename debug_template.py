"""
debug_template.py

Run this while in-game to diagnose template matching failures.
Shows the live screen region, the saved template, and the match score.

    python debug_template.py

Press any key to close the windows.
"""

import cv2
import mss
import numpy as np

TEMPLATE_PATH = "templates/ui_cross.png"
# Scan the full bottom strip of the screen so the cross can be found
# even if the window has shifted slightly.
REGION = {"left": 0, "top": 900, "width": 1680, "height": 200}


def main():
    template = cv2.imread(TEMPLATE_PATH)
    if template is None:
        print(f"ERROR: could not load {TEMPLATE_PATH}")
        return

    with mss.mss() as sct:
        raw = sct.grab(REGION)
        live = np.array(raw)[:, :, :3]

    result = cv2.matchTemplate(live, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)

    print(f"Match score: {max_val:.3f}  (bot requires >= 0.8 to proceed)")

    # Draw a rectangle on the live image showing where the best match was found
    _, _, _, max_loc = cv2.minMaxLoc(result)
    th, tw = template.shape[:2]
    top_left = max_loc
    bottom_right = (top_left[0] + tw, top_left[1] + th)
    live_annotated = live.copy()
    cv2.rectangle(live_annotated, top_left, bottom_right, (0, 255, 0), 2)

    scale = 4
    template_big = cv2.resize(template, (template.shape[1] * scale, template.shape[0] * scale), interpolation=cv2.INTER_NEAREST)

    cv2.imshow("LIVE region — green box = best match location", live_annotated)
    cv2.imshow("TEMPLATE (what bot is looking for)", template_big)
    print("Press any key in either window to close.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
