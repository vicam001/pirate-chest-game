"""Difficulty definitions and password generation."""

from __future__ import annotations

import random
from dataclasses import dataclass

from .constants import DIFFICULTY_ORDER


@dataclass(frozen=True)
class DifficultyConfig:
    key: str
    label: str
    length: int
    symbols: str
    description: str


class DifficultyManager:
    def __init__(self):
        self.configs = {
            "easy": DifficultyConfig(
                key="easy",
                label="Easy",
                length=4,
                symbols="0123456789",
                description="4-digit lock. Fast to crack.",
            ),
            "medium": DifficultyConfig(
                key="medium",
                label="Medium",
                length=6,
                symbols="0123456789",
                description="6-digit lock. Better, but still numbers only.",
            ),
            "hard": DifficultyConfig(
                key="hard",
                label="Hard",
                length=8,
                symbols="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$",
                description="8-char mixed lock. Much safer.",
            ),
        }

        self.tips = {
            "easy": [
                "1234? Every pirate starts there!",
                "Tiny 4-digit codes sink fast!",
                "Short number codes are easy treasure.",
                "Birthdays are pirate bait for hackers.",
            ],
            "medium": [
                "6 digits is better, but still all numbers!",
                "Numbers only means fewer possibilities.",
                "Patterns like 112233 are still weak.",
                "Longer helps, mixing helps even more!",
            ],
            "hard": [
                "Now that is a bigger code space!",
                "Letters, numbers, symbols: smart captain move!",
                "Random mixed characters are hardest to guess.",
                "Strong locks protect treasure and secrets.",
            ],
        }

    def get_config(self, difficulty: str) -> DifficultyConfig:
        return self.configs[difficulty]

    def next_difficulty(self, current: str) -> str:
        idx = DIFFICULTY_ORDER.index(current)
        return DIFFICULTY_ORDER[(idx + 1) % len(DIFFICULTY_ORDER)]

    def random_secret(self, difficulty: str) -> str:
        cfg = self.get_config(difficulty)
        return "".join(random.choice(cfg.symbols) for _ in range(cfg.length))

    def random_tip(self, difficulty: str) -> str:
        return random.choice(self.tips[difficulty])

    def code_space(self, difficulty: str) -> int:
        cfg = self.get_config(difficulty)
        return len(cfg.symbols) ** cfg.length

    def lesson_lines(self, difficulty: str):
        cfg = self.get_config(difficulty)
        space = self.code_space(difficulty)
        return [
            f"You cracked a {cfg.length}-character lock.",
            f"Code space size: {space:,} possible combinations.",
            "Strong passwords are long and mixed.",
            "Use letters + numbers + symbols together.",
            "Never use birthdays, names, or simple patterns.",
            "A password phrase is easier to remember and safer.",
        ]
