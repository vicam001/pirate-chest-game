"""Entrypoint for Pirate Password Chest."""

import asyncio
import sys
from pathlib import Path

from pirate_password_chest import PiratePasswordGame


async def main():
    presentation = False
    if sys.platform != "emscripten":
        import argparse

        parser = argparse.ArgumentParser(description="Pirate Password Chest Game")
        parser.add_argument(
            "--presentation",
            action="store_true",
            help="Run in guided presentation mode for science fair (fullscreen, auto-guided flow)",
        )
        args = parser.parse_args()
        presentation = args.presentation

    if sys.platform == "emscripten":
        root_dir = Path(".")
    else:
        root_dir = Path(__file__).resolve().parent

    game = PiratePasswordGame(
        root_dir=root_dir,
        presentation=presentation,
    )
    await game.run()


asyncio.run(main())
