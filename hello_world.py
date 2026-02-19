"""
hello_world.py

Proof-of-concept: capture the screen, display it, and do a test click.

Run this from a Windows terminal (cmd / PowerShell) with D2R open in
windowed or borderless-windowed mode:

    pip install -r requirements.txt
    python hello_world.py

Controls (while the preview window is focused):
    q  - quit without clicking
    c  - move mouse to screen center and do a single left-click, then quit
"""

import sys
import time

import cv2
import mss
import numpy as np
import pyautogui


def capture_screen() -> np.ndarray:
    """Capture the full primary monitor and return as a BGR numpy array."""
    with mss.mss() as sct:
        # monitor 1 = primary monitor (0 = all monitors combined)
        monitor = sct.monitors[1]
        raw = sct.grab(monitor)
        # mss returns BGRA; drop the alpha channel for OpenCV
        img = np.array(raw)[:, :, :3]
    return img


def main():
    print("Capturing screen...")
    img = capture_screen()

    h, w = img.shape[:2]
    print(f"Captured image: {w}x{h} pixels")

    # Save a screenshot so we can inspect it even if the window doesn't open
    cv2.imwrite("screenshot.png", img)
    print("Saved screenshot.png")

    # Shrink the preview so it fits on screen comfortably
    scale = 0.5
    preview = cv2.resize(img, (int(w * scale), int(h * scale)))

    cv2.imshow("Screen capture preview  |  q = quit  |  c = click center", preview)
    print("Preview window open. Press 'q' to quit or 'c' to test-click the screen center.")

    center_x, center_y = w // 2, h // 2

    while True:
        key = cv2.waitKey(100) & 0xFF  # check every 100 ms

        if key == ord("q"):
            print("Quitting.")
            break

        if key == ord("c"):
            cv2.destroyAllWindows()
            print(f"Moving mouse to screen center ({center_x}, {center_y}) in 2 seconds...")
            time.sleep(2)
            pyautogui.moveTo(center_x, center_y, duration=0.5)
            pyautogui.click()
            print("Click done.")
            break

    cv2.destroyAllWindows()
    print("All done.")


if __name__ == "__main__":
    main()
