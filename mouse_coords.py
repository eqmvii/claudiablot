"""
mouse_coords.py

Live mouse coordinate display. Run in a separate terminal, then hover over
anything in D2R to read its exact screen coordinates.

    python mouse_coords.py

Press Ctrl+C to quit.
"""

import pyautogui
import time

print("Move your mouse around. Press Ctrl+C to quit.\n")

try:
    while True:
        x, y = pyautogui.position()
        print(f"  x={x:4d}  y={y:4d}", end="\r")
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nDone.")
