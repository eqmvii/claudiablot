# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This project is a single-player Diablo II Resurrected Pindleskin farming bot. "Pindleskin" is a boss in Diablo II Act V accessible via the Anya portal in Harrogath, commonly farmed for high-quality item drops.

## Diablo Item Color Information for OCR

Diablo items text can have following colors:

Normal (White)
Magic (Blue)
Rare (Yellow)
Unique (Gold)
Set (Green)
Grey (Grey)
Rune (Orange)

A note on grey: these are either socketed or ethereal. We'll just call them Grey, since we can't tell while the item is on the ground.

## Message Logging (REQUIRED)

**Every time the user sends a message, append a timestamped entry with the full message text to `log.md` in the repo root.** Do this before or alongside any other response. Use the format:

```
## YYYY-MM-DD HH:MM:SS UTC

<full user message here>
```

Get the timestamp via `date -u +"%Y-%m-%d %H:%M:%S UTC"`.

## Project Status

We have a good gameplay loop going. The next step is going to be reading item names from screenshots. 