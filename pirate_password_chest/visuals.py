"""Fallback draw primitives and particles."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pygame

from .constants import (
    BLACK,
    GOLD,
    GOLD_DARK,
    OCEAN,
    OCEAN_DARK,
    ORANGE,
    SAND,
    SAND_DARK,
    SKY_BOTTOM,
    SKY_TOP,
    WHITE,
    WOOD,
    WOOD_DARK,
)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    life: float
    max_life: float
    color: tuple
    gravity: float = 0.0
    bounce: bool = False

    def update(self, dt):
        self.life -= dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.bounce and self.y > 465:
            self.y = 465
            self.vy *= -0.45
            self.vx *= 0.92

    def alive(self):
        return self.life > 0

    def draw(self, surface):
        alpha_ratio = max(0.0, self.life / max(self.max_life, 0.001))
        size = max(1, int(self.size * alpha_ratio))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), size)


def draw_palm(surface, x, y, scale=1.0, sway=0.0):
    trunk_w = int(30 * scale)
    trunk_h = int(130 * scale)
    pygame.draw.rect(surface, (143, 93, 46), (x, y - trunk_h, trunk_w, trunk_h), border_radius=8)

    top = (x + trunk_w // 2, y - trunk_h)
    for ang in [-80, -45, -15, 15, 45, 80]:
        length = int(90 * scale)
        theta = math.radians(ang + sway)
        end = (int(top[0] + math.cos(theta) * length), int(top[1] + math.sin(theta) * length))
        pygame.draw.line(surface, (45, 180, 80), top, end, int(16 * scale))


def draw_background(surface, width, height, t, wave_phase):
    for y in range(0, 250):
        p = y / 250
        color = (
            int(SKY_TOP[0] * (1 - p) + SKY_BOTTOM[0] * p),
            int(SKY_TOP[1] * (1 - p) + SKY_BOTTOM[1] * p),
            int(SKY_TOP[2] * (1 - p) + SKY_BOTTOM[2] * p),
        )
        pygame.draw.line(surface, color, (0, y), (width, y))

    pygame.draw.rect(surface, OCEAN, (0, 250, width, 180))
    for i in range(0, width, 40):
        yy = 278 + int(math.sin(wave_phase + i * 0.03) * 6)
        pygame.draw.arc(surface, OCEAN_DARK, (i, yy, 35, 14), 0, math.pi, 3)

    pygame.draw.rect(surface, SAND, (0, 430, width, 170))
    pygame.draw.ellipse(surface, SAND_DARK, (120, 410, 700, 120), width=0)

    pygame.draw.ellipse(surface, (61, 152, 95), (560, 230, 260, 50))

    pygame.draw.circle(surface, (255, 237, 105), (98, 92), 52)
    pygame.draw.circle(surface, (255, 250, 173), (98, 92), 30)

    ship_x = 700 + int(math.sin(t * 0.8) * 12)
    ship_y = 255 + int(math.sin(t * 1.6) * 3)
    pygame.draw.polygon(surface, (90, 55, 30), [(ship_x, ship_y), (ship_x + 84, ship_y), (ship_x + 60, ship_y + 18), (ship_x + 18, ship_y + 18)])
    pygame.draw.line(surface, (90, 55, 30), (ship_x + 42, ship_y - 42), (ship_x + 42, ship_y), 4)
    pygame.draw.polygon(surface, WHITE, [(ship_x + 42, ship_y - 40), (ship_x + 42, ship_y - 4), (ship_x + 74, ship_y - 22)])

    sway = math.sin(t * 2.2) * 5
    draw_palm(surface, 140, 385, 1.0, sway=sway)
    draw_palm(surface, 785, 398, 0.85, sway=-sway)


def draw_chest_fallback(surface, center, t, open_amount=0.0, shake=0.0):
    shake_x = int(random.uniform(-7, 7) * shake)
    shake_y = int(random.uniform(-5, 5) * shake)
    cx, cy = center[0] + shake_x, center[1] + shake_y

    base_rect = pygame.Rect(cx - 270, cy - 30, 540, 220)
    pygame.draw.rect(surface, WOOD, base_rect, border_radius=28)
    pygame.draw.rect(surface, WOOD_DARK, base_rect, width=8, border_radius=28)

    for px in range(base_rect.left + 24, base_rect.right - 20, 70):
        pygame.draw.line(surface, WOOD_DARK, (px, base_rect.top + 15), (px, base_rect.bottom - 14), 4)

    for yy in [base_rect.top + 35, base_rect.bottom - 45]:
        pygame.draw.rect(surface, GOLD, (base_rect.left + 14, yy, base_rect.width - 28, 22), border_radius=10)
        pygame.draw.rect(surface, GOLD_DARK, (base_rect.left + 14, yy, base_rect.width - 28, 22), width=4, border_radius=10)

    lid_h = 100
    lid_rect = pygame.Rect(cx - 270, cy - 110, 540, lid_h)
    lid_drop = int(open_amount * 52)
    lid_y = lid_rect.y - lid_drop

    pygame.draw.rect(surface, (150, 90, 44), (lid_rect.x, lid_y, lid_rect.w, lid_h), border_radius=24)
    pygame.draw.rect(surface, WOOD_DARK, (lid_rect.x, lid_y, lid_rect.w, lid_h), width=8, border_radius=24)

    for px in range(lid_rect.left + 24, lid_rect.right - 18, 65):
        pygame.draw.line(surface, WOOD_DARK, (px, lid_y + 8), (px, lid_y + lid_h - 8), 4)

    pygame.draw.rect(surface, GOLD, (lid_rect.x + 8, lid_y + 18, lid_rect.w - 16, 20), border_radius=10)
    pygame.draw.rect(surface, GOLD_DARK, (lid_rect.x + 8, lid_y + 18, lid_rect.w - 16, 20), width=4, border_radius=10)

    lock_x = cx
    lock_y = cy + 18
    pygame.draw.rect(surface, (250, 223, 95), (lock_x - 30, lock_y, 60, 70), border_radius=12)
    pygame.draw.rect(surface, GOLD_DARK, (lock_x - 30, lock_y, 60, 70), width=4, border_radius=12)
    pygame.draw.circle(surface, (210, 160, 45), (lock_x, lock_y + 35), 11)

    shimmer = int(8 + 4 * math.sin(t * 5.8))
    pygame.draw.circle(surface, WHITE, (lock_x + 17, lock_y + 18), max(1, shimmer // 3))


def draw_parrot_fallback(surface, x, y, t, emotion="happy"):
    wing_bob = int(math.sin(t * 9) * 10)
    blink = math.sin(t * 2.7) > 0.97

    pygame.draw.line(surface, (240, 160, 70), (x - 16, y + 66), (x - 14, y + 85), 5)
    pygame.draw.line(surface, (240, 160, 70), (x + 6, y + 66), (x + 8, y + 85), 5)

    pygame.draw.ellipse(surface, (58, 205, 95), (x - 62, y - 18, 128, 148))
    pygame.draw.ellipse(surface, (95, 230, 127), (x - 35, y + 18, 64, 86))

    wing_h = 66 + wing_bob
    pygame.draw.ellipse(surface, (36, 168, 82), (x - 90, y + 12, 50, wing_h))
    pygame.draw.ellipse(surface, (36, 168, 82), (x + 40, y + 12, 50, wing_h))

    pygame.draw.circle(surface, (62, 214, 100), (x, y - 24), 54)
    pygame.draw.ellipse(surface, (34, 34, 38), (x - 62, y - 82, 124, 34))
    pygame.draw.rect(surface, (40, 40, 46), (x - 42, y - 106, 84, 32), border_radius=8)
    pygame.draw.rect(surface, (220, 190, 70), (x - 7, y - 100, 14, 18), border_radius=4)

    pygame.draw.polygon(surface, ORANGE, [(x + 6, y - 20), (x + 54, y - 6), (x + 7, y + 8)])

    pygame.draw.circle(surface, WHITE, (x - 14, y - 38), 15)
    if blink:
        pygame.draw.line(surface, BLACK, (x - 24, y - 38), (x - 4, y - 38), 4)
    else:
        pygame.draw.circle(surface, BLACK, (x - 14, y - 38), 7)

    pygame.draw.circle(surface, BLACK, (x + 20, y - 38), 16)
    pygame.draw.line(surface, BLACK, (x + 4, y - 48), (x + 36, y - 28), 5)

    if emotion == "angry":
        pygame.draw.line(surface, BLACK, (x - 24, y - 55), (x - 5, y - 62), 5)
        pygame.draw.arc(surface, BLACK, (x - 20, y - 8, 35, 28), math.pi * 0.1, math.pi * 0.95, 4)
    elif emotion == "surprised":
        pygame.draw.circle(surface, BLACK, (x - 2, y - 6), 9)
    elif emotion == "cheer":
        pygame.draw.arc(surface, BLACK, (x - 26, y - 20, 44, 34), 0.1, math.pi - 0.1, 4)
        pygame.draw.arc(surface, BLACK, (x - 30, y - 46, 18, 11), math.pi, math.pi * 2, 3)
    else:
        pygame.draw.arc(surface, BLACK, (x - 21, y - 15, 35, 26), 0.15, math.pi - 0.15, 4)
