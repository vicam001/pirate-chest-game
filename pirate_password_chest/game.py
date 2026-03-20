"""Main game coordinator."""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

from .constants import FPS, HEIGHT, TITLE, WIDTH
from .difficulty import DifficultyManager
from .managers import AudioManager, SaveManager, SpriteManager
from .scenes import BuilderScene, CrackScene, LandingScene, LessonScene, ParentReportScene, VoyageIntroScene
from .ui import FontBook


class PiratePasswordGame:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)

        pygame.init()
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        # Virtual game canvas remains fixed; display can be fullscreen with letterboxing.
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.display_surface = None
        self.render_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)

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

        self.fullscreen = bool(self.save_manager.settings.get("fullscreen", False))
        self.mouse_virtual_pos = (WIDTH // 2, HEIGHT // 2)
        self.mouse_inside_canvas = True
        self._apply_display_mode(self.fullscreen)

        self.switch_scene("voyage_intro")

    def _apply_display_mode(self, fullscreen: bool):
        self.fullscreen = bool(fullscreen)
        flags = pygame.DOUBLEBUF
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
            self.display_surface = pygame.display.set_mode((0, 0), flags)
        else:
            self.display_surface = pygame.display.set_mode((WIDTH, HEIGHT), flags)

        self._recompute_render_rect()

    def _recompute_render_rect(self):
        dw, dh = self.display_surface.get_size()
        scale = min(dw / WIDTH, dh / HEIGHT)
        rw = max(1, int(WIDTH * scale))
        rh = max(1, int(HEIGHT * scale))
        self.render_rect = pygame.Rect((dw - rw) // 2, (dh - rh) // 2, rw, rh)

    def toggle_fullscreen(self):
        self._apply_display_mode(not self.fullscreen)
        self.save_manager.set_settings(fullscreen=self.fullscreen)

    def map_display_to_virtual(self, pos):
        rx, ry, rw, rh = self.render_rect
        if rw <= 0 or rh <= 0:
            return WIDTH // 2, HEIGHT // 2, True

        vx = int((pos[0] - rx) * WIDTH / rw)
        vy = int((pos[1] - ry) * HEIGHT / rh)
        inside = rx <= pos[0] <= rx + rw and ry <= pos[1] <= ry + rh
        return vx, vy, inside

    def _translate_mouse_event(self, event):
        if not hasattr(event, "pos"):
            return event

        vx, vy, inside = self.map_display_to_virtual(event.pos)
        event_dict = dict(event.dict)
        event_dict["pos"] = (vx, vy)
        event_dict["inside_canvas"] = inside

        if event.type == pygame.MOUSEMOTION and "rel" in event_dict:
            relx = int(event_dict["rel"][0] * WIDTH / max(1, self.render_rect.width))
            rely = int(event_dict["rel"][1] * HEIGHT / max(1, self.render_rect.height))
            event_dict["rel"] = (relx, rely)

        return pygame.event.Event(event.type, event_dict)

    def switch_scene(self, name, payload=None):
        if name == "voyage_intro":
            self.current_scene = VoyageIntroScene(self)
        elif name == "landing":
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

    def _present_frame(self):
        self.display_surface.fill((8, 10, 22))
        if self.render_rect.size == (WIDTH, HEIGHT):
            self.display_surface.blit(self.screen, self.render_rect.topleft)
        else:
            scaled = pygame.transform.smoothscale(self.screen, self.render_rect.size)
            self.display_surface.blit(scaled, self.render_rect.topleft)

    def run(self):
        save_accum = 0.0
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.wave_phase += dt * 2.2
            self.save_manager.add_session_time(dt)
            save_accum += dt

            mx, my, inside = self.map_display_to_virtual(pygame.mouse.get_pos())
            self.mouse_virtual_pos = (mx, my)
            self.mouse_inside_canvas = inside

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)):
                        self.toggle_fullscreen()
                        continue

                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    event = self._translate_mouse_event(event)

                self.current_scene.handle_event(event)

            if not self.running:
                break

            self.current_scene.update(dt)
            self.current_scene.draw(self.screen)
            self._present_frame()
            pygame.display.flip()

            if save_accum >= 1.0:
                self.save_manager.save()
                save_accum = 0.0

        self.save_manager.save()
        pygame.quit()
        sys.exit()
