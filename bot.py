"""
bot.py

Diablo 2 Resurrected - Pindleskin bot.

Starting state: D2R is open on the character select screen with Waldo at
the top of the character list.

Run from a Windows terminal:
    python bot.py

The script gives you 3 seconds to alt-tab into D2R before it acts.

One-time setup required before running:
    python capture_template.py   (while standing in town in-game)
"""

import sys
import time

import cv2
import mss
import numpy as np
import pyautogui

# ---------------------------------------------------------------------------
# Game window config.
# D2R is windowed at 1680x1050, positioned at the upper-left corner (0, 0).
# All click coordinates below are absolute screen pixels.
# ---------------------------------------------------------------------------
GAME_X = 0      # left edge of game window on screen
GAME_Y = 0      # top edge of game window on screen
GAME_W = 1680
GAME_H = 1050

# Template match threshold (0-1). Lower = more lenient.
MATCH_THRESHOLD = 0.8

# Delay between actions (seconds)
STEP_DELAY = 1.0

# Walk path from spawn to Anya portal.
# Each entry is (x, y, delay_seconds) — delay is how long to wait AFTER the click
# before moving to the next waypoint. Tune per-step as needed.
PORTAL_WALK_PATH = [
    (747, 683, 1.58),
    (735, 653, 1.31),
    (717, 646, 1.23),
    (698, 631, 0.92),
    (833, 615, 0.74),
    (845, 626, 0.67),
    (864, 617, 0.92),
    (898, 596, 0.80),
    (804, 588, 0.87),
    (764, 588, 0.68),
    (749, 588, 0.65),
    (757, 592, 0.66),
    (816, 592, 0.60),
    (949, 589, 0.67),
    (870, 595, 0.58),
    (790, 602, 0.60),
    (733, 616, 0.62),
    (729, 598, 0.55),
    (728, 597, 0.56),
    (728, 597, 0.55),
    (723, 576, 1.52),
    (736, 461, 1.82),
    (589, 176, 3.0)
]


def capture_region(region: dict) -> np.ndarray:
    """Grab a screen region and return as a BGR numpy array."""
    with mss.mss() as sct:
        raw = sct.grab(region)
        return np.array(raw)[:, :, :3]


def template_visible(template: np.ndarray, region: dict, threshold=MATCH_THRESHOLD) -> bool:
    """Return True if the template is found within the given screen region."""
    screen = capture_region(region)
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val >= threshold


def wait_for_game_load():
    """Block until the health globe is visible, indicating we're in town."""
    template_path = "templates/ui_cross.png"
    template = cv2.imread(template_path)
    if template is None:
        print(f"ERROR: Template not found at '{template_path}'.")
        print("Run capture_template.py while in-game first.")
        sys.exit(1)

    # Scan the full bottom strip — template matching finds the cross wherever it is
    region = {"left": 0, "top": 900, "width": 1680, "height": 200}

    print("Waiting for game to load (watching for UI cross)...")
    while not template_visible(template, region):
        time.sleep(0.5)
    print("Game loaded — UI detected, in town.")


def walk_to_portal():
    """Click through the waypoint path to reach the Anya portal."""
    print(f"Walking to Anya portal ({len(PORTAL_WALK_PATH)} waypoints)...")
    time.sleep(1)
    for i, (x, y, delay) in enumerate(PORTAL_WALK_PATH, 1):
        print(f"  Waypoint {i}/{len(PORTAL_WALK_PATH)}: ({x}, {y}) — waiting {delay}s")
        if i == len(PORTAL_WALK_PATH):
            # Move first, pause so the game registers hover, then click in place
            pyautogui.moveTo(x, y, duration=0.3)
            time.sleep(0.3)
            pyautogui.click()
        else:
            pyautogui.click(x, y)
        time.sleep(delay)
    print("Entered portal.")


def main():
    # Waldo is always top of the list and pre-selected, so no click needed.
    print("Starting in 3 seconds — alt-tab to D2R now...")
    time.sleep(3)

    # Enter the game
    print("Pressing Enter to confirm character...")
    pyautogui.press("enter")
    time.sleep(STEP_DELAY)

    # Select Hell difficulty
    print("Pressing H for Hell difficulty...")
    pyautogui.press("h")

    # Wait until the loading screen finishes and we're standing in town
    wait_for_game_load()

    walk_to_portal()

    print("Ready — next step: kill Pindleskin.")


if __name__ == "__main__":
    main()
