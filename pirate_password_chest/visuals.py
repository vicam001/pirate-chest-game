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


_sky_gradient_cache: pygame.Surface | None = None
_sky_gradient_size: tuple[int, int] = (0, 0)


def draw_background(surface, width, height, t, wave_phase):
    global _sky_gradient_cache, _sky_gradient_size
    if _sky_gradient_cache is None or _sky_gradient_size != (width, 250):
        _sky_gradient_cache = pygame.Surface((width, 250))
        for y in range(0, 250):
            p = y / 250
            color = (
                int(SKY_TOP[0] * (1 - p) + SKY_BOTTOM[0] * p),
                int(SKY_TOP[1] * (1 - p) + SKY_BOTTOM[1] * p),
                int(SKY_TOP[2] * (1 - p) + SKY_BOTTOM[2] * p),
            )
            pygame.draw.line(_sky_gradient_cache, color, (0, y), (width, y))
        _sky_gradient_size = (width, 250)
    surface.blit(_sky_gradient_cache, (0, 0))

    pygame.draw.rect(surface, OCEAN, (0, 250, width, 180))
    for i in range(0, width, 40):
        yy = 278 + int(math.sin(wave_phase + i * 0.03) * 6)
        pygame.draw.arc(surface, OCEAN_DARK, (i, yy, 35, 14), 0, math.pi, 3)

    pygame.draw.rect(surface, SAND, (0, 430, width, 170))
    pygame.draw.ellipse(surface, SAND_DARK, (120, 410, 700, 120), width=0)

    pygame.draw.ellipse(surface, (61, 152, 95), (560, 230, 260, 50))

    pygame.draw.circle(surface, (255, 237, 105), (98, 92), 52)
    pygame.draw.circle(surface, (255, 250, 173), (98, 92), 30)

    # Stars in the sky
    for i, (sx, sy) in enumerate([(50, 42), (160, 28), (310, 14), (510, 20), (680, 35), (820, 22), (870, 55)]):
        star_pulse = abs(math.sin(t * 1.8 + i * 0.7)) * 0.6 + 0.4
        star_radius = int(3 * star_pulse)
        if star_radius > 0:
            pygame.draw.circle(surface, (255, 255, 240), (sx, sy), star_radius)
            pygame.draw.circle(surface, (255, 255, 200), (sx, sy), max(1, star_radius - 1))

    ship_x = 700 + int(math.sin(t * 0.8) * 12)
    ship_y = 255 + int(math.sin(t * 1.6) * 3)
    pygame.draw.polygon(surface, (90, 55, 30), [(ship_x, ship_y), (ship_x + 84, ship_y), (ship_x + 60, ship_y + 18), (ship_x + 18, ship_y + 18)])
    pygame.draw.line(surface, (90, 55, 30), (ship_x + 42, ship_y - 42), (ship_x + 42, ship_y), 4)
    pygame.draw.polygon(surface, WHITE, [(ship_x + 42, ship_y - 40), (ship_x + 42, ship_y - 4), (ship_x + 74, ship_y - 22)])

    sway = math.sin(t * 2.2) * 5
    draw_palm(surface, 140, 385, 1.0, sway=sway)
    draw_palm(surface, 785, 398, 0.85, sway=-sway)


def draw_spanish_gold_coin(surface, center, radius, t, stamp_phase=0.0):
    cx, cy = int(center[0]), int(center[1])
    radius = max(4, int(radius))
    pygame.draw.circle(surface, (235, 174, 42), (cx, cy), radius)
    pygame.draw.circle(surface, GOLD, (cx, cy), max(2, int(radius * 0.86)))
    pygame.draw.circle(surface, (255, 233, 143), (cx, cy), max(1, int(radius * 0.58)))
    pygame.draw.circle(surface, GOLD_DARK, (cx, cy), radius, width=max(1, radius // 6))
    pygame.draw.circle(surface, (175, 114, 19), (cx, cy), max(2, int(radius * 0.38)), width=max(1, radius // 10))
    pygame.draw.line(
        surface,
        GOLD_DARK,
        (cx - int(radius * 0.2), cy - int(radius * 0.2)),
        (cx + int(radius * 0.2), cy + int(radius * 0.2)),
        max(1, radius // 9),
    )
    pygame.draw.line(
        surface,
        GOLD_DARK,
        (cx - int(radius * 0.2), cy + int(radius * 0.2)),
        (cx + int(radius * 0.2), cy - int(radius * 0.2)),
        max(1, radius // 9),
    )

    glint_angle = t * 3.7 + stamp_phase
    glint_x = cx + int(math.cos(glint_angle) * radius * 0.48)
    glint_y = cy - int(radius * 0.42 + abs(math.sin(glint_angle * 1.2)) * radius * 0.14)
    pygame.draw.circle(surface, WHITE, (glint_x, glint_y), max(1, radius // 5))


def draw_chest_fallback(
    surface,
    center,
    t,
    open_amount=0.0,
    shake=0.0,
    lock_unlocked=False,
    lock_drop=0.0,
    show_coins=False,
    coin_shimmer=0.0,
):
    open_amount = max(0.0, min(1.0, float(open_amount)))
    lock_drop = max(0.0, min(1.0, float(lock_drop)))
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

    if open_amount > 0.14 or show_coins:
        cavity = pygame.Rect(base_rect.left + 26, base_rect.top + 8, base_rect.width - 52, 92)
        pygame.draw.rect(surface, (78, 47, 22), cavity, border_radius=18)
        pygame.draw.rect(surface, (115, 66, 28), cavity, width=3, border_radius=18)

        rows = 4
        cols = 9
        for row in range(rows):
            for col in range(cols):
                jitter = math.sin((row * 0.6) + (col * 0.7) + coin_shimmer * 5.5 + t * 2.2)
                coin_x = cavity.left + 40 + col * 54 + int(jitter * 2)
                coin_y = cavity.bottom - 12 - row * 18 - int(abs(jitter) * 3)
                coin_radius = 13 - row
                draw_spanish_gold_coin(surface, (coin_x, coin_y), coin_radius, t + (row * 0.21), stamp_phase=col * 0.55)

    lid_h = 100
    lid_rect = pygame.Rect(cx - 270, cy - 110, 540, lid_h)
    lid_drop = int(open_amount * 84)
    lid_y = lid_rect.y - lid_drop

    pygame.draw.rect(surface, (150, 90, 44), (lid_rect.x, lid_y, lid_rect.w, lid_h), border_radius=24)
    pygame.draw.rect(surface, WOOD_DARK, (lid_rect.x, lid_y, lid_rect.w, lid_h), width=8, border_radius=24)

    for px in range(lid_rect.left + 24, lid_rect.right - 18, 65):
        pygame.draw.line(surface, WOOD_DARK, (px, lid_y + 8), (px, lid_y + lid_h - 8), 4)

    pygame.draw.rect(surface, GOLD, (lid_rect.x + 8, lid_y + 18, lid_rect.w - 16, 20), border_radius=10)
    pygame.draw.rect(surface, GOLD_DARK, (lid_rect.x + 8, lid_y + 18, lid_rect.w - 16, 20), width=4, border_radius=10)

    lock_surface = pygame.Surface((110, 120), pygame.SRCALPHA)
    pygame.draw.rect(lock_surface, (250, 223, 95), (25, 28, 60, 70), border_radius=12)
    pygame.draw.rect(lock_surface, GOLD_DARK, (25, 28, 60, 70), width=4, border_radius=12)
    pygame.draw.circle(lock_surface, (210, 160, 45), (55, 63), 11)
    pygame.draw.circle(lock_surface, WHITE, (72, 46), 3)

    if lock_unlocked:
        drift_x = int(34 * lock_drop)
        drift_y = int(88 * lock_drop)
        spin = -30 * lock_drop
        falling_lock = pygame.transform.rotozoom(lock_surface, spin, max(0.72, 1.0 - 0.28 * lock_drop))
        lock_rect = falling_lock.get_rect(center=(cx + drift_x, cy + 52 + drift_y))
        surface.blit(falling_lock, lock_rect)
    else:
        lock_rect = lock_surface.get_rect(center=(cx, cy + 52))
        surface.blit(lock_surface, lock_rect)

    shimmer = int(8 + 4 * math.sin(t * 5.8 + coin_shimmer * 1.7))
    pygame.draw.circle(surface, WHITE, (cx + 17, cy + 36), max(1, shimmer // 3))


def draw_parrot_fallback(surface, x, y, t, emotion="happy"):
    wing_bob = int(math.sin(t * 9) * 10)
    blink = math.sin(t * 2.7) > 0.97
    breath = math.sin(t * 3.2) * 2  # gentle breathing

    # ── Tail feathers (drawn first, behind the body) ──
    tail_sway = math.sin(t * 4.5) * 5
    for i, (length, color) in enumerate([
        (58, (30, 140, 65)), (52, (200, 60, 50)), (46, (48, 120, 195)),
        (40, (220, 190, 40)), (34, (30, 155, 75)),
    ]):
        angle = -1.8 + i * 0.22 + math.sin(t * 3.8 + i * 0.6) * 0.08
        tx = x - 28 + int(tail_sway * 0.3) + i * 4
        ty = y + 60 + i * 2
        ex = tx + int(math.cos(angle) * length)
        ey = ty + int(math.sin(angle) * length)
        pygame.draw.line(surface, color, (tx, ty), (ex, ey), max(3, 6 - i))
        # Feather tip barb
        pygame.draw.circle(surface, color, (ex, ey), max(2, 4 - i))

    # ── Feet with toes ──
    foot_color = (240, 165, 55)
    foot_dark = (200, 130, 40)
    for fx, fy_off in [(-14, 0), (8, 0)]:
        fy = y + 68
        # Leg
        pygame.draw.line(surface, foot_color, (x + fx, fy), (x + fx + 2, fy + 18), 5)
        pygame.draw.line(surface, foot_dark, (x + fx, fy), (x + fx + 2, fy + 18), 2)
        # Three toes
        toe_y = fy + 18
        toe_x = x + fx + 2
        for angle in (-0.5, 0.0, 0.5):
            ex = toe_x + int(math.cos(angle) * 10)
            ey = toe_y + int(math.sin(angle + 1.0) * 6) + 2
            pygame.draw.line(surface, foot_color, (toe_x, toe_y), (ex, ey), 3)
            pygame.draw.circle(surface, foot_dark, (ex, ey), 2)

    # ── Body (main green with feather-texture shading) ──
    body_green = (52, 195, 88)
    body_light = (88, 225, 118)
    body_dark = (38, 158, 68)
    body_rect = (x - 52, y - 14 + int(breath), 108, 140)
    pygame.draw.ellipse(surface, body_green, body_rect)
    # Feather texture lines on body
    for fy_off in range(16, 120, 14):
        fy_pos = y - 14 + fy_off + int(breath)
        wave = int(math.sin(fy_off * 0.3 + t * 2) * 3)
        pygame.draw.arc(surface, body_dark,
                        (x - 36 + wave, fy_pos, 76, 10), 0.3, math.pi - 0.3, 1)
    # Belly highlight
    belly = (x - 30, y + 22 + int(breath), 56, 72)
    pygame.draw.ellipse(surface, body_light, belly)
    pygame.draw.ellipse(surface, (75, 210, 105), belly, width=1)

    # ── Wings ──
    wing_green = (32, 162, 75)
    wing_tip = (28, 130, 58)
    wing_highlight = (60, 190, 100)
    wing_h = 62 + wing_bob
    # Left wing
    lw = (x - 78, y + 8, 44, wing_h)
    pygame.draw.ellipse(surface, wing_green, lw)
    pygame.draw.ellipse(surface, wing_highlight, (lw[0] + 6, lw[1] + 4, 28, wing_h - 16))
    pygame.draw.ellipse(surface, wing_tip, lw, width=2)
    # Wing feather lines
    for fi in range(3):
        fy = lw[1] + 18 + fi * 16
        pygame.draw.line(surface, wing_tip, (lw[0] + 8, fy), (lw[0] + 36, fy + 4), 1)
    # Right wing
    rw = (x + 34, y + 8, 44, wing_h)
    pygame.draw.ellipse(surface, wing_green, rw)
    pygame.draw.ellipse(surface, wing_highlight, (rw[0] + 6, rw[1] + 4, 28, wing_h - 16))
    pygame.draw.ellipse(surface, wing_tip, rw, width=2)
    for fi in range(3):
        fy = rw[1] + 18 + fi * 16
        pygame.draw.line(surface, wing_tip, (rw[0] + 8, fy), (rw[0] + 36, fy + 4), 1)

    # ── Head ──
    head_green = (56, 208, 96)
    head_light = (80, 225, 125)
    head_r = 48
    hx, hy = x + 2, y - 22
    pygame.draw.circle(surface, head_green, (hx, hy), head_r)
    # Forehead highlight
    pygame.draw.circle(surface, head_light, (hx - 8, hy - 18), 22)
    # Cheek feather detail
    pygame.draw.arc(surface, body_dark, (hx - 34, hy + 2, 30, 18), 0.4, math.pi - 0.4, 1)
    pygame.draw.arc(surface, body_dark, (hx - 28, hy + 14, 24, 14), 0.4, math.pi - 0.4, 1)

    # ── Pirate bandana ──
    bandana_red = (200, 52, 42)
    bandana_dark = (160, 38, 30)
    bandana_highlight = (225, 80, 65)
    # Main bandana wrap
    band_pts = [
        (hx - 44, hy - 18), (hx + 44, hy - 18),
        (hx + 48, hy - 6), (hx - 48, hy - 6),
    ]
    pygame.draw.polygon(surface, bandana_red, band_pts)
    pygame.draw.polygon(surface, bandana_dark, band_pts, width=2)
    # Bandana top curve
    pygame.draw.arc(surface, bandana_red, (hx - 44, hy - 38, 88, 42), 0, math.pi, 0)
    pygame.draw.arc(surface, bandana_dark, (hx - 44, hy - 38, 88, 42), 0.1, math.pi - 0.1, 2)
    # Highlight stripe
    pygame.draw.line(surface, bandana_highlight, (hx - 30, hy - 14), (hx + 30, hy - 14), 2)
    # Hanging knot tails on the right side
    knot_wave = math.sin(t * 5.0) * 3
    pygame.draw.line(surface, bandana_red, (hx + 38, hy - 10),
                     (hx + 52 + int(knot_wave), hy + 8), 4)
    pygame.draw.line(surface, bandana_dark, (hx + 40, hy - 10),
                     (hx + 56 + int(knot_wave * 0.7), hy + 14), 3)
    # Small white skull on bandana
    skull_x, skull_y = hx, hy - 14
    pygame.draw.circle(surface, (230, 225, 215), (skull_x, skull_y), 6)
    pygame.draw.circle(surface, BLACK, (skull_x - 2, skull_y - 1), 1)
    pygame.draw.circle(surface, BLACK, (skull_x + 2, skull_y - 1), 1)
    pygame.draw.line(surface, BLACK, (skull_x - 3, skull_y + 3), (skull_x + 3, skull_y + 3), 1)

    # ── Beak (detailed curved beak) ──
    beak_base = (245, 175, 45)
    beak_tip = (220, 140, 30)
    beak_highlight = (255, 210, 90)
    # Upper beak (larger, curved)
    upper_beak = [
        (hx + 14, hy - 4), (hx + 56, hy + 4), (hx + 50, hy + 12), (hx + 14, hy + 6),
    ]
    pygame.draw.polygon(surface, beak_base, upper_beak)
    pygame.draw.polygon(surface, beak_tip, upper_beak, width=2)
    # Beak ridge line
    pygame.draw.line(surface, beak_highlight, (hx + 16, hy - 2), (hx + 48, hy + 5), 2)
    # Nostril
    pygame.draw.circle(surface, beak_tip, (hx + 28, hy + 2), 2)
    # Lower beak
    lower_beak = [
        (hx + 14, hy + 8), (hx + 42, hy + 14), (hx + 14, hy + 14),
    ]
    pygame.draw.polygon(surface, (215, 155, 35), lower_beak)
    pygame.draw.polygon(surface, beak_tip, lower_beak, width=1)
    # Beak tip hook
    pygame.draw.arc(surface, beak_tip, (hx + 46, hy + 2, 14, 16), -0.5, 1.2, 2)

    # ── Eyes (large, expressive, cartoony) ──
    # Eye whites (slightly different sizes for character)
    left_eye_x, left_eye_y = hx - 16, hy - 6
    pygame.draw.ellipse(surface, WHITE, (left_eye_x - 14, left_eye_y - 13, 26, 24))
    pygame.draw.ellipse(surface, (235, 240, 235), (left_eye_x - 12, left_eye_y - 11, 22, 20))

    if blink:
        # Blink — curved line
        pygame.draw.arc(surface, BLACK, (left_eye_x - 12, left_eye_y - 6, 22, 12),
                        0.2, math.pi - 0.2, 3)
    else:
        # Iris
        iris_color = (40, 35, 30)
        pupil_x = left_eye_x
        pupil_y = left_eye_y
        # Slight look direction based on emotion
        if emotion == "surprised":
            pupil_y -= 2
        elif emotion == "angry":
            pupil_x += 2
        pygame.draw.circle(surface, iris_color, (pupil_x, pupil_y), 8)
        # Pupil
        pygame.draw.circle(surface, BLACK, (pupil_x, pupil_y), 5)
        # Eye shine (two highlights)
        pygame.draw.circle(surface, WHITE, (pupil_x + 3, pupil_y - 3), 3)
        pygame.draw.circle(surface, (220, 230, 240), (pupil_x - 2, pupil_y + 2), 1)
    # Eye outline
    pygame.draw.ellipse(surface, BLACK, (left_eye_x - 14, left_eye_y - 13, 26, 24), width=2)

    # ── Emotion-based expressions ──
    if emotion == "angry":
        # Angry eyebrows (thick, angled down)
        pygame.draw.line(surface, BLACK, (left_eye_x - 14, left_eye_y - 20),
                         (left_eye_x + 8, left_eye_y - 14), 4)
        # Frown
        pygame.draw.arc(surface, BLACK, (hx - 12, hy + 16, 32, 20),
                        math.pi * 0.15, math.pi * 0.85, 3)
        # Ruffled feathers on head
        for i in range(3):
            fx = hx - 20 + i * 16
            pygame.draw.line(surface, body_dark, (fx, hy - 36), (fx + 4, hy - 46), 2)
    elif emotion == "surprised":
        # Raised eyebrow
        pygame.draw.arc(surface, BLACK, (left_eye_x - 16, left_eye_y - 26, 30, 16),
                        0.2, math.pi - 0.2, 3)
        # Open mouth (beak gap)
        pygame.draw.ellipse(surface, (60, 35, 25), (hx + 18, hy + 10, 18, 10))
    elif emotion == "cheer":
        # Happy eyebrows (curved up)
        pygame.draw.arc(surface, BLACK, (left_eye_x - 14, left_eye_y - 24, 26, 14),
                        0.3, math.pi - 0.3, 2)
        # Big smile
        pygame.draw.arc(surface, BLACK, (hx - 16, hy + 10, 38, 24),
                        0.15, math.pi - 0.15, 3)
        # Rosy cheek
        pygame.draw.circle(surface, (255, 160, 140, 90), (hx - 26, hy + 10), 8)
        # Sparkle near eye
        sparkle_phase = (t * 4) % 6.28
        sx = left_eye_x + 20 + int(math.cos(sparkle_phase) * 4)
        sy = left_eye_y - 16 + int(math.sin(sparkle_phase) * 3)
        pygame.draw.line(surface, (255, 255, 200), (sx - 4, sy), (sx + 4, sy), 2)
        pygame.draw.line(surface, (255, 255, 200), (sx, sy - 4), (sx, sy + 4), 2)
    elif emotion == "talk":
        # Slightly open beak — mouth gap
        pygame.draw.ellipse(surface, (70, 40, 28), (hx + 20, hy + 10, 14, 8))
        # Normal eyebrow
        pygame.draw.arc(surface, BLACK, (left_eye_x - 12, left_eye_y - 22, 24, 12),
                        0.3, math.pi - 0.3, 2)
    else:
        # Default happy — gentle smile
        pygame.draw.arc(surface, BLACK, (hx - 10, hy + 12, 28, 18),
                        0.2, math.pi - 0.2, 2)

    # ── Body outline for definition ──
    pygame.draw.ellipse(surface, body_dark, body_rect, width=2)


# ---------------------------------------------------------------------------
# Treasure item drawing functions (for the treasure vault reveal)
# ---------------------------------------------------------------------------

def draw_golden_key(surface, center, size, t):
    """Draw a shimmering golden key."""
    cx, cy = int(center[0]), int(center[1])
    s = max(8, int(size))
    # Key head (oval)
    head_r = s // 2
    pygame.draw.circle(surface, (250, 205, 55), (cx, cy - s // 4), head_r)
    pygame.draw.circle(surface, (203, 151, 25), (cx, cy - s // 4), head_r, width=2)
    # Key hole
    pygame.draw.circle(surface, (170, 120, 30), (cx, cy - s // 4), head_r // 3)
    # Shaft
    shaft_w = max(3, s // 6)
    pygame.draw.rect(surface, (250, 205, 55), (cx - shaft_w // 2, cy, shaft_w, s // 2))
    pygame.draw.rect(surface, (203, 151, 25), (cx - shaft_w // 2, cy, shaft_w, s // 2), width=1)
    # Teeth
    for i in range(2):
        ty = cy + s // 2 - i * (s // 5)
        pygame.draw.rect(surface, (250, 205, 55), (cx + shaft_w // 2, ty - 2, s // 5, 4))
        pygame.draw.rect(surface, (203, 151, 25), (cx + shaft_w // 2, ty - 2, s // 5, 4), width=1)
    # Shimmer
    glint_angle = t * 3.2
    gx = cx + int(math.cos(glint_angle) * head_r * 0.4)
    gy = cy - s // 4 - int(abs(math.sin(glint_angle)) * head_r * 0.3)
    pygame.draw.circle(surface, (255, 255, 220), (gx, gy), max(2, s // 8))


def draw_ruby_shield(surface, center, size, t):
    """Draw a red gem set in a shield shape."""
    cx, cy = int(center[0]), int(center[1])
    s = max(8, int(size))
    hs = s // 2
    # Shield shape
    pts = [(cx, cy - hs), (cx + hs, cy - hs // 3), (cx + hs * 2 // 3, cy + hs),
           (cx, cy + hs + hs // 3), (cx - hs * 2 // 3, cy + hs), (cx - hs, cy - hs // 3)]
    pygame.draw.polygon(surface, (200, 40, 40), pts)
    pygame.draw.polygon(surface, (160, 30, 30), pts, width=2)
    # Inner gem
    gem_r = max(3, s // 4)
    pygame.draw.circle(surface, (240, 80, 80), (cx, cy), gem_r)
    pygame.draw.circle(surface, (255, 140, 140), (cx - gem_r // 3, cy - gem_r // 3), gem_r // 2)
    pygame.draw.circle(surface, (160, 30, 30), (cx, cy), gem_r, width=1)
    # Pulse
    pulse = 1.0 + 0.08 * math.sin(t * 3)
    if pulse > 1.04:
        pygame.draw.circle(surface, (255, 200, 200), (cx, cy), int(gem_r * 1.3), width=1)


def draw_emerald_scroll(surface, center, size, t):
    """Draw a green rolled parchment scroll."""
    cx, cy = int(center[0]), int(center[1])
    s = max(8, int(size))
    w = int(s * 0.8)
    h = int(s * 1.2)
    # Scroll body
    pygame.draw.rect(surface, (60, 180, 80), (cx - w // 2, cy - h // 2, w, h), border_radius=4)
    pygame.draw.rect(surface, (40, 140, 60), (cx - w // 2, cy - h // 2, w, h), width=2, border_radius=4)
    # Rolled edges
    roll_r = max(3, w // 5)
    pygame.draw.circle(surface, (50, 160, 70), (cx - w // 2 + 2, cy - h // 2), roll_r)
    pygame.draw.circle(surface, (40, 140, 60), (cx - w // 2 + 2, cy - h // 2), roll_r, width=1)
    pygame.draw.circle(surface, (50, 160, 70), (cx - w // 2 + 2, cy + h // 2), roll_r)
    pygame.draw.circle(surface, (40, 140, 60), (cx - w // 2 + 2, cy + h // 2), roll_r, width=1)
    # Text lines
    for i in range(3):
        lx = cx - w // 3
        ly = cy - h // 4 + i * (h // 4)
        lw = w * 2 // 3 - (i % 2) * (w // 6)
        pygame.draw.line(surface, (180, 255, 200), (lx, ly), (lx + lw, ly), 1)
    # Sparkle dots
    for i in range(4):
        angle = t * 2 + i * 1.57
        sx = cx + int(math.cos(angle) * w // 3)
        sy = cy + int(math.sin(angle) * h // 3)
        pygame.draw.circle(surface, (180, 255, 200), (sx, sy), 1)


def draw_diamond_crown(surface, center, size, t):
    """Draw a sparkling crown with diamond."""
    cx, cy = int(center[0]), int(center[1])
    s = max(8, int(size))
    hs = s // 2
    # Crown base
    base_rect = (cx - hs, cy + hs // 4, s, hs // 2)
    pygame.draw.rect(surface, (100, 180, 255), base_rect, border_radius=4)
    pygame.draw.rect(surface, (60, 120, 200), base_rect, width=2, border_radius=4)
    # Crown points
    points_top = [(cx - hs, cy + hs // 4), (cx - hs // 2, cy - hs // 2),
                  (cx, cy - hs // 6), (cx + hs // 2, cy - hs // 2),
                  (cx + hs, cy + hs // 4)]
    pygame.draw.polygon(surface, (100, 180, 255), points_top)
    pygame.draw.polygon(surface, (60, 120, 200), points_top, width=2)
    # Central diamond
    d_r = max(3, s // 5)
    diamond = [(cx, cy - d_r), (cx + d_r, cy), (cx, cy + d_r), (cx - d_r, cy)]
    pygame.draw.polygon(surface, (220, 240, 255), diamond)
    pygame.draw.polygon(surface, (160, 200, 255), diamond, width=1)
    # Rainbow shimmer
    hue_shift = (t * 2) % 6.28
    sr = int(128 + 127 * math.sin(hue_shift))
    sg = int(128 + 127 * math.sin(hue_shift + 2.09))
    sb = int(128 + 127 * math.sin(hue_shift + 4.19))
    pygame.draw.circle(surface, (sr, sg, sb), (cx, cy), max(2, d_r // 2))
    # Sparkle
    spark_x = cx + int(math.cos(t * 4) * hs * 0.6)
    spark_y = cy - hs // 4 + int(math.sin(t * 3) * hs * 0.3)
    pygame.draw.line(surface, WHITE, (spark_x - 3, spark_y), (spark_x + 3, spark_y), 1)
    pygame.draw.line(surface, WHITE, (spark_x, spark_y - 3), (spark_x, spark_y + 3), 1)


def draw_captains_medal(surface, center, size, t):
    """Draw a gold medal with rotating star."""
    cx, cy = int(center[0]), int(center[1])
    s = max(8, int(size))
    r = s // 2
    # Medal circle
    pygame.draw.circle(surface, (250, 205, 55), (cx, cy), r)
    pygame.draw.circle(surface, (203, 151, 25), (cx, cy), r, width=2)
    # Inner ring
    pygame.draw.circle(surface, (255, 230, 120), (cx, cy), int(r * 0.75), width=1)
    # Rotating star
    star_angle = t * 1.5
    star_r_outer = int(r * 0.55)
    star_r_inner = int(r * 0.25)
    star_pts = []
    for i in range(10):
        a = star_angle + i * math.pi / 5
        rad = star_r_outer if i % 2 == 0 else star_r_inner
        star_pts.append((cx + int(math.cos(a) * rad), cy + int(math.sin(a) * rad)))
    pygame.draw.polygon(surface, (255, 240, 160), star_pts)
    pygame.draw.polygon(surface, (180, 140, 40), star_pts, width=1)
    # Shimmer
    gx = cx + int(math.cos(t * 3.5) * r * 0.3)
    gy = cy - int(abs(math.sin(t * 2.8)) * r * 0.3)
    pygame.draw.circle(surface, WHITE, (gx, gy), max(1, r // 4))
