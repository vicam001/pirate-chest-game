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
                length=1,
                symbols="0123456789",
                description="1-digit lock. Super easy to crack.",
            ),
            "medium": DifficultyConfig(
                key="medium",
                label="Medium",
                length=2,
                symbols="0123456789",
                description="2-digit lock. A bit stronger.",
            ),
            "hard": DifficultyConfig(
                key="hard",
                label="Hard",
                length=3,
                symbols="0123456789",
                description="3-digit lock. Stronger again.",
            ),
            "expert": DifficultyConfig(
                key="expert",
                label="Expert",
                length=4,
                symbols="0123456789",
                description="4-digit lock. Toughest in this mode.",
            ),
        }

        self.tips = {
            "easy": [
                "One digit? Any pirate can brute-force that!",
                "Single-digit locks open in no time!",
                "Shorter locks are always easier to crack.",
                "Let's try a bigger lock next!",
            ],
            "medium": [
                "Two digits is better than one!",
                "More digits means more possibilities.",
                "Keep climbing for stronger locks.",
                "Every extra digit helps protect treasure.",
            ],
            "hard": [
                "Three digits makes guessing much harder!",
                "Nice progress, captain.",
                "Longer locks defend treasure better.",
                "One more step to the toughest lock!",
            ],
            "expert": [
                "Four digits: toughest chest in this adventure!",
                "Now that is a much bigger code space.",
                "Great work leveling up your lock strength.",
                "Longer secrets keep pirates guessing.",
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
            f"You cracked a {cfg.length}-digit lock.",
            f"Code space size: {space:,} possible combinations.",
            "Longer locks are stronger than short ones.",
            "Each extra digit makes guessing harder.",
            "Avoid simple patterns like 1111 or 1234.",
            "Use long, mixed passwords for real accounts.",
        ]
