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

    # Only scan around the known UI cross position (center ~846, 1066)
    region = {"left": 821, "top": 1041, "width": 50, "height": 50}

    print("Waiting for game to load (watching for UI cross)...")
    while not template_visible(template, region):
        time.sleep(0.5)
    print("Game loaded — UI detected, in town.")


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

    print("Ready — next step: walk to the Anya portal.")


if __name__ == "__main__":
    main()
