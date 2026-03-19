"""Main game coordinator."""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

from .constants import FPS, HEIGHT, TITLE, WIDTH
from .difficulty import DifficultyManager
from .managers import AudioManager, SaveManager, SpriteManager
from .scenes import BuilderScene, CrackScene, LandingScene, LessonScene, ParentReportScene
from .ui import FontBook


class PiratePasswordGame:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)

        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        self.fonts = FontBook()

        self.save_manager = SaveManager(self.root_dir)
        self.save_manager.increment_session()

        self.audio = AudioManager(self.root_dir, self.save_manager.settings)
        self.audio.play_music()

        self.sprite_manager = SpriteManager(self.root_dir)
        self.difficulty_manager = DifficultyManager()

        self.current_difficulty = "easy"
        self.last_round_result = None

        self.wave_phase = 0.0

        self.current_scene = None
        self.running = True

        self.switch_scene("landing")

    def switch_scene(self, name, payload=None):
        if name == "landing":
            self.current_scene = LandingScene(self)
        elif name == "crack":
            self.current_scene = CrackScene(self)
        elif name == "lesson":
            self.current_scene = LessonScene(self)
        elif name == "builder":
            self.current_scene = BuilderScene(self)
        elif name == "parent_report":
            self.current_scene = ParentReportScene(self)
        else:
            raise ValueError(f"Unknown scene: {name}")

        self.current_scene.enter(payload)

    def run(self):
        save_accum = 0.0
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.wave_phase += dt * 2.2
            self.save_manager.add_session_time(dt)
            save_accum += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                self.current_scene.handle_event(event)

            if not self.running:
                break

            self.current_scene.update(dt)
            self.current_scene.draw(self.screen)
            pygame.display.flip()

            if save_accum >= 1.0:
                self.save_manager.save()
                save_accum = 0.0

        self.save_manager.save()
        pygame.quit()
        sys.exit()
