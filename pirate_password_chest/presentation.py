"""Presentation mode controller for science fair guided flow."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from .constants import BLACK, HEIGHT, WHITE, WIDTH, YELLOW
from .dialogue import (
    BUILDER_INTRO_PRESENTATION,
    CRACK_INTRO_PRESENTATION,
    CRACK_SUCCESS,
    FINALE_DIALOGUE,
    LESSON_DIALOGUE,
    TITLE_DIALOGUE,
    DialogueSequence,
)
from .ui import draw_text_outline


@dataclass
class PresentationStep:
    scene_name: str
    payload: dict | None = None
    dialogue_on_enter: DialogueSequence | None = None
    auto_advance_seconds: float = 0  # 0 = manual only
    audience_cue: str | None = None
    wait_for_scene_complete: bool = False


def build_presentation_script() -> list[PresentationStep]:
    """Build the full scripted flow for presentation mode."""
    return [
        # Step 0: Title slide (part of voyage_intro)
        PresentationStep(
            scene_name="voyage_intro",
            payload={"presentation_phase": "title"},
            dialogue_on_enter=TITLE_DIALOGUE,
        ),
        # Step 1: Voyage with questions
        PresentationStep(
            scene_name="voyage_intro",
            payload={"presentation_phase": "voyage"},
            wait_for_scene_complete=True,
        ),
        # Step 2: Crack the lock (Easy)
        PresentationStep(
            scene_name="crack",
            payload={"force_difficulty": "easy"},
            dialogue_on_enter=CRACK_INTRO_PRESENTATION,
            wait_for_scene_complete=True,
        ),
        # Step 3: Lesson
        PresentationStep(
            scene_name="lesson",
            dialogue_on_enter=LESSON_DIALOGUE,
        ),
        # Step 4: Build a password
        PresentationStep(
            scene_name="builder",
            dialogue_on_enter=BUILDER_INTRO_PRESENTATION,
            wait_for_scene_complete=True,
        ),
        # Step 5: Finale
        PresentationStep(
            scene_name="finale",
            dialogue_on_enter=FINALE_DIALOGUE,
        ),
    ]


class PresentationController:
    """Manages step-by-step progression through the presentation."""

    def __init__(self) -> None:
        self.steps = build_presentation_script()
        self.current_step_index = 0
        self.active = True
        self.waiting_for_scene = False
        # The NEXT button rect (drawn by scenes / game)
        self.next_button_rect = pygame.Rect(WIDTH - 200, HEIGHT - 70, 180, 54)
        self.next_hovered = False

    def current_step(self) -> PresentationStep | None:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance(self, game) -> None:
        """Move to the next step, loading the appropriate scene."""
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps):
            self.active = False
            return
        step = self.current_step()
        if step is None:
            self.active = False
            return
        self.waiting_for_scene = step.wait_for_scene_complete
        game.switch_scene(step.scene_name, step.payload)

    def start(self, game) -> None:
        """Begin the presentation from step 0."""
        self.current_step_index = 0
        self.active = True
        step = self.current_step()
        if step:
            self.waiting_for_scene = step.wait_for_scene_complete
            game.switch_scene(step.scene_name, step.payload)

    def handle_event(self, event, game) -> bool:
        """Handle NEXT button click and keyboard shortcuts. Returns True if consumed."""
        if not self.active:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RIGHT, pygame.K_SPACE):
                # Don't auto-advance if waiting for scene completion
                if not self.waiting_for_scene:
                    self.advance(game)
                    return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.next_button_rect.collidepoint(event.pos):
                if not self.waiting_for_scene:
                    self.advance(game)
                    return True

        if event.type == pygame.MOUSEMOTION:
            self.next_hovered = self.next_button_rect.collidepoint(event.pos)

        return False

    def notify_scene_complete(self, game) -> None:
        """Called by scenes when they signal completion."""
        if self.waiting_for_scene:
            self.waiting_for_scene = False

    def draw_overlay(self, screen, fonts, t: float) -> None:
        """Draw the NEXT button and any audience cue on top of the scene."""
        if not self.active:
            return

        step = self.current_step()
        if step is None:
            return

        # Audience cue banner
        audience_cue = step.audience_cue
        # Check if the current scene's dialogue has an audience cue
        if audience_cue:
            self._draw_audience_cue(screen, audience_cue, t)

        # NEXT button
        if not self.waiting_for_scene:
            self._draw_next_button(screen, fonts, t)
        else:
            # Show a subtle "waiting..." indicator
            pulse = int(abs(math.sin(t * 2)) * 80) + 80
            draw_text_outline(
                screen,
                "Playing...",
                fonts.tiny,
                (pulse, pulse, pulse),
                BLACK,
                (WIDTH - 110, HEIGHT - 42),
                center=True,
            )

    def _draw_next_button(self, screen, fonts, t: float) -> None:
        rect = self.next_button_rect
        inflate = int(3 * math.sin(t * 4))
        draw_rect = rect.inflate(inflate, inflate)

        color = (60, 180, 80) if self.next_hovered else (50, 160, 70)
        glow = (140, 255, 160) if self.next_hovered else (120, 230, 140)

        pygame.draw.rect(screen, glow, draw_rect.inflate(8, 8), border_radius=18)
        pygame.draw.rect(screen, color, draw_rect, border_radius=16)
        pygame.draw.rect(screen, BLACK, draw_rect, width=3, border_radius=16)
        draw_text_outline(screen, "NEXT >>", fonts.small, WHITE, BLACK, draw_rect.center, center=True)

    def _draw_audience_cue(self, screen, text: str, t: float) -> None:
        """Draw a pulsing banner at bottom of screen."""
        pulse = 0.7 + 0.3 * abs(math.sin(t * 3))
        banner_h = 64
        banner = pygame.Surface((WIDTH, banner_h), pygame.SRCALPHA)

        bg_alpha = int(220 * pulse)
        banner.fill((255, 235, 59, bg_alpha))
        pygame.draw.rect(banner, (245, 127, 23), (0, 0, WIDTH, banner_h), width=4)

        screen.blit(banner, (0, HEIGHT - banner_h - 70))

        # Hand icon (simple procedural)
        hand_x, hand_y = 60, HEIGHT - banner_h - 70 + banner_h // 2
        bob = int(math.sin(t * 5) * 4)
        pygame.draw.circle(screen, (245, 127, 23), (hand_x, hand_y + bob), 18)
        pygame.draw.rect(screen, (245, 127, 23), (hand_x - 4, hand_y + bob - 30, 8, 20))

        draw_text_outline(
            screen,
            text,
            pygame.font.SysFont("comicsansms", 36, bold=True),
            BLACK,
            YELLOW,
            (WIDTH // 2, HEIGHT - banner_h - 70 + banner_h // 2),
            center=True,
        )

    def is_finished(self) -> bool:
        return not self.active
