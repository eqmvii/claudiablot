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
    (870, 710, 0.6),
    (1309, 763, 0.8),
    (186, 848, 0.8),
    (476, 836, 0.8),
    (345, 768, 0.8),
    (260, 428, 0.8)
    # (418, 229, 2.76),  # portal
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
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(0.2)
        pyautogui.click()
        time.sleep(delay)
    print("Entered portal.")


def blade_warp_to_pindleskin():
    """Blade Warp through the temple to reach Pindleskin."""
    print(f"Blade Warping to Pindleskin ({len(BLADE_WARP_PATH)} warps)...")
    for i, (x, y, move_dur, delay) in enumerate(BLADE_WARP_PATH, 1):
        print(f"  Warp {i}/{len(BLADE_WARP_PATH)}: ({x}, {y})")
        pyautogui.moveTo(x, y, duration=move_dur)
        pyautogui.press("s")
        time.sleep(delay)
    print("Arrived at Pindleskin.")


def kill_pindleskin():
    """Fight Pindleskin: cast weakness sigil then alternate Abyss and Miasma Bolt."""
    print("Engaging Pindleskin...")
    pyautogui.moveTo(1047, 536, duration=0.3)

    # Cast lethargy sigil
    pyautogui.press("f5")
    time.sleep(0.2)

    # 7 rounds of Abyss (D) + 3x Miasma Bolt (F)
    for i in range(1, 7):
        print(f"  Attack round {i}/7")
        pyautogui.press("d")
        time.sleep(0.1)
        pyautogui.press("f")
        time.sleep(0.1)
        pyautogui.press("f")
        time.sleep(0.1)
        pyautogui.press("f")
        time.sleep(0.5)

    print("Pindleskin down. Check loot.")
    time.sleep(1.0)
    pyautogui.press("alt")


def exit_game():
    """Press Escape to open the menu then click Save and Exit."""
    print("Exiting game...")
    pyautogui.press("escape")
    time.sleep(0.5)
    pyautogui.moveTo(819, 507, duration=0.4)
    pyautogui.click()
    print("Save and Exit clicked.")


def wait_for_play_button():
    """Block until the Play button is visible, indicating we're on character select."""
    template = cv2.imread("templates/play_button.png")
    region = {"left": 765, "top": 951, "width": 160, "height": 80}
    print("Waiting for character select screen (watching for Play button)...")
    while not template_visible(template, region):
        time.sleep(0.5)
    print("Character select screen detected.")


def run_once(run_number: int):
    """Execute one full Pindleskin farming run."""
    print(f"\n=== Run {run_number} ===")

    # Enter the game
    print("Pressing Enter to confirm character...")
    pyautogui.press("enter")
    time.sleep(STEP_DELAY)

    # Select Hell difficulty
    print("Pressing H for Hell difficulty...")
    pyautogui.press("h")
    pyautogui.moveTo(840, 525, duration=0.3)

    # Wait until the loading screen finishes and we're standing in town
    wait_for_game_load()

    print("Summon a pal")
    time.sleep(0.1)
    pyautogui.press("f8") # defiler
    print("Cast the healing thinger")
    time.sleep(0.1)
    pyautogui.press("f7") # healing hex thinger

    walk_to_portal()

    blade_warp_to_pindleskin()

    kill_pindleskin()

    print("Waiting 5 seconds for loot...")
    time.sleep(5)

    exit_game()


def main():
    print("Starting in 2 seconds — alt-tab to D2R now...")
    time.sleep(2)

    run_number = 1
    while True:
        run_once(run_number)
        run_number += 1
        wait_for_play_button()


if __name__ == "__main__":
    main()
