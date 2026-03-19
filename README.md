# Pirate Password Chest - Arrr You Safe?

A colorful, kid-friendly Pygame mini-adventure that teaches password safety through pirate gameplay.

## Features in v2

- Scene-based game flow: Landing -> Crack -> Lesson -> Builder -> Parent Report
- Difficulty progression:
  - Easy: 4-character numeric
  - Medium: 6-character numeric
  - Hard: 8-character mixed (`A-Z`, `0-9`, `!@#$`)
- Real audio pipeline with fallback generated tones if audio files are missing
- Sprite-first animation pipeline with fallback procedural rendering
- Local progress save with stars, stickers, and round history
- Hidden Parent/Teacher mode (hold top-right corner for ~2 seconds)

## Main Commands

### 1) Create local virtual environment
```bash
python3.12 -m venv .venv
```

### 2) Install dependencies in the virtual environment
```bash
.venv/bin/python -m pip install pygame
```

### 3) Run the game
```bash
.venv/bin/python main.py
```

### 4) Syntax check
```bash
.venv/bin/python -m py_compile main.py pirate_password_chest/*.py
```

### 5) Headless smoke test (safe for CI/server)
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python - <<'PY'
from pathlib import Path
from pirate_password_chest.game import PiratePasswordGame
import pygame

game = PiratePasswordGame(Path.cwd())
for _ in range(180):
    dt = game.clock.tick(60) / 1000.0
    game.wave_phase += dt * 2.2
    game.current_scene.update(dt)
    game.current_scene.draw(game.screen)
    pygame.display.flip()
pygame.quit()
print("HEADLESS_SMOKE_OK")
PY
```

## Controls

- Mouse-only UI with large hitboxes
- Landing screen:
  - `PLAY`
  - `DIFFICULTY` (cycle easy/medium/hard)
  - `SETTINGS` (music/SFX sliders + mute + fullscreen)
- Fullscreen toggle:
  - Settings panel `FULL: ON/OFF`
  - Keyboard shortcut `F11` (or `Alt+Enter`)
- Crack screen:
  - Giant up/down arrows for each dial
  - `TRY!`, `HINT`, `LANDING`, `LESSON`
- Builder screen:
  - `ADD LETTER`, `ADD NUMBER`, `ADD SYMBOL`, `UNDO`, `CLEAR`, `DONE`

## Audio Assets (optional)

Drop real `.wav` files here to override fallback tones:

- `assets/audio/music/island_loop.wav`
- `assets/audio/sfx/click.wav`
- `assets/audio/sfx/dial.wav`
- `assets/audio/sfx/clunk.wav`
- `assets/audio/sfx/success.wav`
- `assets/audio/sfx/confetti.wav`
- `assets/audio/sfx/reward.wav`

## Save Data

- Save file: `data/progress.json`
- Auto-created on first launch
- Includes settings, stars, stickers, and round history

## Project Structure

- `main.py` - thin entrypoint
- `pirate_password_chest/` - game package (scenes/managers/ui/difficulty/visuals)
- `assets/` - character art plus optional audio/sprite assets
- `data/` - local progress save
