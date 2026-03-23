"""Main game coordinator."""

from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path

import pygame

from .constants import FPS, HEIGHT, TITLE, WIDTH
from .dialogue import CHARACTERS, DialogueManager
from .difficulty import DifficultyManager
from .managers import AudioManager, SaveManager, SpriteManager
from .presentation import PresentationController
from .scenes import (
    BuilderScene,
    CrackScene,
    FinaleScene,
    LandingScene,
    LessonScene,
    PasswordChallengeScene,
    ParentReportScene,
    StudioIntroScene,
    VoyageIntroScene,
)
from .ui import FontBook, draw_dialogue_panel, draw_text_outline
from .scroll_panel import ScrollPanel
from .virgil import Virgil


class PiratePasswordGame:
    def __init__(self, root_dir: str | Path, presentation: bool = False):
        self.root_dir = Path(root_dir)
        self.presentation_mode = presentation

        if not pygame.get_init():
            pygame.init()
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()

        # Virtual game canvas remains fixed; display can be fullscreen with letterboxing.
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.display_surface = pygame.display.get_surface() or pygame.display.set_mode((WIDTH, HEIGHT))
        self.render_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
        self._scaled_surface = None
        self._scaled_surface_size = None
        self._overlay_cache: dict[tuple[tuple[int, int, int], int], pygame.Surface] = {}

        self.fonts = FontBook()

        self.save_manager = SaveManager(self.root_dir)
        self.save_manager.increment_session()

        self.audio = AudioManager(self.root_dir, self.save_manager.settings)
        self.audio.play_music()

        self.sprite_manager = SpriteManager(self.root_dir)
        self.difficulty_manager = DifficultyManager()

        self.dialogue_manager = DialogueManager()

        # Virgil — the star character, shared across all scenes
        self.virgil = Virgil(x=700, y=350)

        # Ancient Pirate Scroll — single text display panel
        self.scroll = ScrollPanel()

        self.current_difficulty = "easy"
        self.last_round_result = None

        self.wave_phase = 0.0

        self.current_scene = None
        self.running = True

        # Scene transition fade
        self._fade_alpha = 0
        self._fade_direction = 0  # -1 fading out, 1 fading in, 0 none
        self._fade_speed = 600  # alpha per second
        self._pending_scene = None
        self._pending_payload = None

        # Presentation mode: fullscreen by default, create controller
        self.presentation: PresentationController | None = None
        if self.presentation_mode:
            self.fullscreen = sys.platform != "emscripten"
            self.presentation = PresentationController()
        else:
            self.fullscreen = bool(self.save_manager.settings.get("fullscreen", False))
            if sys.platform == "emscripten":
                self.fullscreen = False

        self.mouse_virtual_pos = (WIDTH // 2, HEIGHT // 2)
        self.mouse_inside_canvas = True
        self._apply_display_mode(self.fullscreen)

        if self.presentation and self.presentation.active:
            self.presentation.start(self)
        else:
            self.audio.stop_music()
            self.switch_scene("studio_intro")

    def _apply_display_mode(self, fullscreen: bool):
        self.fullscreen = bool(fullscreen)
        if sys.platform == "emscripten":
            self.display_surface = pygame.display.get_surface()
        elif self.fullscreen:
            flags = pygame.DOUBLEBUF | pygame.FULLSCREEN
            self.display_surface = pygame.display.set_mode((0, 0), flags)
        else:
            self.display_surface = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF)

        self._recompute_render_rect()

    def _recompute_render_rect(self):
        dw, dh = self.display_surface.get_size()
        scale = min(dw / WIDTH, dh / HEIGHT)
        rw = max(1, int(WIDTH * scale))
        rh = max(1, int(HEIGHT * scale))
        self.render_rect = pygame.Rect((dw - rw) // 2, (dh - rh) // 2, rw, rh)
        if self._scaled_surface_size != self.render_rect.size:
            self._scaled_surface = None
            self._scaled_surface_size = None

    def toggle_fullscreen(self):
        if sys.platform == "emscripten":
            return
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
        # If there's already a scene and no fade in progress, trigger a fade-out first
        if self.current_scene is not None and self._fade_direction == 0:
            self._pending_scene = name
            self._pending_payload = payload
            self._fade_direction = -1  # fade out
            self._fade_alpha = 0
            return

        # If a fade is already in progress, override the pending scene
        if self._fade_direction != 0 and self.current_scene is not None:
            self._pending_scene = name
            self._pending_payload = payload
            return

        self._do_switch_scene(name, payload)

    def _do_switch_scene(self, name, payload=None):
        self.scroll.collapsed = False  # each scene starts with full scroll
        if name == "studio_intro":
            self.current_scene = StudioIntroScene(self)
        elif name == "voyage_intro":
            self.current_scene = VoyageIntroScene(self)
        elif name == "landing":
            self.current_scene = LandingScene(self)
        elif name == "crack":
            self.current_scene = CrackScene(self)
        elif name == "lesson":
            self.current_scene = LessonScene(self)
        elif name == "builder":
            self.current_scene = PasswordChallengeScene(self)
        elif name == "parent_report":
            self.current_scene = ParentReportScene(self)
        elif name == "finale":
            self.current_scene = FinaleScene(self)
        else:
            raise ValueError(f"Unknown scene: {name}")

        self.current_scene.enter(payload)

        # Start fade-in
        self._fade_direction = 1
        self._fade_alpha = 255

        # Start dialogue sequence for this step if in presentation mode
        if self.presentation and self.presentation.active:
            step = self.presentation.current_step()
            if step and step.dialogue_on_enter:
                self.dialogue_manager.start(step.dialogue_on_enter)

    def _present_frame(self):
        self.display_surface.fill((8, 10, 22))
        if self.render_rect.size == (WIDTH, HEIGHT):
            self.display_surface.blit(self.screen, self.render_rect.topleft)
        else:
            self._scaled_surface = pygame.transform.smoothscale(self.screen, self.render_rect.size)
            self.display_surface.blit(self._scaled_surface, self.render_rect.topleft)

    def _get_overlay_surface(self, color, alpha):
        key = (tuple(color), int(alpha))
        overlay = self._overlay_cache.get(key)
        if overlay is None:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((*color, int(alpha)))
            self._overlay_cache[key] = overlay
            if len(self._overlay_cache) > 32:
                self._overlay_cache.clear()
                self._overlay_cache[key] = overlay
        return overlay

    async def run(self):
        save_accum = 0.0
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            await asyncio.sleep(0)
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

                # Presentation controller gets first crack at events
                if self.presentation and self.presentation.active:
                    # Advance dialogue on click/space when dialogue is active
                    if self.dialogue_manager.active:
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            self.dialogue_manager.advance()
                            continue
                        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RIGHT):
                            self.dialogue_manager.advance()
                            continue
                    elif self.presentation.handle_event(event, self):
                        continue

                self.current_scene.handle_event(event)

            if not self.running:
                break

            # Update dialogue manager
            self.dialogue_manager.update(dt)

            # Update Virgil animation
            self.virgil.update(dt)

            self.current_scene.update(dt)

            # Check if scene completed (for presentation auto-advance)
            if self.presentation and self.presentation.active:
                if hasattr(self.current_scene, 'completed') and self.current_scene.completed:
                    self.presentation.notify_scene_complete(self)

            self.current_scene.draw(self.screen)

            # Draw the Ancient Pirate Scroll on top of scene
            t = pygame.time.get_ticks() / 1000.0
            self.scroll.update(dt)
            self.scroll.draw(self.screen, t)

            # Draw presentation overlay (NEXT button, audience cues)
            if self.presentation and self.presentation.active and not self.dialogue_manager.active:
                t = pygame.time.get_ticks() / 1000.0
                self.presentation.draw_overlay(self.screen, self.fonts, t)

            # Draw dialogue panel on top if active
            if self.dialogue_manager.active:
                self._draw_dialogue_overlay()

            # Scene transition fade
            self._update_fade(dt)

            self._present_frame()
            pygame.display.flip()

            if save_accum >= 1.0:
                self.save_manager.save()
                save_accum = 0.0

        self.save_manager.save()
        pygame.quit()
        if sys.platform != "emscripten":
            sys.exit()

    def _update_fade(self, dt):
        if self._fade_direction == 0:
            return

        if self._fade_direction == -1:
            # Fading out (alpha increasing)
            self._fade_alpha = min(255, self._fade_alpha + int(self._fade_speed * dt))
            if self._fade_alpha >= 255:
                # Fully faded out -- switch scene
                self._fade_direction = 0
                if self._pending_scene:
                    name = self._pending_scene
                    payload = self._pending_payload
                    self._pending_scene = None
                    self._pending_payload = None
                    self._do_switch_scene(name, payload)
        elif self._fade_direction == 1:
            # Fading in (alpha decreasing)
            self._fade_alpha = max(0, self._fade_alpha - int(self._fade_speed * dt))
            if self._fade_alpha <= 0:
                self._fade_direction = 0

        if self._fade_alpha > 0:
            self.screen.blit(self._get_overlay_surface((0, 0, 0), self._fade_alpha), (0, 0))

    def _draw_dialogue_overlay(self):
        """Draw the current dialogue line as a large panel overlay."""
        line = self.dialogue_manager.current_line()
        if line is None:
            return

        char_info = CHARACTERS.get(line.character, {})
        char_name = char_info.get("name", line.character.title())
        char_color = char_info.get("color", (200, 200, 200))
        portrait = self.sprite_manager.get_portrait(line.character)

        # Semi-transparent overlay behind dialogue
        self.screen.blit(self._get_overlay_surface((0, 0, 0), 100), (0, 0))

        # Determine panel color tint based on character
        panel_bg = (
            min(255, char_color[0] // 3 + 200),
            min(255, char_color[1] // 3 + 200),
            min(255, char_color[2] // 3 + 180),
        )

        draw_dialogue_panel(
            self.screen, self.fonts,
            char_name, line.text,
            portrait=portrait,
            color=panel_bg,
            y=HEIGHT - 170,
        )

        # Character name in their color above the panel
        t = pygame.time.get_ticks() / 1000.0
        name_glow = (
            min(255, char_color[0] + 40),
            min(255, char_color[1] + 40),
            min(255, char_color[2] + 40),
        )
        draw_text_outline(
            self.screen, char_name, self.fonts.small,
            name_glow, (0, 0, 0),
            (WIDTH // 2, HEIGHT - 185), center=True,
        )

        # Audience cue if present
        if line.audience_cue and self.presentation_mode:
            self.presentation._draw_audience_cue(self.screen, line.audience_cue, t)

        # "Click to continue" hint with pulsing
        pulse = int(128 + 127 * math.sin(t * 3))
        draw_text_outline(
            self.screen,
            "Click or press SPACE to continue",
            self.fonts.tiny,
            (pulse, pulse, pulse),
            (0, 0, 0),
            (WIDTH // 2, HEIGHT - 10),
            center=True,
        )
