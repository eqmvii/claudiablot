# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This project is a single-player Diablo II Pindleskin farming bot driven by Claude Code. "Pindleskin" is a boss in Diablo II Act V accessible via the Anya portal in Harrogath, commonly farmed for high-quality item drops.

## Message Logging (REQUIRED)

**Every time the user sends a message, append a timestamped entry with the full message text to `log.md` in the repo root.** Do this before or alongside any other response. Use the format:

```
## YYYY-MM-DD HH:MM:SS UTC

<full user message here>
```

Get the timestamp via `date -u +"%Y-%m-%d %H:%M:%S UTC"`.

## Project Status

The repository is newly initialized. No build system, dependencies, or source files have been established yet. When implementing, update this file with:
- Build/run commands
- Language and framework choices
- Architecture overview
- How to run tests
