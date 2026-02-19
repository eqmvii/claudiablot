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

import os
import sys
import time
from datetime import datetime

import cv2
import mss
import numpy as np
import pyautogui

from find_runes import find_runes

# ---------------------------------------------------------------------------
# Game window config.
# D2R is windowed at 1680x1050, positioned at the upper-left corner (0, 0).
# All click coordinates below are absolute screen pixels.
# ---------------------------------------------------------------------------
GAME_X = 0      # left edge of game window on screen
GAME_Y = 0      # top edge of game window on screen
GAME_W = 1680
GAME_H = 1050

# Set to True to print step-by-step progress to the console.
VERBOSE = False

# Template match threshold (0-1). Lower = more lenient.
MATCH_THRESHOLD = 0.8

# Directory for per-run loot screenshots
SCREENS_DIR = "screens_from_runs"

# Log file for run results
RUN_LOG = "runs.log"

# Loot capture region — same as capture_loot.py
LOOT_CENTER_X = 1047
LOOT_CENTER_Y = 536
LOOT_WIDTH    = 700
LOOT_HEIGHT   = 640

# Delay between actions (seconds)
STEP_DELAY = 1.0

# Blade Warp path from Anya portal into Nihlathak's temple to reach Pindleskin.
# Each entry is (x, y, move_duration, delay_after) where:
#   move_duration — seconds to take moving the mouse to (x, y)
#   delay_after   — seconds to wait after pressing S before the next warp
BLADE_WARP_PATH = [
    (938, 191, 0.5, 0.5),   # warp 1
    (1428, 269, 0.5, 0.5),
    (1551, 165, 0.5, 0.5),
    (1240, 120, 0.5, 0.5)
]

# Walk path from spawn to Anya portal.
# Each entry is (x, y, delay_seconds) — delay is how long to wait AFTER the click
# before moving to the next waypoint. Tune per-step as needed.
PORTAL_WALK_PATH = [
    (702, 730, 0.3),
    (638, 726, 0.3),
    (635, 743, 0.3),
    (870, 710, 0.5),
    (1309, 763, 0.6),
    (186, 848, 0.6),
    (476, 836, 0.6),
    (345, 768, 0.5),
    (260, 428, 0.5)
    # (418, 229, 2.76),  # portal
]


def log(msg):
    if VERBOSE:
        print(msg)


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
        log(f"ERROR: Template not found at '{template_path}'.")
        log("Run capture_template.py while in-game first.")
        sys.exit(1)

    # Scan the full bottom strip — template matching finds the cross wherever it is
    region = {"left": 0, "top": 900, "width": 1680, "height": 200}

    log("Waiting for game to load (watching for UI cross)...")
    while not template_visible(template, region):
        time.sleep(0.5)
    log("Game loaded — UI detected, in town.")


def walk_to_portal():
    """Click through the waypoint path to reach the Anya portal."""
    log(f"Walking to Anya portal ({len(PORTAL_WALK_PATH)} waypoints)...")
    time.sleep(1)
    for i, (x, y, delay) in enumerate(PORTAL_WALK_PATH, 1):
        log(f"  Waypoint {i}/{len(PORTAL_WALK_PATH)}: ({x}, {y}) — waiting {delay}s")
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(delay)
    log("Entered portal.")


def blade_warp_to_pindleskin():
    """Blade Warp through the temple to reach Pindleskin."""
    log(f"Blade Warping to Pindleskin ({len(BLADE_WARP_PATH)} warps)...")
    for i, (x, y, move_dur, delay) in enumerate(BLADE_WARP_PATH, 1):
        log(f"  Warp {i}/{len(BLADE_WARP_PATH)}: ({x}, {y})")
        pyautogui.moveTo(x, y, duration=move_dur)
        pyautogui.press("s")
        time.sleep(delay)
    log("Arrived at Pindleskin.")


def kill_pindleskin():
    """Fight Pindleskin: cast weakness sigil then alternate Abyss and Miasma Bolt."""
    log("Engaging Pindleskin...")
    pyautogui.moveTo(1047, 536, duration=0.3)

    # Cast lethargy sigil
    pyautogui.press("f5")
    time.sleep(0.2)

    # 7 rounds of Abyss (D) + 3x Miasma Bolt (F)
    for i in range(1, 7):
        log(f"  Attack round {i}/7")
        pyautogui.press("d")
        time.sleep(0.1)
        pyautogui.press("f")
        time.sleep(0.1)
        pyautogui.press("f")
        time.sleep(0.1)
        pyautogui.press("f")
        time.sleep(0.5)

    log("Pindleskin down. Check loot.")
    time.sleep(1.0)
    pyautogui.press("alt")


def loot_runes():
    """Capture a loot screenshot, save it, and pick up any rune found."""
    pyautogui.moveTo(200, 200, duration=0.2)
    time.sleep(0.2)

    os.makedirs(SCREENS_DIR, exist_ok=True)

    crop = {
        "left":   LOOT_CENTER_X - LOOT_WIDTH  // 2,
        "top":    LOOT_CENTER_Y - LOOT_HEIGHT // 2,
        "width":  LOOT_WIDTH,
        "height": LOOT_HEIGHT,
    }

    with mss.mss() as sct:
        raw = sct.grab(crop)
        img = np.array(raw)[:, :, :3]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENS_DIR, f"run_{timestamp}.png")
    cv2.imwrite(path, img)
    log(f"Saved loot screenshot: {path}")

    hits = find_runes(path)

    with open(RUN_LOG, "a") as f:
        f.write(f"{timestamp}  runes_found={len(hits)}\n")

    if not hits:
        log("No rune found.")
        return

    for cx, cy in hits:
        # Crop-local coords → absolute screen coords
        screen_x = crop["left"] + cx
        screen_y = crop["top"]  + cy
        log(f"Rune at crop ({cx}, {cy}) → screen ({screen_x}, {screen_y}) — picking up!")
        pyautogui.moveTo(screen_x, screen_y, duration=0.5)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(0.5)


def exit_game():
    """Press Escape to open the menu then click Save and Exit."""
    log("Exiting game...")
    pyautogui.press("escape")
    time.sleep(0.5)
    pyautogui.moveTo(819, 507, duration=0.4)
    pyautogui.click()
    log("Save and Exit clicked.")


def wait_for_play_button():
    """Block until the Play button is visible, indicating we're on character select."""
    template = cv2.imread("templates/play_button.png")
    region = {"left": 765, "top": 951, "width": 160, "height": 80}
    log("Waiting for character select screen (watching for Play button)...")
    while not template_visible(template, region):
        time.sleep(0.5)
    log("Character select screen detected.")


def run_once(run_number: int):
    """Execute one full Pindleskin farming run."""
    log(f"\n=== Run {run_number} ===")

    # Enter the game
    log("Pressing Enter to confirm character...")
    pyautogui.press("enter")
    time.sleep(STEP_DELAY)

    # Select Hell difficulty
    log("Pressing H for Hell difficulty...")
    pyautogui.press("h")
    pyautogui.moveTo(840, 525, duration=0.3)

    # Wait until the loading screen finishes and we're standing in town
    wait_for_game_load()

    log("Summon a pal")
    time.sleep(0.1)
    pyautogui.press("f8") # defiler
    log("Cast the healing thinger")
    time.sleep(0.1)
    pyautogui.press("f7") # healing hex thinger

    walk_to_portal()

    time.sleep(0.5)

    blade_warp_to_pindleskin()

    kill_pindleskin()

    loot_runes()

    log("Waiting 5 seconds before next game...")
    time.sleep(5)

    exit_game()


def main():
    log("Starting in 2 seconds — alt-tab to D2R now...")
    time.sleep(2)

    run_number = 1
    while True:
        run_once(run_number)
        run_number += 1
        wait_for_play_button()


if __name__ == "__main__":
    main()
