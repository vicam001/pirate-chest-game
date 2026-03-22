"""Entrypoint for Pirate Password Chest."""

import argparse
from pathlib import Path

from pirate_password_chest import PiratePasswordGame


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pirate Password Chest Game")
    parser.add_argument(
        "--presentation",
        action="store_true",
        help="Run in guided presentation mode for science fair (fullscreen, auto-guided flow)",
    )
    args = parser.parse_args()

    game = PiratePasswordGame(
        root_dir=Path(__file__).resolve().parent,
        presentation=args.presentation,
    )
    game.run()
