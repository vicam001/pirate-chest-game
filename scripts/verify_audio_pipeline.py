#!/usr/bin/env python3
"""Verify generated audio assets are loaded and playable by the game."""

from __future__ import annotations

import time
from pathlib import Path
import sys

import pygame

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pirate_password_chest.game import PiratePasswordGame


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    root = ROOT
    required = [
        root / "assets/audio/music/island_loop.wav",
        root / "assets/audio/sfx/click.wav",
        root / "assets/audio/sfx/dial.wav",
        root / "assets/audio/sfx/clunk.wav",
        root / "assets/audio/sfx/success.wav",
        root / "assets/audio/sfx/confetti.wav",
        root / "assets/audio/sfx/reward.wav",
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert_true(not missing, f"Missing audio files: {missing}")

    game = PiratePasswordGame(root)
    audio = game.audio
    assert_true(audio.available, "Audio mixer is unavailable")

    # Verify music channel starts and all named SFX are present/playable.
    audio.play_music()
    pygame.time.wait(60)
    assert_true(audio.music_channel is not None and audio.music_channel.get_busy(), "Music did not start playing")

    expected_sfx = ["click", "dial", "clunk", "success", "confetti", "reward"]
    for name in expected_sfx:
        sound = audio.sfx.get(name)
        assert_true(sound is not None, f"SFX not loaded: {name}")
        assert_true(sound.get_length() > 0.0, f"SFX has zero length: {name}")
        audio.play_sfx(name)
        pygame.time.wait(40)

    assert_true(any(ch.get_busy() for ch in audio.sfx_channels), "No SFX channel became active")

    for _ in range(15):
        dt = game.clock.tick(60) / 1000.0
        game.wave_phase += dt * 2.2
        game.current_scene.update(dt)
        game.current_scene.draw(game.screen)
        pygame.display.flip()
        time.sleep(0.005)

    pygame.quit()
    print("AUDIO_PIPELINE_OK")


if __name__ == "__main__":
    main()
