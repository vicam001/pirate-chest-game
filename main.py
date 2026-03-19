"""Entrypoint for Pirate Password Chest."""

from pathlib import Path

from pirate_password_chest import PiratePasswordGame


if __name__ == "__main__":
    game = PiratePasswordGame(root_dir=Path(__file__).resolve().parent)
    game.run()
