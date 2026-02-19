"""
record_walk.py

Records your walk to the Anya portal for use in bot.py.

Instructions:
1. Run this script in a Windows terminal:
       pip install pynput
       python record_walk.py
2. Alt-tab to D2R and walk to the portal by left-clicking as normal.
3. When you've clicked the portal and entered, press Escape in D2R
   (or switch back to the terminal and press Ctrl+C).

Output: walk_recording.md  — share this so bot.py can be updated.
"""

import time
from pynput import mouse, keyboard

clicks = []       # list of (x, y, timestamp)
recording = True


def on_click(x, y, button, pressed):
    if not pressed or button != mouse.Button.left:
        return
    t = time.time()
    clicks.append((x, y, t))
    idx = len(clicks)
    print(f"  [{idx}] ({x}, {y})")


def on_press(key):
    global recording
    if key == keyboard.Key.esc:
        recording = False
        return False  # stop keyboard listener


def save_recording():
    if not clicks:
        print("No clicks recorded.")
        return

    # Delay for waypoint N = time between click N and click N+1.
    # Last waypoint gets the same delay as the second-to-last (or 2s if only one click).
    delays = []
    for i in range(len(clicks) - 1):
        delays.append(round(clicks[i + 1][2] - clicks[i][2], 2))
    delays.append(delays[-1] if len(delays) > 0 else 2.0)

    lines = [
        "# Walk Recording\n",
        "Paste the `PORTAL_WALK_PATH` block below into `bot.py`.\n",
        "\n## Waypoint table\n",
        "| Step | X | Y | Delay after click (s) |\n",
        "|------|---|---|-----------------------|\n",
    ]
    for i, ((x, y, _), delay) in enumerate(zip(clicks, delays), 1):
        lines.append(f"| {i} | {x} | {y} | {delay} |\n")

    lines.append("\n## bot.py snippet\n")
    lines.append("```python\n")
    lines.append("PORTAL_WALK_PATH = [\n")
    for (x, y, _), delay in zip(clicks, delays):
        lines.append(f"    ({x}, {y}, {delay}),\n")
    lines.append("]\n")
    lines.append("```\n")

    with open("walk_recording.md", "w") as f:
        f.writelines(lines)

    print(f"\nSaved walk_recording.md  ({len(clicks)} waypoints)")


def main():
    print("Recording started — left-click your way to the portal in D2R.")
    print("Press Escape (in-game or terminal) to stop and save.\n")

    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()
    keyboard_listener.join()   # block until Escape
    mouse_listener.stop()

    save_recording()


if __name__ == "__main__":
    main()
