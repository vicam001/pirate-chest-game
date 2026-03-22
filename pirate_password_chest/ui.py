"""UI primitives for big child-friendly controls."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from .constants import (
    BLACK,
    BLUE,
    FONT_BIG_SIZE,
    FONT_HUGE_SIZE,
    FONT_MED_SIZE,
    FONT_NAME,
    FONT_SMALL_SIZE,
    FONT_TINY_SIZE,
    WHITE,
    YELLOW,
)


class FontBook:
    def __init__(self) -> None:
        self.huge = pygame.font.SysFont(FONT_NAME, FONT_HUGE_SIZE, bold=True)
        self.big = pygame.font.SysFont(FONT_NAME, FONT_BIG_SIZE, bold=True)
        self.med = pygame.font.SysFont(FONT_NAME, FONT_MED_SIZE, bold=True)
        self.small = pygame.font.SysFont(FONT_NAME, FONT_SMALL_SIZE, bold=True)
        self.tiny = pygame.font.SysFont(FONT_NAME, FONT_TINY_SIZE, bold=True)


def draw_text_outline(surface, text, font, color, outline, pos, center=True):
    base = font.render(text, True, color)
    outline_surf = font.render(text, True, outline)

    if center:
        rect = base.get_rect(center=pos)
    else:
        rect = base.get_rect(topleft=pos)

    for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
        surface.blit(outline_surf, rect.move(ox, oy))
    surface.blit(base, rect)
    return rect


def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if font.size(test)[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


class Button:
    def __init__(self, rect, label, color, hover, text_color=WHITE, pulse=True):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.hover = hover
        self.text_color = text_color
        self.pulse = pulse
        self.visible = True
        self.enabled = True

    def draw(self, surface, fonts: FontBook, t, mouse_pos=None):
        if not self.visible:
            return

        mouse = mouse_pos if mouse_pos is not None else pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse)
        color = self.hover if hovered and self.enabled else self.color

        inflate = int(4 * math.sin(t * 5)) if self.pulse else 0
        draw_rect = self.rect.inflate(inflate, inflate)

        glow = (255, 230, 110) if hovered else (255, 206, 90)
        if not self.enabled:
            glow = (160, 160, 160)
            color = (120, 120, 120)

        pygame.draw.rect(surface, glow, draw_rect.inflate(10, 10), border_radius=22)
        pygame.draw.rect(surface, color, draw_rect, border_radius=20)
        pygame.draw.rect(surface, BLACK, draw_rect, width=4, border_radius=20)
        draw_text_outline(surface, self.label, fonts.med, self.text_color, BLACK, draw_rect.center, center=True)

    def clicked(self, pos):
        return self.visible and self.enabled and self.rect.collidepoint(pos)


class Slider:
    def __init__(self, rect, label, initial=0.5):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = max(0.0, min(1.0, initial))
        self.dragging = False

    @property
    def handle_x(self):
        return int(self.rect.left + self.value * self.rect.width)

    def draw(self, surface, fonts: FontBook):
        draw_text_outline(surface, self.label, fonts.small, YELLOW, BLACK, (self.rect.centerx, self.rect.top - 24), center=True)
        pygame.draw.rect(surface, (40, 70, 90), self.rect.inflate(8, 8), border_radius=14)
        pygame.draw.rect(surface, (100, 190, 220), self.rect, border_radius=12)

        fill_rect = pygame.Rect(self.rect.left, self.rect.top, int(self.rect.width * self.value), self.rect.height)
        if fill_rect.width > 0:
            pygame.draw.rect(surface, BLUE, fill_rect, border_radius=12)

        handle_center = (self.handle_x, self.rect.centery)
        pygame.draw.circle(surface, WHITE, handle_center, 16)
        pygame.draw.circle(surface, BLACK, handle_center, 16, width=3)

        pct = int(self.value * 100)
        draw_text_outline(surface, f"{pct}%", fonts.tiny, WHITE, BLACK, (self.rect.right + 52, self.rect.centery), center=True)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.inflate(18, 16).collidepoint(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])
            return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            self._set_from_x(event.pos[0])
            return True
        return False

    def _set_from_x(self, x):
        self.value = (x - self.rect.left) / max(1, self.rect.width)
        self.value = max(0.0, min(1.0, self.value))


@dataclass
class DialLayout:
    x: int
    y: int
    radius: int


class DialWheel:
    def __init__(self, symbols: str, layout: DialLayout):
        self.symbols = list(symbols)
        self.layout = layout
        self.index = 0
        self.from_index = 0
        self.to_index = 0
        self.direction = 1
        self.progress = 0.0
        self.animating = False
        self.up_rect = pygame.Rect(layout.x - 42, layout.y - 110, 84, 64)
        self.down_rect = pygame.Rect(layout.x - 42, layout.y + 56, 84, 64)

    def reset(self):
        self.index = 0
        self.from_index = 0
        self.to_index = 0
        self.direction = 1
        self.progress = 0.0
        self.animating = False

    def set_symbol(self, symbol):
        if symbol in self.symbols:
            self.index = self.symbols.index(symbol)
            self.to_index = self.index
            self.from_index = self.index
            self.animating = False

    def current_symbol(self):
        idx = self.to_index if self.animating else self.index
        return self.symbols[idx]

    def increment(self, delta):
        current = self.to_index if self.animating else self.index
        self.from_index = current
        self.to_index = (current + delta) % len(self.symbols)
        self.direction = 1 if delta > 0 else -1
        self.progress = 0.0
        self.animating = True

    def update(self, dt):
        if not self.animating:
            return
        self.progress += dt / 0.14
        if self.progress >= 1.0:
            self.progress = 1.0
            self.index = self.to_index
            self.animating = False

    def draw(self, surface, fonts: FontBook):
        x = self.layout.x
        y = self.layout.y
        radius = self.layout.radius

        outer = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
        pygame.draw.circle(surface, (220, 235, 250), (x, y), radius)
        pygame.draw.circle(surface, (168, 196, 218), (x, y), radius, width=8)
        pygame.draw.circle(surface, WHITE, (x, y), radius - 8)
        pygame.draw.rect(surface, BLACK, outer, width=4, border_radius=40)

        clip = pygame.Rect(x - radius + 8, y - radius + 8, radius * 2 - 16, radius * 2 - 16)
        old_clip = surface.get_clip()
        surface.set_clip(clip)

        if self.animating:
            p = self.progress
            step = radius * 2
            old_symbol = self.symbols[self.from_index]
            new_symbol = self.symbols[self.to_index]
            if self.direction > 0:
                old_y = y - p * step
                new_y = y + (1 - p) * step
            else:
                old_y = y + p * step
                new_y = y - (1 - p) * step
            draw_text_outline(surface, old_symbol, fonts.huge, BLUE, BLACK, (x, int(old_y)), center=True)
            draw_text_outline(surface, new_symbol, fonts.huge, BLUE, BLACK, (x, int(new_y)), center=True)
        else:
            draw_text_outline(surface, self.symbols[self.index], fonts.huge, BLUE, BLACK, (x, y), center=True)

        surface.set_clip(old_clip)

        for rect, up in ((self.up_rect, True), (self.down_rect, False)):
            pygame.draw.rect(surface, (255, 255, 196), rect.inflate(8, 8), border_radius=20)
            pygame.draw.rect(surface, (255, 190, 64), rect, border_radius=18)
            pygame.draw.rect(surface, BLACK, rect, width=4, border_radius=18)
            if up:
                points = [(rect.centerx, rect.top + 12), (rect.left + 16, rect.bottom - 12), (rect.right - 16, rect.bottom - 12)]
            else:
                points = [(rect.centerx, rect.bottom - 12), (rect.left + 16, rect.top + 12), (rect.right - 16, rect.top + 12)]
            pygame.draw.polygon(surface, (103, 55, 16), points)


def draw_panel(surface, rect, bg_color=(255, 243, 203), border_color=(70, 45, 22)):
    pygame.draw.rect(surface, bg_color, rect, border_radius=24)
    pygame.draw.rect(surface, border_color, rect, width=6, border_radius=24)


def draw_dialogue_panel(surface, fonts, character_name, text, portrait=None,
                        color=(255, 243, 203), y=None, width_pct=0.85):
    """Draw a large dialogue panel with character portrait and text.

    Designed for readability on a projector -- wider, taller, larger text.
    """
    from .constants import HEIGHT, WIDTH as SCREEN_WIDTH

    panel_w = int(SCREEN_WIDTH * width_pct)
    panel_h = 140
    panel_x = (SCREEN_WIDTH - panel_w) // 2
    panel_y = y if y is not None else HEIGHT - panel_h - 20

    rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
    draw_panel(surface, rect, bg_color=color, border_color=(70, 45, 22))

    # Portrait circle
    portrait_x = panel_x + 80
    portrait_y = panel_y + panel_h // 2
    if portrait is not None:
        pr = portrait.get_rect(center=(portrait_x, portrait_y))
        # Clip to circle
        pygame.draw.circle(surface, (70, 45, 22), (portrait_x, portrait_y), 52, width=4)
        surface.blit(portrait, pr)
    else:
        pygame.draw.circle(surface, (200, 200, 200), (portrait_x, portrait_y), 48)
        pygame.draw.circle(surface, (70, 45, 22), (portrait_x, portrait_y), 48, width=3)

    # Character name
    name_x = portrait_x + 70
    draw_text_outline(surface, character_name, fonts.tiny, YELLOW, BLACK,
                      (name_x, panel_y + 22), center=False)

    # Text (wrapped)
    text_x = name_x
    text_max_w = panel_w - (text_x - panel_x) - 30
    lines = wrap_text(text, fonts.small, text_max_w)
    yy = panel_y + 52
    for line in lines[:3]:
        draw_text_outline(surface, line, fonts.small, BLACK, WHITE,
                          (text_x, yy), center=False)
        yy += 34
