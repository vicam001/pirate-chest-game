"""Scene implementations for Pirate Password Chest."""

from __future__ import annotations

import math
import random
from datetime import datetime, timezone

import pygame

from .constants import (
    BLACK,
    BLUE,
    CYAN,
    DARK_BLUE,
    DIFFICULTY_ORDER,
    GOLD,
    GREEN,
    HEIGHT,
    ORANGE,
    PARENT_HOLD_SECONDS,
    PARENT_HOTSPOT,
    RED,
    WHITE,
    WIDTH,
    YELLOW,
)
from .difficulty import DifficultyConfig
from .ui import Button, DialLayout, DialWheel, Slider, draw_panel, draw_text_outline, wrap_text
from .visuals import Particle, draw_background, draw_chest_fallback, draw_parrot_fallback, draw_spanish_gold_coin


class BaseScene:
    def __init__(self, game):
        self.game = game
        self.completed = False  # Signal to presentation controller

    def enter(self, payload=None):
        self.completed = False
        return None

    def handle_event(self, event):
        return None

    def update(self, dt):
        return None

    def draw(self, screen):
        return None

    @property
    def is_presentation(self):
        return self.game.presentation_mode

    def draw_world(self, t):
        draw_background(self.game.screen, WIDTH, HEIGHT, t, self.game.wave_phase)
        self.game.sprite_manager.draw_world_overlays(self.game.screen, t)

    def draw_speech_bubble(self, text, tail_x=560, tail_y=170,
                           bubble_rect=None, font=None, tail_direction="down"):
        """Draw a speech bubble with text. tail_direction: 'down' points tail downward, 'up' points upward."""
        if bubble_rect is None:
            bubble_rect = pygame.Rect(92, 18, 716, 130)
        if font is None:
            font = self.game.fonts.small

        pygame.draw.rect(self.game.screen, WHITE, bubble_rect, border_radius=22)
        pygame.draw.rect(self.game.screen, BLACK, bubble_rect, width=4, border_radius=22)

        if tail_direction == "down":
            tail = [(tail_x - 20, bubble_rect.bottom - 2),
                    (tail_x, bubble_rect.bottom + 24),
                    (tail_x + 20, bubble_rect.bottom - 2)]
        else:
            tail = [(tail_x - 20, bubble_rect.top + 2),
                    (tail_x, bubble_rect.top - 24),
                    (tail_x + 20, bubble_rect.top + 2)]
        pygame.draw.polygon(self.game.screen, WHITE, tail)
        pygame.draw.polygon(self.game.screen, BLACK, tail, width=4)

        lines = wrap_text(text, font, bubble_rect.width - 36)
        line_h = font.get_height() + 6
        total_h = min(len(lines), 3) * line_h
        start_y = bubble_rect.top + (bubble_rect.height - total_h) // 2
        for line in lines[:3]:
            draw_text_outline(self.game.screen, line, font, BLACK, YELLOW,
                              (bubble_rect.centerx, start_y), center=True)
            start_y += line_h

    def draw_character_portrait(self, char_id, pos, size=100):
        """Draw a character portrait at the given position."""
        portrait = self.game.sprite_manager.get_portrait(char_id)
        if portrait is not None:
            scaled = pygame.transform.smoothscale(portrait, (size, size))
            rect = scaled.get_rect(center=pos)
            # Decorative circle border
            pygame.draw.circle(self.game.screen, (70, 45, 22), pos, size // 2 + 4, width=4)
            self.game.screen.blit(scaled, rect)
        else:
            from .dialogue import CHARACTERS
            info = CHARACTERS.get(char_id, {})
            color = info.get("color", (200, 200, 200))
            name = info.get("name", "?")
            pygame.draw.circle(self.game.screen, color, pos, size // 2)
            pygame.draw.circle(self.game.screen, BLACK, pos, size // 2, width=3)
            initial = self.game.fonts.med.render(name[0], True, WHITE)
            ir = initial.get_rect(center=pos)
            self.game.screen.blit(initial, ir)

    def draw_particles(self, particles):
        for p in particles:
            p.draw(self.game.screen)


class VoyageIntroScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.map_rect = pygame.Rect(28, 54, 844, 520)
        self.sea_rect = self.map_rect.inflate(-40, -46)
        self.route_points = [
            (100, 488),
            (170, 440),
            (255, 402),
            (360, 370),
            (485, 352),
            (610, 360),
            (700, 396),
            (742, 452),
            (700, 510),
            (610, 532),
            (510, 530),
            (450, 486),
            (430, 424),
        ]
        self.segment_lengths: list[float] = []
        self.total_route_length = 1.0
        self._rebuild_route_metrics()

        self.skip_button = Button((14, 10, 120, 44), "SKIP", (110, 76, 45), (130, 94, 58), pulse=False)
        self.choice_a_button = Button((100, 480, 320, 82), "CHOICE A", (52, 140, 68), (72, 165, 88), pulse=False)
        self.choice_b_button = Button((480, 480, 320, 82), "CHOICE B", (170, 68, 55), (195, 90, 72), pulse=False)
        self.disembark_button = Button((240, 520, 420, 64), "DISEMBARK!", (176, 124, 60), (198, 145, 78))

        self.questions = [
            {
                "trigger": 0.22,
                "question": "A stranger online asks for your name and address. What do you do?",
                "choices": ("KEEP SECRET!", "TELL THEM"),
                "responses": (
                    "Great job! Never share your address with strangers online!",
                    "Oh no! Your address is secret treasure -- never share it!",
                ),
                "best": 0,
                "character": "nina",
            },
            {
                "trigger": 0.50,
                "question": "Which password is harder for pirates to crack?",
                "choices": ("Sun$et#42!", "fluffy"),
                "responses": (
                    "Aye! Mix letters, numbers and symbols for super-strong passwords!",
                    "Too easy! Always mix letters, numbers AND symbols!",
                ),
                "best": 0,
                "character": "captain",
            },
            {
                "trigger": 0.78,
                "question": "Your friend wants your password to help you. What do you do?",
                "choices": ("KEEP SECRET!", "TELL THEM"),
                "responses": (
                    "Well done! Only share passwords with trusted grown-ups like parents!",
                    "Watch out! Even good friends should not get your password!",
                ),
                "best": 0,
                "character": "gibbs",
            },
        ]

        self.progress = 0.0
        self.travel_speed = 0.095
        self.question_cursor = 0
        self.awaiting_choice = False
        self.active_question = None
        self.status_line = ""
        self.response_timer = 0.0
        self.disembark_ready = False
        self.auto_land_timer = 0.0

        # Answer flash effect
        self.flash_timer = 0.0
        self.flash_color = None  # GREEN or RED

    def _rebuild_route_metrics(self):
        self.segment_lengths = []
        total = 0.0
        for idx in range(len(self.route_points) - 1):
            x0, y0 = self.route_points[idx]
            x1, y1 = self.route_points[idx + 1]
            seg = max(1.0, math.hypot(x1 - x0, y1 - y0))
            self.segment_lengths.append(seg)
            total += seg
        self.total_route_length = max(1.0, total)

    def enter(self, payload=None):
        self.completed = False
        self.progress = 0.0
        self.question_cursor = 0
        self.awaiting_choice = False
        self.active_question = None
        self.active_character = None
        self.status_line = "Captain's Log: Set sail for Password Island! Protect your treasure!"
        self.response_timer = 0.0
        self.disembark_ready = False
        self.auto_land_timer = 0.0

        self.flash_timer = 0.0
        self.flash_color = None

        # Presentation mode: title phase shows only dialogue, skip voyage
        self.presentation_phase = None
        if payload and isinstance(payload, dict):
            self.presentation_phase = payload.get("presentation_phase")

    def _route_position(self, progress):
        p = max(0.0, min(1.0, progress))
        target = p * self.total_route_length
        walked = 0.0

        for idx, seg_len in enumerate(self.segment_lengths):
            start = self.route_points[idx]
            end = self.route_points[idx + 1]
            if walked + seg_len >= target:
                local = (target - walked) / max(seg_len, 0.001)
                x = start[0] + (end[0] - start[0]) * local
                y = start[1] + (end[1] - start[1]) * local
                heading = math.atan2(end[1] - start[1], end[0] - start[0])
                return x, y, heading
            walked += seg_len

        prev = self.route_points[-2]
        last = self.route_points[-1]
        heading = math.atan2(last[1] - prev[1], last[0] - prev[0])
        return float(last[0]), float(last[1]), heading

    def _distance_travelled(self):
        return self.progress * self.total_route_length

    def _open_question(self):
        if self.question_cursor >= len(self.questions):
            return
        self.active_question = self.questions[self.question_cursor]
        self.active_character = self.active_question.get("character")
        self.awaiting_choice = True
        self.choice_a_button.label = self.active_question["choices"][0]
        self.choice_b_button.label = self.active_question["choices"][1]
        self.status_line = self.active_question["question"]
        self.game.audio.play_sfx("dial")

    def _resolve_choice(self, idx):
        if self.active_question is None:
            return
        self.awaiting_choice = False
        self.status_line = self.active_question["responses"][idx]
        self.response_timer = 2.2
        if idx == self.active_question["best"]:
            self.game.audio.play_sfx("success")
            self.flash_color = GREEN
        else:
            self.game.audio.play_sfx("clunk")
            self.flash_color = RED
        self.flash_timer = 0.5
        self.question_cursor += 1
        self.active_question = None

    def _draw_parchment_grain(self, screen, rect):
        for i in range(95):
            px = rect.left + ((i * 67 + 43) % rect.width)
            py = rect.top + ((i * 41 + 29) % rect.height)
            r = 1 + (i % 2)
            shade = 198 + (i % 19)
            pygame.draw.circle(screen, (shade, shade - 18, shade - 42), (px, py), r)

        for i in range(24):
            cx = rect.left + ((i * 113 + 79) % rect.width)
            cy = rect.top + ((i * 89 + 37) % rect.height)
            w = 24 + (i % 4) * 8
            h = 12 + (i % 5) * 4
            pygame.draw.ellipse(screen, (182, 145, 91), (cx, cy, w, h), width=1)

    def _draw_vignette(self, screen):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (25, 14, 8, 120), (0, 0, WIDTH, 24))
        pygame.draw.rect(overlay, (25, 14, 8, 120), (0, HEIGHT - 24, WIDTH, 24))
        pygame.draw.rect(overlay, (25, 14, 8, 120), (0, 0, 24, HEIGHT))
        pygame.draw.rect(overlay, (25, 14, 8, 120), (WIDTH - 24, 0, 24, HEIGHT))
        pygame.draw.rect(overlay, (25, 14, 8, 70), (24, 24, WIDTH - 48, HEIGHT - 48), width=12)
        screen.blit(overlay, (0, 0))

    def _draw_chart_background(self, screen, t):
        screen.fill((42, 27, 16))
        for y in range(0, HEIGHT):
            p = y / max(1, HEIGHT)
            col = (
                int(92 * (1 - p) + 46 * p),
                int(72 * (1 - p) + 32 * p),
                int(45 * (1 - p) + 18 * p),
            )
            pygame.draw.line(screen, col, (0, y), (WIDTH, y))

        draw_panel(screen, self.map_rect, bg_color=(226, 198, 141), border_color=(90, 59, 32))
        self._draw_parchment_grain(screen, self.map_rect.inflate(-16, -14))
        pygame.draw.rect(screen, (75, 109, 126), self.sea_rect, border_radius=32)
        pygame.draw.rect(screen, (53, 79, 96), self.sea_rect, width=4, border_radius=32)

        for gx in range(self.sea_rect.left + 22, self.sea_rect.right, 62):
            pygame.draw.line(screen, (110, 145, 160), (gx, self.sea_rect.top + 14), (gx, self.sea_rect.bottom - 14), 1)
        for gy in range(self.sea_rect.top + 20, self.sea_rect.bottom, 56):
            pygame.draw.line(screen, (110, 145, 160), (self.sea_rect.left + 10, gy), (self.sea_rect.right - 10, gy), 1)

        for i in range(40):
            px = self.sea_rect.left + ((i * 101 + 17) % self.sea_rect.width)
            py = self.sea_rect.top + ((i * 53 + 9) % self.sea_rect.height)
            pygame.draw.circle(screen, (90, 122, 138), (px, py), 2)

        for x in range(self.sea_rect.left - 24, self.sea_rect.right + 24, 34):
            yy = self.sea_rect.top + 192 + int(math.sin(t * 2.2 + x * 0.04) * 6)
            pygame.draw.arc(screen, (156, 182, 194), (x, yy, 30, 12), 0, math.pi, 2)

        frame = self.map_rect.inflate(10, 10)
        pygame.draw.rect(screen, (70, 44, 23), frame, width=4, border_radius=26)
        pygame.draw.rect(screen, (162, 118, 71), frame.inflate(-8, -8), width=2, border_radius=22)

        self._draw_island(screen, t)
        self._draw_compass(screen, (120, 145), t)
        self._draw_vignette(screen)

    def _draw_island(self, screen, t):
        island = pygame.Rect(360, 184, 332, 256)
        pygame.draw.ellipse(screen, (96, 126, 74), island)
        pygame.draw.ellipse(screen, (74, 102, 56), island.inflate(-64, -52))
        pygame.draw.ellipse(screen, (123, 96, 68), (450, 248, 140, 82))
        pygame.draw.ellipse(screen, (99, 78, 56), (472, 232, 94, 56))

        shore = pygame.Rect(388, 378, 274, 88)
        pygame.draw.ellipse(screen, (218, 186, 115), shore)
        pygame.draw.ellipse(screen, (188, 156, 90), shore.inflate(-36, -22), width=4)

        pygame.draw.polygon(screen, (80, 68, 60), [(505, 248), (536, 197), (568, 252)])
        pygame.draw.polygon(screen, (67, 57, 49), [(539, 252), (577, 191), (613, 252)])

        sway = math.sin(t * 2.7) * 4.0
        for base_x in (432, 530, 614):
            top = (base_x + int(sway), 282)
            pygame.draw.line(screen, (104, 72, 44), (base_x, 360), top, 10)
            pygame.draw.circle(screen, (77, 120, 64), (top[0], top[1] - 10), 34)
            pygame.draw.circle(screen, (88, 136, 72), (top[0] + 20, top[1] - 2), 24)

        cove = pygame.Rect(477, 390, 98, 36)
        pygame.draw.ellipse(screen, (94, 128, 141), cove)
        pygame.draw.arc(screen, (142, 170, 176), cove.inflate(12, 6), 0, math.pi, 2)

        land = self.route_points[-1]
        pygame.draw.circle(screen, (246, 208, 122), land, 14)
        pygame.draw.circle(screen, (130, 79, 32), land, 14, width=3)
        pygame.draw.line(screen, (130, 79, 32), (land[0] - 7, land[1] - 7), (land[0] + 7, land[1] + 7), 3)
        pygame.draw.line(screen, (130, 79, 32), (land[0] - 7, land[1] + 7), (land[0] + 7, land[1] - 7), 3)
        draw_text_outline(screen, "X", self.game.fonts.tiny, (118, 50, 30), BLACK, (land[0], land[1] - 30), center=True)

    def _draw_compass(self, screen, center, t):
        x, y = center
        pygame.draw.circle(screen, (235, 203, 142), (x, y), 44)
        pygame.draw.circle(screen, (102, 66, 37), (x, y), 44, width=4)
        pygame.draw.circle(screen, (217, 184, 124), (x, y), 30, width=2)
        spin = t * 0.35
        for ang in (0, math.pi / 2, math.pi, math.pi * 1.5):
            px = x + int(math.cos(ang + spin) * 30)
            py = y + int(math.sin(ang + spin) * 30)
            pygame.draw.line(screen, (102, 66, 37), (x, y), (px, py), 3)
        pygame.draw.polygon(screen, (188, 61, 44), [(x, y - 30), (x - 6, y), (x + 6, y)])
        pygame.draw.polygon(screen, (57, 60, 67), [(x, y + 30), (x - 6, y), (x + 6, y)])
        draw_text_outline(screen, "N", self.game.fonts.tiny, (84, 46, 30), WHITE, (x, y - 56), center=True)

    def _draw_route(self, screen):
        travelled = self._distance_travelled()
        left = travelled

        for idx in range(len(self.route_points) - 1):
            start = self.route_points[idx]
            end = self.route_points[idx + 1]
            seg_len = self.segment_lengths[idx]
            seg_dx = end[0] - start[0]
            seg_dy = end[1] - start[1]
            dash_count = max(1, int(seg_len // 18))
            for dash in range(dash_count):
                p0 = dash / dash_count
                p1 = min(1.0, p0 + 0.52 / dash_count)
                sx = int(start[0] + seg_dx * p0)
                sy = int(start[1] + seg_dy * p0)
                ex = int(start[0] + seg_dx * p1)
                ey = int(start[1] + seg_dy * p1)
                pygame.draw.line(screen, (90, 71, 52), (sx, sy), (ex, ey), 3)
            if left > 0:
                if left >= seg_len:
                    draw_end = end
                else:
                    pct = left / max(seg_len, 0.001)
                    draw_end = (
                        int(start[0] + (end[0] - start[0]) * pct),
                        int(start[1] + (end[1] - start[1]) * pct),
                    )
                pygame.draw.line(screen, (236, 194, 96), start, draw_end, 6)
                pygame.draw.line(screen, (255, 231, 150), start, draw_end, 2)
            left -= seg_len

        walked = 0.0
        for idx, point in enumerate(self.route_points):
            reached = walked <= travelled + 1.0
            color = (235, 199, 111) if reached else (154, 129, 102)
            pygame.draw.circle(screen, color, point, 8)
            pygame.draw.circle(screen, (88, 58, 34), point, 8, width=2)
            if idx < len(self.segment_lengths):
                walked += self.segment_lengths[idx]

        draw_text_outline(
            screen,
            "START",
            self.game.fonts.tiny,
            (81, 52, 28),
            WHITE,
            (self.route_points[0][0], self.route_points[0][1] + 22),
            center=True,
        )
        draw_text_outline(
            screen,
            "LAND",
            self.game.fonts.tiny,
            (81, 52, 28),
            WHITE,
            (self.route_points[-1][0] + 40, self.route_points[-1][1]),
            center=True,
        )

    def _draw_ship_wake(self, screen, x, y, heading, t):
        back = heading + math.pi
        # Expanding wake trail
        for idx in range(10):
            dist = 24 + idx * 16 + int((t * 60) % 14)
            wx = int(x + math.cos(back) * dist)
            wy = int(y + math.sin(back) * dist)
            # Spread wake sideways
            spread = idx * 2.5
            perp = back + math.pi / 2
            alpha = max(40, 180 - idx * 16)
            radius = max(2, 8 - idx)
            color = (180, 210, 220, alpha)
            wake_surf = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(wake_surf, color, (radius * 2, radius * 2), radius)
            screen.blit(wake_surf, (wx - radius * 2 + int(math.cos(perp) * spread),
                                    wy - radius * 2 + int(math.sin(perp) * spread)))
            screen.blit(wake_surf, (wx - radius * 2 - int(math.cos(perp) * spread),
                                    wy - radius * 2 - int(math.sin(perp) * spread)))
        # Bow wave (splash at front of ship)
        front = heading
        for i in range(3):
            fw_x = int(x + math.cos(front) * (20 + i * 8))
            fw_y = int(y + math.sin(front) * (20 + i * 8))
            splash_r = max(2, 5 - i)
            pygame.draw.circle(screen, (200, 225, 235), (fw_x, fw_y), splash_r, width=2)

    def _draw_galleon(self, screen, pos, heading, t):
        ship = pygame.Surface((220, 170), pygame.SRCALPHA)
        cx, cy = 110, 85
        bob = math.sin(t * 5.0) * 3.0
        cy = int(cy + bob)

        # --- Hull ---
        # Main body
        hull_pts = [(18, cy + 10), (202, cy + 10), (186, cy + 42), (30, cy + 42)]
        pygame.draw.polygon(ship, (80, 47, 27), hull_pts)
        # Upper deck
        deck_pts = [(28, cy + 4), (194, cy + 4), (202, cy + 10), (18, cy + 10)]
        pygame.draw.polygon(ship, (112, 68, 38), deck_pts)
        # Deck railing
        pygame.draw.line(ship, (65, 38, 20), (28, cy + 4), (194, cy + 4), 2)
        # Hull planks (horizontal lines)
        for py in range(cy + 14, cy + 40, 8):
            pygame.draw.line(ship, (65, 38, 20), (24, py), (196, py), 1)
        # Gold trim band
        pygame.draw.rect(ship, (196, 148, 72), (28, cy + 18, 164, 7), border_radius=3)
        pygame.draw.rect(ship, (160, 110, 50), (28, cy + 18, 164, 7), width=1, border_radius=3)

        # --- Cannon ports ---
        for px in (55, 85, 115, 145):
            pygame.draw.rect(ship, (40, 25, 15), (px, cy + 26, 10, 8), border_radius=2)
            pygame.draw.rect(ship, (30, 18, 10), (px, cy + 26, 10, 8), width=1, border_radius=2)

        # --- Prow (front) ---
        prow_pts = [(202, cy + 10), (218, cy + 2), (202, cy + 18)]
        pygame.draw.polygon(ship, (110, 65, 35), prow_pts)
        # Bowsprit (diagonal pole extending from prow)
        pygame.draw.line(ship, (86, 52, 29), (202, cy + 6), (218, cy - 14), 3)

        # --- Stern (back) ---
        stern = pygame.Rect(18, cy - 8, 28, 22)
        pygame.draw.rect(ship, (95, 55, 30), stern, border_radius=4)
        pygame.draw.rect(ship, (65, 38, 20), stern, width=2, border_radius=4)
        # Stern windows
        for wy in (cy - 2, cy + 6):
            pygame.draw.rect(ship, (180, 220, 240), (22, wy, 8, 5), border_radius=2)
            pygame.draw.rect(ship, (60, 35, 18), (22, wy, 8, 5), width=1, border_radius=2)

        # --- Masts ---
        # Main mast (tall)
        pygame.draw.line(ship, (86, 52, 29), (100, cy + 6), (100, cy - 60), 5)
        # Fore mast (shorter)
        pygame.draw.line(ship, (86, 52, 29), (150, cy + 6), (150, cy - 40), 4)
        # Crow's nest
        pygame.draw.rect(ship, (70, 42, 22), (92, cy - 62, 16, 6), border_radius=2)

        # --- Sails ---
        sail_billow = math.sin(t * 3.5) * 4
        # Main sail (large)
        main_sail = [
            (100, cy - 56), (100, cy + 2),
            (155 + int(sail_billow), cy - 22),
        ]
        pygame.draw.polygon(ship, (240, 236, 220), main_sail)
        pygame.draw.polygon(ship, (200, 195, 178), main_sail, width=2)
        # Fore sail (smaller)
        fore_sail = [
            (150, cy - 36), (150, cy + 2),
            (190 + int(sail_billow * 0.7), cy - 14),
        ]
        pygame.draw.polygon(ship, (225, 220, 205), fore_sail)
        pygame.draw.polygon(ship, (190, 185, 170), fore_sail, width=2)
        # Jib sail (triangle from bowsprit)
        jib_sail = [
            (218, cy - 12), (202, cy + 4),
            (185 + int(sail_billow * 0.5), cy - 6),
        ]
        pygame.draw.polygon(ship, (235, 232, 218), jib_sail)

        # --- Pirate flag (skull and crossbones) ---
        flag_wave = math.sin(t * 6.0) * 3
        flag_rect = pygame.Rect(82, cy - 78 + int(flag_wave), 20, 14)
        pygame.draw.line(ship, (86, 52, 29), (100, cy - 62), (92, cy - 78 + int(flag_wave)), 2)
        pygame.draw.rect(ship, (20, 20, 22), flag_rect, border_radius=2)
        # Tiny skull
        pygame.draw.circle(ship, (220, 220, 210), (flag_rect.centerx, flag_rect.centery - 1), 3)
        pygame.draw.line(ship, (220, 220, 210), (flag_rect.centerx - 3, flag_rect.centery + 3),
                         (flag_rect.centerx + 3, flag_rect.centery + 3), 1)

        # --- Lantern (stern) ---
        lantern_glow = int(abs(math.sin(t * 4.0)) * 60 + 195)
        pygame.draw.circle(ship, (lantern_glow, int(lantern_glow * 0.8), 50), (30, cy - 10), 5)
        pygame.draw.circle(ship, (255, 245, 193), (30, cy - 10), 2)

        # --- Water splashes at hull ---
        for sx in (40, 90, 160):
            splash_y = cy + 38 + int(math.sin(t * 7.0 + sx * 0.1) * 3)
            pygame.draw.arc(ship, (180, 210, 220), (sx, splash_y, 18, 8), 0, math.pi, 2)

        rotated = pygame.transform.rotozoom(ship, -math.degrees(heading), 1.0)
        rect = rotated.get_rect(center=(int(pos[0]), int(pos[1])))
        screen.blit(rotated, rect)

    def _draw_shark(self, screen, x, y, t):
        # Body sway
        sway = math.sin(t * 4.0) * 3.0
        bx = int(x + sway)
        by = int(y)

        # Tail fin (behind body, animated swish)
        tail_angle = math.sin(t * 8.0) * 12.0
        tail_pts = [
            (bx - 42, by + 2),
            (int(bx - 62 + tail_angle), by - 14),
            (int(bx - 58 + tail_angle), by + 16),
        ]
        pygame.draw.polygon(screen, (100, 115, 120), tail_pts)
        pygame.draw.polygon(screen, (80, 92, 98), tail_pts, width=2)

        # Main body — larger teardrop shape
        body = pygame.Rect(bx - 40, by - 10, 86, 30)
        pygame.draw.ellipse(screen, (134, 149, 158), body)
        # Belly (lighter underside)
        belly = pygame.Rect(bx - 30, by + 2, 66, 18)
        pygame.draw.ellipse(screen, (180, 195, 200), belly)
        # Body outline
        pygame.draw.ellipse(screen, (90, 102, 110), body, width=2)

        # Dorsal fin (top, with sway)
        fin_sway = math.sin(t * 7.0) * 4.0
        fin = [
            (int(bx + fin_sway), by - 32),
            (bx - 10, by - 6),
            (bx + 12, by - 8),
        ]
        pygame.draw.polygon(screen, (110, 125, 132), fin)
        pygame.draw.polygon(screen, (85, 98, 105), fin, width=2)

        # Pectoral fins (sides)
        pec_fin = [
            (bx + 8, by + 12),
            (bx + 22, by + 24),
            (bx + 18, by + 10),
        ]
        pygame.draw.polygon(screen, (115, 130, 138), pec_fin)

        # Snout / nose (front)
        pygame.draw.ellipse(screen, (128, 142, 150), (bx + 32, by - 5, 22, 18))

        # Eye — expressive, slightly menacing but cartoonish
        eye_x, eye_y = bx + 26, by - 2
        pygame.draw.circle(screen, (240, 245, 240), (eye_x, eye_y), 7)
        pygame.draw.circle(screen, (30, 30, 35), (eye_x + 2, eye_y), 4)
        pygame.draw.circle(screen, WHITE, (eye_x + 3, eye_y - 2), 2)  # highlight
        # Eyebrow (slightly angry look)
        pygame.draw.line(screen, (70, 80, 88), (eye_x - 6, eye_y - 7), (eye_x + 4, eye_y - 5), 2)

        # Mouth — animated jaw open/close
        jaw_open = abs(math.sin(t * 3.0)) * 6
        mouth_y = by + 6 + int(jaw_open * 0.3)
        # Upper jaw line
        pygame.draw.arc(screen, (60, 68, 75), (bx + 24, by + 1, 28, 12), 0.2, math.pi - 0.2, 2)
        # Teeth (small triangles along jaw line)
        for tx in range(bx + 28, bx + 48, 5):
            pygame.draw.polygon(screen, (230, 230, 225), [
                (tx, by + 6), (tx + 2, by + 10 + int(jaw_open * 0.2)), (tx + 4, by + 6)
            ])

        # Water ripple / splash around shark
        for i in range(3):
            ripple_x = bx - 20 + i * 30
            ripple_y = by + 16 + int(math.sin(t * 5.0 + i * 2.0) * 2)
            pygame.draw.arc(screen, (170, 200, 210, 160),
                            (ripple_x, ripple_y, 20, 8), 0, math.pi, 2)

    def handle_event(self, event):
        # Title phase: no interaction (dialogue handled by game)
        if self.presentation_phase == "title":
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_s):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("landing")
                return
            if self.disembark_ready and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.game.audio.play_sfx("click")
                if self.is_presentation:
                    self.completed = True
                else:
                    self.game.switch_scene("landing")
                return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        if not self.is_presentation and self.skip_button.clicked(event.pos):
            self.game.audio.play_sfx("click")
            self.game.switch_scene("landing")
            return

        if self.awaiting_choice:
            if self.choice_a_button.clicked(event.pos):
                self._resolve_choice(0)
                return
            if self.choice_b_button.clicked(event.pos):
                self._resolve_choice(1)
                return

        if self.disembark_ready and self.disembark_button.clicked(event.pos):
            self.game.audio.play_sfx("click")
            if self.is_presentation:
                self.completed = True
            else:
                self.game.switch_scene("landing")

    def update(self, dt):
        # In presentation title phase, the scene just shows the background
        # while dialogue plays -- nothing to update
        if self.presentation_phase == "title":
            return

        if self.flash_timer > 0:
            self.flash_timer -= dt

        if self.response_timer > 0:
            self.response_timer -= dt

        if self.disembark_ready:
            self.auto_land_timer += dt
            if self.is_presentation:
                # In presentation mode, signal completion instead of auto-landing
                if self.auto_land_timer >= 2.0:
                    self.completed = True
                return
            if self.auto_land_timer >= 6.0:
                self.game.switch_scene("landing")
            return

        if self.awaiting_choice or self.response_timer > 0:
            return

        self.progress = min(1.0, self.progress + dt * self.travel_speed)

        if self.question_cursor < len(self.questions):
            next_question = self.questions[self.question_cursor]
            if self.progress >= next_question["trigger"]:
                self._open_question()
                return

        if self.progress >= 1.0:
            self.disembark_ready = True
            self.status_line = "Land ho! You learned to guard your treasure. Well done, Captain!"
            self.game.audio.play_sfx("reward")

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0

        # Title phase: show map background with title overlay
        if self.presentation_phase == "title":
            self._draw_chart_background(screen, t)

            # Animated ship sailing across the title
            ship_x = 140 + int(math.sin(t * 0.4) * 60)
            ship_y = 430 + int(math.sin(t * 1.2) * 4)
            heading = math.sin(t * 0.3) * 0.15
            self._draw_galleon(screen, (ship_x, ship_y), heading, t)

            # Title panel with parchment background
            title_bg = pygame.Rect(120, 130, 660, 240)
            draw_panel(screen, title_bg, bg_color=(226, 198, 141), border_color=(90, 59, 32))

            # Big title text with glow
            draw_text_outline(screen, "Pirate Password Chest", self.game.fonts.huge, YELLOW, BLACK, (450, 190), center=True)
            draw_text_outline(screen, "Protect Your Digital Treasure!", self.game.fonts.med, WHITE, BLACK, (450, 260), center=True)
            draw_text_outline(screen, "A Cybersecurity Adventure", self.game.fonts.small, CYAN, BLACK, (450, 320), center=True)

            # Draw parrot with bobbing
            parrot_y = 460 + int(math.sin(t * 3.0) * 6)
            self.game.sprite_manager.draw_parrot(screen, (200, parrot_y), "cheer", t)
            draw_text_outline(screen, "Virgil", self.game.fonts.tiny, YELLOW, BLACK, (200, parrot_y + 100), center=True)

            # Draw captain portrait
            self.draw_character_portrait("captain", (700, 460), 90)
            draw_text_outline(screen, "Captain", self.game.fonts.tiny, WHITE, BLACK, (700, 520), center=True)
            return

        self._draw_chart_background(screen, t)
        self._draw_route(screen)

        ship_x, ship_y, heading = self._route_position(self.progress)
        shark_x = ship_x - 60
        shark_y = ship_y + 34 + math.sin(t * 4.4) * 5.0

        self._draw_ship_wake(screen, ship_x, ship_y, heading, t)
        self._draw_shark(screen, shark_x, shark_y, t)
        self._draw_galleon(screen, (ship_x, ship_y), heading, t)

        # Compact header bar with title + progress
        title_panel = pygame.Rect(140, 8, 620, 52)
        draw_panel(screen, title_panel, bg_color=(78, 52, 32), border_color=(184, 143, 88))
        draw_text_outline(screen, "Voyage To Password Island", self.game.fonts.small, (245, 213, 133), BLACK, (450, 34), center=True)

        # Progress bar instead of text — positioned at bottom of title panel
        progress_pct = int(self.progress * 100)
        bar_x, bar_y, bar_w, bar_h = 160, 52, 580, 12
        pygame.draw.rect(screen, (50, 35, 20), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        fill_w = int(bar_w * self.progress)
        if fill_w > 0:
            pygame.draw.rect(screen, (236, 194, 96), (bar_x, bar_y, fill_w, bar_h), border_radius=6)
        pygame.draw.rect(screen, (90, 59, 32), (bar_x, bar_y, bar_w, bar_h), width=2, border_radius=6)
        draw_text_outline(screen, f"{progress_pct}%", self.game.fonts.tiny, (240, 220, 177), BLACK, (bar_x + bar_w + 30, bar_y + 4), center=True)

        # Status line — only shown when NOT in a question (avoids duplicate)
        if not self.awaiting_choice and self.status_line:
            status_panel = pygame.Rect(60, 72, 780, 50)
            draw_panel(screen, status_panel, bg_color=(86, 64, 46), border_color=(198, 159, 103))
            for idx, line in enumerate(wrap_text(self.status_line, self.game.fonts.tiny, status_panel.width - 34)[:2]):
                draw_text_outline(
                    screen, line, self.game.fonts.tiny,
                    (247, 226, 174), BLACK,
                    (status_panel.centerx, status_panel.top + 12 + idx * 24),
                    center=True,
                )

        if not self.is_presentation:
            self.skip_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        if self.awaiting_choice and self.active_question is not None:
            # Darken background
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((28, 19, 13, 140))
            screen.blit(shade, (0, 0))

            # Question panel — full width, well-organized
            q_panel = pygame.Rect(60, 80, 780, 390)
            draw_panel(screen, q_panel, bg_color=(98, 71, 49), border_color=(204, 165, 108))

            # Character portrait on the left
            char_id = self.active_character
            if char_id:
                from .dialogue import CHARACTERS
                char_info = CHARACTERS.get(char_id, {})
                char_name = char_info.get("name", "")
                self.draw_character_portrait(char_id, (q_panel.left + 70, q_panel.top + 100), 90)
                draw_text_outline(screen, char_name, self.game.fonts.tiny, YELLOW, BLACK,
                                  (q_panel.left + 70, q_panel.top + 160), center=True)

            # "Crew Question" title
            text_left = q_panel.left + 140 if char_id else q_panel.centerx
            draw_text_outline(screen, "Crew Question!", self.game.fonts.med, (248, 216, 138), BLACK,
                              (q_panel.centerx + 40, q_panel.top + 40), center=True)

            # Question text — centered, large
            q_lines = wrap_text(self.active_question["question"], self.game.fonts.small, q_panel.width - 180)
            for idx, line in enumerate(q_lines[:3]):
                draw_text_outline(
                    screen, line, self.game.fonts.small,
                    (255, 245, 220), BLACK,
                    (q_panel.centerx + 40, q_panel.top + 110 + idx * 42),
                    center=True,
                )

            # Audience cue in presentation mode
            if self.is_presentation and self.active_question:
                cue = "SHOUT the answer!"
                if self.question_cursor == 1:
                    cue = "POINT to A or B!"
                draw_text_outline(screen, cue, self.game.fonts.small, YELLOW, BLACK,
                                  (q_panel.centerx, q_panel.top + 260), center=True)

            # Divider line before buttons
            pygame.draw.line(screen, (204, 165, 108),
                             (q_panel.left + 30, q_panel.top + 300),
                             (q_panel.right - 30, q_panel.top + 300), 2)

            # Choice buttons at bottom of panel
            self.choice_a_button.rect = pygame.Rect(q_panel.left + 30, q_panel.top + 310, 340, 70)
            self.choice_b_button.rect = pygame.Rect(q_panel.right - 370, q_panel.top + 310, 340, 70)
            self.choice_a_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            self.choice_b_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        elif self.disembark_ready:
            self.disembark_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            draw_text_outline(screen, "Press Enter or click Disembark", self.game.fonts.tiny,
                              (244, 222, 173), BLACK, (450, 500), center=True)

        # Correct/wrong answer flash overlay
        if self.flash_timer > 0 and self.flash_color:
            alpha = int(120 * (self.flash_timer / 0.5))
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((*self.flash_color, alpha))
            screen.blit(flash, (0, 0))


class LandingScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.play_button = Button((300, 325, 300, 96), "PLAY", (255, 135, 40), (255, 170, 70))
        self.diff_button = Button((300, 434, 300, 74), "MODE", (91, 163, 255), (117, 184, 255), pulse=False)
        self.settings_button = Button((300, 518, 300, 58), "SETTINGS", (167, 121, 251), (188, 145, 255), pulse=False)
        self.mute_button = Button((0, 0, 220, 60), "MUTE: OFF", (215, 106, 80), (238, 128, 98), pulse=False)
        self.fullscreen_button = Button((0, 0, 220, 60), "FULL: OFF", (84, 145, 220), (105, 167, 240), pulse=False)
        self.settings_open = False

        self.music_slider = Slider((0, 0, 320, 28), "Music", initial=self.game.audio.music_volume)
        self.sfx_slider = Slider((0, 0, 320, 28), "SFX", initial=self.game.audio.sfx_volume)
        self.settings_panel = pygame.Rect(210, 190, 480, 380)

        self.parent_rect = pygame.Rect(PARENT_HOTSPOT)
        self.parent_hold = 0.0
        self.parent_holding = False

        self.parrot_pos = (780, 380)
        self.chest_pos = (450, 380)

        # Cycling Virgil quotes
        self.virgil_quotes = [
            "Ahoy! Protect your info online -- never share your password!",
            "A strong password is your best treasure map!",
            "Mix letters, numbers, and symbols -- pirate-proof security!",
            "Your birthday is secret treasure -- keep it private!",
            "Click PLAY to start your adventure! SQUAWK!",
            "Only share passwords with trusted grown-ups!",
            "Never click links from strangers on the seven seas!",
        ]
        self.current_quote = self.virgil_quotes[0]
        self.quote_timer = 0.0
        self.quote_interval = 6.0
        self.quote_index = 0

    def _sync_audio_settings(self):
        self.game.audio.set_music_volume(self.music_slider.value)
        self.game.audio.set_sfx_volume(self.sfx_slider.value)
        self.game.save_manager.set_settings(
            mute=self.game.audio.muted,
            music_volume=self.music_slider.value,
            sfx_volume=self.sfx_slider.value,
            fullscreen=self.game.fullscreen,
        )

    def _layout_settings_controls(self):
        panel = self.settings_panel
        self.music_slider.rect = pygame.Rect(panel.left + 76, panel.top + 110, 320, 28)
        self.sfx_slider.rect = pygame.Rect(panel.left + 76, panel.top + 190, 320, 28)
        self.mute_button.rect = pygame.Rect(panel.left + 130, panel.top + 245, 220, 60)
        self.fullscreen_button.rect = pygame.Rect(panel.left + 130, panel.top + 310, 220, 50)

    def _truncate_to_width(self, text, max_width):
        if self.game.fonts.tiny.size(text)[0] <= max_width:
            return text
        trimmed = text
        while trimmed and self.game.fonts.tiny.size(trimmed + "...")[0] > max_width:
            trimmed = trimmed[:-1]
        return (trimmed + "...") if trimmed else "..."

    def handle_event(self, event):
        if self.settings_open:
            self._layout_settings_controls()
            handled = self.music_slider.handle_event(event) or self.sfx_slider.handle_event(event)
            if handled:
                self._sync_audio_settings()
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.settings_open:
                if self.mute_button.clicked(event.pos):
                    self.game.audio.set_muted(not self.game.audio.muted)
                    self._sync_audio_settings()
                    self.game.audio.play_sfx("click")
                    return

                if self.fullscreen_button.clicked(event.pos):
                    self.game.toggle_fullscreen()
                    self._sync_audio_settings()
                    self.game.audio.play_sfx("click")
                    return

                if not self.settings_panel.collidepoint(event.pos):
                    self.settings_open = False
                    self.game.audio.play_sfx("click")
                    return
                return

            if self.parent_rect.collidepoint(event.pos):
                self.parent_holding = True
                self.parent_hold = 0.0

            if self.play_button.clicked(event.pos):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("crack")
                return

            if self.diff_button.clicked(event.pos):
                self.game.current_difficulty = self.game.difficulty_manager.next_difficulty(self.game.current_difficulty)
                self.game.audio.play_sfx("dial")
                return

            if self.settings_button.clicked(event.pos):
                self.settings_open = not self.settings_open
                self.game.audio.play_sfx("click")
                return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.parent_holding = False
            self.parent_hold = 0.0

        if event.type == pygame.MOUSEMOTION and self.parent_holding:
            if not self.parent_rect.collidepoint(event.pos):
                self.parent_holding = False
                self.parent_hold = 0.0

    def update(self, dt):
        if self.parent_holding and pygame.mouse.get_pressed()[0] and self.game.mouse_inside_canvas and self.parent_rect.collidepoint(self.game.mouse_virtual_pos):
            self.parent_hold += dt
            if self.parent_hold >= PARENT_HOLD_SECONDS:
                self.parent_holding = False
                self.parent_hold = 0.0
                self.game.audio.play_sfx("click")
                self.game.switch_scene("parent_report")
                return

        self.mute_button.label = "MUTE: ON" if self.game.audio.muted else "MUTE: OFF"
        self.fullscreen_button.label = "FULL: ON" if self.game.fullscreen else "FULL: OFF"
        cfg = self.game.difficulty_manager.get_config(self.game.current_difficulty)
        self.diff_button.label = f"MODE: {cfg.label.upper()}"

        # Cycle Virgil quotes
        self.quote_timer += dt
        if self.quote_timer >= self.quote_interval:
            self.quote_timer = 0.0
            self.quote_index = (self.quote_index + 1) % len(self.virgil_quotes)
            self.current_quote = self.virgil_quotes[self.quote_index]

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        # Title at the top, clear of everything
        draw_text_outline(screen, "Pirate Password Chest", self.game.fonts.huge, YELLOW, BLACK, (350, 50), center=True)
        draw_text_outline(screen, "Arrr You Safe?", self.game.fonts.med, WHITE, BLACK, (350, 120), center=True)

        # Chest in center-left area
        self.game.sprite_manager.draw_chest(
            screen,
            self.chest_pos,
            "closed",
            t,
            fallback=lambda s: draw_chest_fallback(s, self.chest_pos, t, open_amount=0.0, shake=0.0),
        )

        # Virgil on the right side, bobbing
        virgil_y = self.parrot_pos[1] + int(math.sin(t * 3.0) * 5)
        self.game.sprite_manager.draw_parrot(
            screen,
            (self.parrot_pos[0], virgil_y),
            "idle",
            t,
            fallback=lambda s: draw_parrot_fallback(s, self.parrot_pos[0], virgil_y, t, emotion="happy"),
        )
        draw_text_outline(screen, "Virgil", self.game.fonts.tiny, YELLOW, BLACK,
                          (self.parrot_pos[0], virgil_y + 110), center=True)

        # Speech bubble above Virgil — positioned to not overlap with title or buttons
        bubble_rect = pygame.Rect(440, 155, 440, 100)
        self.draw_speech_bubble(self.current_quote, tail_x=720, tail_y=260,
                                bubble_rect=bubble_rect, font=self.game.fonts.tiny)

        # Buttons in the left-center area
        self.play_button.rect = pygame.Rect(80, 290, 300, 96)
        self.diff_button.rect = pygame.Rect(80, 400, 300, 74)
        self.settings_button.rect = pygame.Rect(80, 488, 300, 58)
        self.play_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.diff_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.settings_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        # Hidden parent hotspot hint only while holding.
        if self.parent_holding:
            progress = min(1.0, self.parent_hold / PARENT_HOLD_SECONDS)
            pygame.draw.rect(screen, (255, 255, 255, 60), self.parent_rect, border_radius=8)
            pygame.draw.rect(screen, WHITE, self.parent_rect, width=2, border_radius=8)
            bar = pygame.Rect(self.parent_rect.left + 8, self.parent_rect.bottom - 16, int((self.parent_rect.width - 16) * progress), 8)
            pygame.draw.rect(screen, GREEN, bar, border_radius=4)

        if self.settings_open:
            self._layout_settings_controls()
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((6, 16, 35, 150))
            screen.blit(overlay, (0, 0))
            panel = self.settings_panel
            draw_panel(screen, panel, bg_color=(34, 58, 98), border_color=(188, 214, 255))
            draw_text_outline(screen, "Settings", self.game.fonts.med, WHITE, BLACK, (panel.centerx, panel.top + 34), center=True)
            self.music_slider.draw(screen, self.game.fonts)
            self.sfx_slider.draw(screen, self.game.fonts)
            self.mute_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            self.fullscreen_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)


class CrackScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.config: DifficultyConfig | None = None
        self.secret = ""
        self.dials: list[DialWheel] = []
        self.attempts = 0
        self.hints_used = 0
        self.revealed = []
        self.weak_meter = 0.0
        self.parrot_line = ""
        self.parrot_emotion = "talk"
        self.chest_state = "closed"
        self.shake_timer = 0.0
        self.win = False
        self.start_ticks = 0
        self.virgil_pos = (WIDTH - 122, 120)
        self.virgil_hit_size = (200, 188)
        self.virgil_quote_timer = 0.0
        self.virgil_next_quote_delay = random.uniform(5.0, 9.0)
        from .dialogue import CRACK_IDLE_QUOTES
        self.virgil_idle_quotes = CRACK_IDLE_QUOTES
        self.last_virgil_quote = ""

        self.try_button = Button((650, 340, 230, 120), "TRY!", (255, 124, 33), (255, 156, 70), text_color=YELLOW)
        self.home_button = Button((20, 448, 250, 92), "LANDING", (151, 102, 222), (178, 131, 242), pulse=False)
        self.lesson_button = Button((650, 470, 230, 92), "LESSON", (90, 191, 102), (115, 212, 128), pulse=False)

        self.sparkles: list[Particle] = []
        self.treasure: list[Particle] = []
        self.cinematic_timer = 0.0
        self.cinematic_open_amount = 0.0
        self.cinematic_zoom = 0.0
        self.lock_drop = 0.0
        self.lock_unlocked = False
        self.coin_hotspots: list[pygame.Rect] = []
        self.cinematic_sfx_flags: set[str] = set()

    def enter(self, payload=None):
        self.completed = False

        # Support forced difficulty from presentation mode
        difficulty = self.game.current_difficulty
        if payload and isinstance(payload, dict):
            forced = payload.get("force_difficulty")
            if forced:
                difficulty = forced
                self.game.current_difficulty = forced

        self.config = self.game.difficulty_manager.get_config(difficulty)
        self.secret = self.game.difficulty_manager.random_secret(self.config.key)
        self.dials = self._build_dials(self.config)
        self.attempts = 0
        self.hints_used = 0
        self.revealed = [None for _ in range(self.config.length)]
        self.weak_meter = 0.0
        self.parrot_line = "Spin the dials and crack the lock, matey!"
        self.parrot_emotion = "talk"
        self.chest_state = "closed"
        self.shake_timer = 0.0
        self.win = False
        self.start_ticks = pygame.time.get_ticks()
        self.virgil_quote_timer = 0.0
        self.virgil_next_quote_delay = random.uniform(5.0, 9.0)
        self.last_virgil_quote = ""
        self.sparkles.clear()
        self.treasure.clear()
        self.proactive_hint_timer = 0.0
        self.screen_shake_timer = 0.0
        self.cinematic_timer = 0.0
        self.cinematic_open_amount = 0.0
        self.cinematic_zoom = 0.0
        self.lock_drop = 0.0
        self.lock_unlocked = False
        self.coin_hotspots.clear()
        self.cinematic_sfx_flags.clear()

    def _virgil_rect(self):
        return pygame.Rect(
            self.virgil_pos[0] - self.virgil_hit_size[0] // 2,
            self.virgil_pos[1] - self.virgil_hit_size[1] // 2,
            self.virgil_hit_size[0],
            self.virgil_hit_size[1],
        )

    def _next_virgil_quote(self):
        if len(self.virgil_idle_quotes) == 1:
            return self.virgil_idle_quotes[0]
        choices = [q for q in self.virgil_idle_quotes if q != self.last_virgil_quote]
        return random.choice(choices or self.virgil_idle_quotes)

    def _build_dials(self, config: DifficultyConfig):
        dials = []
        spacing = 120
        start_x = 450 - ((config.length - 1) * spacing) // 2
        size_by_length = {1: 72, 2: 66, 3: 60, 4: 54}
        dial_size = size_by_length.get(config.length, 54)
        for i in range(config.length):
            dials.append(DialWheel(config.symbols, DialLayout(start_x + (i * spacing), 355, dial_size)))
        return dials

    def _guess(self):
        return "".join(d.current_symbol() for d in self.dials)

    def _spawn_win_particles(self):
        for _ in range(90):
            ang = random.uniform(0, math.pi * 2)
            speed = random.uniform(40, 190)
            self.sparkles.append(
                Particle(
                    x=450,
                    y=250,
                    vx=math.cos(ang) * speed,
                    vy=math.sin(ang) * speed,
                    size=random.uniform(3, 7),
                    life=random.uniform(1.1, 1.8),
                    max_life=1.8,
                    color=random.choice([GOLD, YELLOW, WHITE, (255, 220, 140)]),
                    gravity=45,
                )
            )

        for _ in range(40):
            self.treasure.append(
                Particle(
                    x=450,
                    y=300,
                    vx=random.uniform(-180, 180),
                    vy=random.uniform(-280, -100),
                    size=random.uniform(7, 14),
                    life=4.0,
                    max_life=4.0,
                    color=random.choice([(250, 210, 55), (120, 220, 255), (255, 95, 150), (148, 255, 168)]),
                    gravity=420,
                    bounce=True,
                )
            )

    @staticmethod
    def _ease(value):
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    def _spawn_coin_clink_fx(self, x, y):
        for _ in range(26):
            ang = random.uniform(0, math.pi * 2)
            speed = random.uniform(30, 155)
            self.sparkles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(ang) * speed,
                    vy=math.sin(ang) * speed - random.uniform(20, 65),
                    size=random.uniform(2.0, 4.5),
                    life=random.uniform(0.35, 0.85),
                    max_life=0.85,
                    color=random.choice([GOLD, YELLOW, WHITE, (255, 209, 92)]),
                    gravity=165,
                )
            )

    def _draw_coin_zoom_panel(self, screen, t):
        if self.cinematic_zoom <= 0.02:
            self.coin_hotspots.clear()
            return

        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((6, 8, 18, int(90 + self.cinematic_zoom * 120)))
        screen.blit(shade, (0, 0))

        source = pygame.Rect(300, 232, 300, 190)
        target = pygame.Rect(74, 54, 752, 496)
        panel = pygame.Rect(
            int(source.x + (target.x - source.x) * self.cinematic_zoom),
            int(source.y + (target.y - source.y) * self.cinematic_zoom),
            int(source.width + (target.width - source.width) * self.cinematic_zoom),
            int(source.height + (target.height - source.height) * self.cinematic_zoom),
        )

        # Outer wooden frame
        pygame.draw.rect(screen, (55, 32, 16), panel.inflate(16, 16), border_radius=32)
        # Inner chest cavity
        pygame.draw.rect(screen, (85, 50, 22), panel, border_radius=28)
        # Gold trim
        pygame.draw.rect(screen, (210, 165, 60), panel, width=4, border_radius=28)
        # Inner gold band
        band = pygame.Rect(panel.left + 12, panel.top + 12, panel.width - 24, panel.height - 24)
        pygame.draw.rect(screen, (180, 140, 50), band, width=2, border_radius=22)

        # Title
        draw_text_outline(
            screen, "Pirate Treasure!", self.game.fonts.med, YELLOW, BLACK,
            (panel.centerx, panel.top + 38), center=True,
        )
        # Subtitle
        draw_text_outline(
            screen, "Tap the coins to hear them clink!", self.game.fonts.tiny, WHITE, BLACK,
            (panel.centerx, panel.top + 74), center=True,
        )

        # Coin display area — velvet-like dark background
        coin_area = pygame.Rect(panel.left + 36, panel.top + 96, panel.width - 72, panel.height - 120)
        # Dark velvet backing
        pygame.draw.rect(screen, (50, 28, 14), coin_area, border_radius=18)
        # Subtle inner shadow
        pygame.draw.rect(screen, (70, 42, 20), coin_area.inflate(-6, -6), border_radius=16)
        pygame.draw.rect(screen, (110, 72, 32), coin_area, width=2, border_radius=18)

        # Draw coins in a staggered pile layout (more natural than a grid)
        self.coin_hotspots = []
        cols = 7
        rows = 5
        for row in range(rows):
            for col in range(cols):
                # Stagger odd rows
                offset_x = 28 if row % 2 == 1 else 0
                wobble = math.sin(t * 2.2 + row * 0.9 + col * 0.6)
                col_spacing = (coin_area.width - 80) // max(1, cols - 1)
                row_spacing = (coin_area.height - 60) // max(1, rows - 1)
                px = coin_area.left + 40 + col * col_spacing + offset_x
                py = coin_area.top + 30 + row * row_spacing
                py -= int(abs(wobble) * 4)

                # Skip coins that would go out of bounds
                if px > coin_area.right - 20 or px < coin_area.left + 20:
                    continue

                # Coins in back rows are slightly smaller (depth)
                base_radius = 20
                radius = max(8, base_radius - row * 2)

                draw_spanish_gold_coin(screen, (px, py), radius, t + row * 0.15, stamp_phase=col * 0.5)
                hotspot = pygame.Rect(px - radius, py - radius, radius * 2, radius * 2)
                self.coin_hotspots.append(hotspot)

        # Subtle top highlight (very faint, not obstructing)
        highlight_surf = pygame.Surface((coin_area.width - 40, 14), pygame.SRCALPHA)
        highlight_surf.fill((255, 240, 180, 25))
        screen.blit(highlight_surf, (coin_area.left + 20, coin_area.top + 8))

    def _resolve_success(self):
        self.win = True
        self.chest_state = "closed"
        self.parrot_emotion = "cheer"
        self.parrot_line = "SQUAWK! You cracked it! See how easy that was?"
        self.cinematic_timer = 0.0
        self.cinematic_open_amount = 0.0
        self.cinematic_zoom = 0.0
        self.lock_drop = 0.0
        self.lock_unlocked = False
        self.cinematic_sfx_flags.clear()
        self._spawn_win_particles()
        self.game.audio.play_sfx("success")

        elapsed = (pygame.time.get_ticks() - self.start_ticks) / 1000.0
        stars = self.game.save_manager.compute_stars(self.attempts, self.hints_used, elapsed)
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "difficulty": self.config.key,
            "code_length": self.config.length,
            "charset_type": "numeric" if set(self.config.symbols) <= set("0123456789") else "mixed",
            "attempts": self.attempts,
            "hints_used": self.hints_used,
            "solved": True,
            "solve_seconds": round(elapsed, 2),
            "stars_awarded": stars,
        }
        self.game.save_manager.record_round(result)
        self.game.last_round_result = result

    def _wrong_guess(self):
        self.attempts += 1
        self.weak_meter = min(1.0, self.weak_meter + 0.10)
        wrong_tips = [
            "Nope! Try again, matey!",
            "Crackers! That was not right!",
            "Shiver me passwords! Keep trying!",
            "Almost... or maybe not! SQUAWK!",
            "A cyber-pirate would try faster. You can do it!",
        ]
        self.parrot_line = random.choice(wrong_tips)
        self.parrot_emotion = "angry"
        self.chest_state = "shake"
        self.shake_timer = 0.38
        self.screen_shake_timer = 0.25
        self.game.audio.play_sfx("clunk")

    def _reveal_hint(self):
        hidden = [i for i, v in enumerate(self.revealed) if v is None]
        if not hidden:
            self.parrot_line = "No more hints, captain! Virgil spilled 'em all!"
            self.parrot_emotion = "surprised"
            return
        idx = random.choice(hidden)
        self.revealed[idx] = self.secret[idx]
        self.hints_used += 1
        self.parrot_line = f"Virgil hint ho! Spot {idx + 1} is '{self.secret[idx]}'"
        self.parrot_emotion = "talk"
        self.virgil_quote_timer = 0.0
        self.virgil_next_quote_delay = random.uniform(6.0, 10.0)
        self.game.audio.play_sfx("click")

    def handle_event(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        pos = event.pos

        if self.home_button.clicked(pos):
            self.game.audio.play_sfx("click")
            self.game.switch_scene("landing")
            return

        if self.win:
            if self.cinematic_zoom > 0.78:
                for hotspot in self.coin_hotspots:
                    if hotspot.collidepoint(pos):
                        self._spawn_coin_clink_fx(pos[0], pos[1])
                        self.game.audio.play_sfx("coins_clink")
                        return
            if self.lesson_button.clicked(pos):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("lesson")
            return

        if self._virgil_rect().collidepoint(pos):
            self._reveal_hint()
            return

        for dial in self.dials:
            if dial.up_rect.collidepoint(pos):
                dial.increment(1)
                self.parrot_emotion = "surprised"
                self.game.audio.play_sfx("dial")
                return
            if dial.down_rect.collidepoint(pos):
                dial.increment(-1)
                self.parrot_emotion = "surprised"
                self.game.audio.play_sfx("dial")
                return

        if self.try_button.clicked(pos):
            guess = self._guess()
            if guess == self.secret:
                self._resolve_success()
            else:
                self._wrong_guess()
            return

    def update(self, dt):
        for dial in self.dials:
            dial.update(dt)

        for p in self.sparkles:
            p.update(dt)
        self.sparkles = [p for p in self.sparkles if p.alive()]

        for p in self.treasure:
            p.update(dt)
        self.treasure = [p for p in self.treasure if p.alive()]

        if self.shake_timer > 0:
            self.shake_timer -= dt
        elif self.chest_state == "shake":
            self.chest_state = "closed"
            self.parrot_emotion = "talk"

        if self.screen_shake_timer > 0:
            self.screen_shake_timer -= dt

        if self.win:
            self.cinematic_timer += dt

            if self.cinematic_timer >= 0.18 and "unlock" not in self.cinematic_sfx_flags:
                self.cinematic_sfx_flags.add("unlock")
                self.lock_unlocked = True
                self.game.audio.play_sfx("clunk")

            self.lock_drop = self._ease((self.cinematic_timer - 0.18) / 0.55)
            self.cinematic_open_amount = self._ease((self.cinematic_timer - 0.35) / 1.15)
            self.cinematic_zoom = self._ease((self.cinematic_timer - 1.15) / 1.2)

            if self.cinematic_timer >= 0.92 and "reward" not in self.cinematic_sfx_flags:
                self.cinematic_sfx_flags.add("reward")
                self.game.audio.play_sfx("reward")

            if self.cinematic_timer >= 1.55 and "confetti" not in self.cinematic_sfx_flags:
                self.cinematic_sfx_flags.add("confetti")
                self.game.audio.play_sfx("confetti")

            if self.cinematic_zoom > 0.7 and self.parrot_line != "Pirate gold! Tap the coins to hear them clink! SQUAWK!":
                self.parrot_line = "Pirate gold! Tap the coins to hear them clink! SQUAWK!"

        if not self.win:
            self.virgil_quote_timer += dt
            if self.virgil_quote_timer >= self.virgil_next_quote_delay:
                self.parrot_line = self._next_virgil_quote()
                self.last_virgil_quote = self.parrot_line
                self.parrot_emotion = random.choice(["talk", "surprised"])
                self.virgil_quote_timer = 0.0
                self.virgil_next_quote_delay = random.uniform(6.0, 12.0)

            # Proactive hints in presentation mode after some time
            if self.is_presentation and not self.win:
                self.proactive_hint_timer += dt
                if self.proactive_hint_timer >= 15.0 and self.attempts >= 3:
                    hidden = [i for i, v in enumerate(self.revealed) if v is None]
                    if hidden:
                        self.parrot_line = "Need help? Click me for a hint! SQUAWK!"
                        self.parrot_emotion = "talk"
                        self.proactive_hint_timer = 0.0

        # Set completed after win cinematic finishes
        if self.win and self.cinematic_zoom >= 0.95:
            self.completed = True

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        # Red flash on wrong guess
        if self.screen_shake_timer > 0:
            intensity = self.screen_shake_timer / 0.25
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 40, 40, int(50 * intensity)))
            screen.blit(flash, (0, 0))

        self.coin_hotspots.clear()

        if self.win:
            draw_chest_fallback(
                screen,
                (450, 340),
                t,
                open_amount=self.cinematic_open_amount,
                shake=0.0,
                lock_unlocked=self.lock_unlocked,
                lock_drop=self.lock_drop,
                show_coins=self.cinematic_open_amount > 0.55,
                coin_shimmer=self.cinematic_timer,
            )
        else:
            self.game.sprite_manager.draw_chest(
                screen,
                (450, 340),
                self.chest_state,
                t,
                fallback=lambda s: draw_chest_fallback(s, (450, 340), t, open_amount=0.0, shake=1.0 if self.chest_state == "shake" else 0.0),
            )

        emotion_map = {"talk": "talk", "angry": "angry", "surprised": "surprised", "cheer": "cheer"}
        emotion = emotion_map.get(self.parrot_emotion, "idle")
        virgil_y = self.virgil_pos[1] + int(math.sin(t * 3.0) * 6)
        self.game.sprite_manager.draw_parrot(
            screen,
            (self.virgil_pos[0], virgil_y),
            emotion,
            t,
            fallback=lambda s: draw_parrot_fallback(s, self.virgil_pos[0], virgil_y, t, emotion=emotion),
        )

        # Clickable glow hint around Virgil
        if not self.win:
            glow_alpha = int(40 + 30 * abs(math.sin(t * 3)))
            glow_surf = pygame.Surface((220, 220), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (255, 255, 100, glow_alpha), (110, 110), 100)
            screen.blit(glow_surf, (self.virgil_pos[0] - 110, virgil_y - 110))

        draw_text_outline(screen, "Virgil", self.game.fonts.tiny, YELLOW, BLACK,
                          (self.virgil_pos[0], virgil_y + 110), center=True)
        if not self.win:
            draw_text_outline(screen, "(click for hint)", self.game.fonts.tiny, (200, 200, 150), BLACK,
                              (self.virgil_pos[0], virgil_y + 134), center=True)

        # Title + difficulty (above chest, clear area)
        title = "Chest Unlocked! Treasure Reveal" if self.win else f"Crack the {self.config.length}-char code!"
        title_color = YELLOW if self.win else ORANGE
        draw_text_outline(screen, title, self.game.fonts.big, title_color, BLACK, (380, 198), center=True)
        diff_line = "Legendary Reward Sequence" if self.win else f"Difficulty: {self.config.label}"
        draw_text_outline(screen, diff_line, self.game.fonts.small, CYAN, BLACK, (380, 266), center=True)

        # Speech bubble — positioned below the title, left side, not overlapping Virgil or dials
        bubble_rect = pygame.Rect(30, 14, 620, 110)
        self.draw_speech_bubble(self.parrot_line, tail_x=680, tail_y=virgil_y - 50,
                                bubble_rect=bubble_rect, font=self.game.fonts.tiny)

        if not self.win:
            for dial in self.dials:
                dial.draw(screen, self.game.fonts)

        if not self.win:
            self.try_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.home_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        if self.win:
            if not self.is_presentation:
                self.lesson_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            if self.cinematic_zoom > 0.78:
                # Show Nina cheering on success
                self.draw_character_portrait("nina", (80, 540), 60)

        tries_rect = pygame.Rect(666, 250, 212, 60)
        if not self.win:
            draw_panel(screen, tries_rect, bg_color=(36, 64, 112), border_color=(188, 214, 255))
            draw_text_outline(screen, f"Tries: {self.attempts}", self.game.fonts.small, YELLOW, BLACK, tries_rect.center, center=True)

            hint_text = " ".join(v if v is not None else "?" for v in self.revealed)
            draw_text_outline(screen, f"Hints: {hint_text}", self.game.fonts.tiny, WHITE, BLACK, (450, 496), center=True)

            # Weak meter
            x, y, w, h = 300, 546, 300, 34
            pygame.draw.rect(screen, (238, 224, 203), (x - 5, y - 5, w + 10, h + 10), border_radius=12)
            pygame.draw.rect(screen, BLACK, (x - 5, y - 5, w + 10, h + 10), width=3, border_radius=12)
            pygame.draw.rect(screen, (120, 50, 50), (x, y, w, h), border_radius=10)
            fill = int(w * self.weak_meter)
            if fill > 0:
                pygame.draw.rect(screen, RED, (x, y, fill, h), border_radius=10)
            draw_text_outline(screen, "Weak Password Meter", self.game.fonts.tiny, YELLOW, BLACK, (450, y - 14), center=True)

        self.draw_particles(self.treasure)
        self.draw_particles(self.sparkles)
        self._draw_coin_zoom_panel(screen, t)


class LessonScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.to_builder_button = Button((90, 520, 340, 64), "BUILD PASSWORD", (84, 190, 96), (110, 214, 122), pulse=False)
        self.play_again_button = Button((470, 520, 340, 64), "PLAY AGAIN", (255, 172, 50), (255, 196, 80), pulse=False)

    def enter(self, payload=None):
        self.completed = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.is_presentation and self.to_builder_button.clicked(event.pos):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("builder")
                return
            if not self.is_presentation and self.play_again_button.clicked(event.pos):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("crack")
                return

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 20, 38, 170))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(30, 30, 840, 560)
        draw_panel(screen, panel)

        # Title
        draw_text_outline(screen, "What We Learned!", self.game.fonts.med, RED, BLACK,
                          (panel.centerx, panel.top + 38), center=True)

        # Stars
        result = self.game.last_round_result or {}
        stars = result.get("stars_awarded", 0)
        if stars > 0:
            # Draw star icons
            star_text = ""
            for _ in range(stars):
                star_text += "* "
            draw_text_outline(screen, f"Stars: {star_text.strip()}", self.game.fonts.small,
                              YELLOW, BLACK, (panel.centerx, panel.top + 78), center=True)

        # Lesson cards — each is a small panel with portrait + text
        lessons = [
            ("captain", "Longer passwords are harder to crack!", (60, 130, 60)),
            ("captain", "Mix LETTERS + NUMBERS + SYMBOLS!", (60, 130, 60)),
            ("gibbs", "I used 'password123'... now I am a GHOST!", (120, 80, 80)),
            ("captain", "NEVER share your password!", (60, 130, 60)),
            ("virgil", "Only share with parents. SQUAWK!", (50, 140, 70)),
        ]

        card_x = panel.left + 18
        card_w = panel.width - 36
        card_h = 56
        y_start = panel.top + 108

        for idx, (char_id, text, card_tint) in enumerate(lessons):
            cy = y_start + idx * (card_h + 8)

            # Card background
            card_rect = pygame.Rect(card_x, cy, card_w, card_h)
            pygame.draw.rect(screen, card_tint, card_rect, border_radius=14)
            pygame.draw.rect(screen, (40, 30, 20), card_rect, width=2, border_radius=14)

            # Portrait on left
            portrait_cx = card_x + 32
            portrait_cy = cy + card_h // 2
            self.draw_character_portrait(char_id, (portrait_cx, portrait_cy), 38)

            # Text — use tiny font and wrap within card width
            text_x = card_x + 60
            text_max_w = card_w - 80
            lines = wrap_text(text, self.game.fonts.tiny, text_max_w)
            if len(lines) == 1:
                draw_text_outline(screen, lines[0], self.game.fonts.tiny, WHITE, BLACK,
                                  (text_x, cy + card_h // 2 - 2), center=False)
            else:
                for li, line in enumerate(lines[:2]):
                    draw_text_outline(screen, line, self.game.fonts.tiny, WHITE, BLACK,
                                      (text_x, cy + 14 + li * 24), center=False)

        # Example password
        example_y = y_start + len(lessons) * (card_h + 8) + 10
        draw_text_outline(screen, "Strong example:", self.game.fonts.tiny, BLACK, YELLOW,
                          (panel.centerx - 60, example_y), center=True)
        draw_text_outline(screen, "C@pt@in$tar42!", self.game.fonts.small, DARK_BLUE, BLACK,
                          (panel.centerx + 100, example_y), center=True)

        # Buttons
        if not self.is_presentation:
            self.to_builder_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            self.play_again_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)


class BuilderScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.password = ""
        self.strength = 0
        self.parrot_line = "Build a mighty password with letters, numbers, and symbols!"
        self.parrot_emotion = "talk"

        self.add_letter_button = Button((40, 324, 250, 95), "ADD LETTER", (78, 139, 255), (100, 157, 255))
        self.add_number_button = Button((325, 324, 250, 95), "ADD NUMBER", (80, 196, 107), (111, 214, 130))
        self.add_symbol_button = Button((610, 324, 250, 95), "ADD SYMBOL", (255, 146, 68), (255, 168, 97))
        self.backspace_button = Button((170, 438, 250, 82), "UNDO", (204, 96, 72), (226, 119, 92), pulse=False)
        self.clear_button = Button((480, 438, 250, 82), "CLEAR", (148, 94, 206), (170, 115, 224), pulse=False)
        self.finish_button = Button((250, 534, 400, 58), "DONE", (252, 170, 35), (255, 196, 80), pulse=False)

        self.confetti: list[Particle] = []
        self.sparkles: list[Particle] = []
        self.confetti_done = False
        self.saved_strength = False

    def enter(self, payload=None):
        self.completed = False
        self.password = ""
        self.strength = 0
        self.parrot_line = "Mix letters, numbers and symbols for a treasure-proof password!"
        self.parrot_emotion = "talk"
        self.confetti.clear()
        self.sparkles.clear()
        self.confetti_done = False
        self.saved_strength = False
        self.milestone_shown = set()  # Track which strength milestones triggered

    def _calculate_strength(self, pwd):
        if not pwd:
            return 0
        length_score = min(len(pwd), 12) / 12 * 55
        has_lower = any(c.islower() for c in pwd)
        has_upper = any(c.isupper() for c in pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_symbol = any(not c.isalnum() for c in pwd)
        variety = sum([has_lower, has_upper, has_digit, has_symbol])
        variety_score = (variety / 4) * 35
        unique_bonus = min(len(set(pwd)), 10) / 10 * 10
        return min(100, int(length_score + variety_score + unique_bonus))

    def _spawn_sparkles(self, x, y, count=16):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(20, 120)
            self.sparkles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    size=random.uniform(2, 5),
                    life=random.uniform(0.45, 1.0),
                    max_life=1.0,
                    color=random.choice([GOLD, WHITE, YELLOW]),
                    gravity=25,
                )
            )

    def _spawn_confetti(self):
        for _ in range(180):
            self.confetti.append(
                Particle(
                    x=random.uniform(120, 780),
                    y=random.uniform(50, 180),
                    vx=random.uniform(-100, 100),
                    vy=random.uniform(-70, 180),
                    size=random.uniform(4, 8),
                    life=random.uniform(1.8, 3.2),
                    max_life=3.2,
                    color=random.choice([RED, YELLOW, GREEN, BLUE, ORANGE, (255, 255, 255)]),
                    gravity=280,
                )
            )

    def _append_char(self, kind):
        if len(self.password) >= 24:
            self.parrot_line = "That is already a mega-password!"
            self.parrot_emotion = "cheer"
            return

        if kind == "letter":
            self.password += random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        elif kind == "number":
            self.password += random.choice("0123456789")
        elif kind == "symbol":
            self.password += random.choice("!@#$%^&*?+-_=~")

        self.strength = self._calculate_strength(self.password)
        self._spawn_sparkles(450, 282)

        # Character-based milestone reactions
        from .dialogue import BUILDER_MILESTONES
        if self.strength >= 100 and not self.confetti_done:
            self.confetti_done = True
            ml = BUILDER_MILESTONES.get(100)
            self.parrot_line = ml.text if ml else "TREASURE-SAFE!"
            self.parrot_emotion = "cheer"
            self._spawn_confetti()
            self.game.audio.play_sfx("confetti")
            self.game.audio.play_sfx("reward")
            self.completed = True  # Signal presentation mode
        elif self.strength >= 80 and 80 not in self.milestone_shown:
            self.milestone_shown.add(80)
            ml = BUILDER_MILESTONES.get(80)
            self.parrot_line = ml.text if ml else "Very strong!"
            self.parrot_emotion = "cheer"
            self.game.audio.play_sfx("click")
        elif self.strength >= 50 and 50 not in self.milestone_shown:
            self.milestone_shown.add(50)
            ml = BUILDER_MILESTONES.get(50)
            self.parrot_line = ml.text if ml else "Getting stronger!"
            self.parrot_emotion = "talk"
            self.game.audio.play_sfx("click")
        elif self.strength >= 25 and 25 not in self.milestone_shown:
            self.milestone_shown.add(25)
            ml = BUILDER_MILESTONES.get(25)
            self.parrot_line = ml.text if ml else "Good start!"
            self.parrot_emotion = "talk"
            self.game.audio.play_sfx("click")
        else:
            tips = [
                "Good start! Do not use your real name or birthday!",
                "Keep building -- mix letters AND numbers AND symbols!",
                "Longer passwords protect your treasure even better!",
            ]
            self.parrot_line = random.choice(tips)
            self.parrot_emotion = "talk"
            self.game.audio.play_sfx("click")

    def _persist_builder_result_once(self):
        if self.saved_strength:
            return
        self.game.save_manager.record_builder_strength(self.strength)
        self.saved_strength = True

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.add_letter_button.clicked(pos):
                self._append_char("letter")
                return
            if self.add_number_button.clicked(pos):
                self._append_char("number")
                return
            if self.add_symbol_button.clicked(pos):
                self._append_char("symbol")
                return
            if self.backspace_button.clicked(pos):
                self.password = self.password[:-1]
                self.strength = self._calculate_strength(self.password)
                self.parrot_line = "Trimmed one!"
                self.parrot_emotion = "surprised"
                self.game.audio.play_sfx("click")
                return
            if self.clear_button.clicked(pos):
                self.password = ""
                self.strength = 0
                self.confetti_done = False
                self.parrot_line = "Fresh start, captain!"
                self.parrot_emotion = "talk"
                self.game.audio.play_sfx("click")
                return
            if self.finish_button.clicked(pos):
                self._persist_builder_result_once()
                self.game.audio.play_sfx("click")
                self.game.switch_scene("landing")
                return

    def update(self, dt):
        for p in self.sparkles:
            p.update(dt)
        self.sparkles = [p for p in self.sparkles if p.alive()]

        for p in self.confetti:
            p.update(dt)
        self.confetti = [p for p in self.confetti if p.alive()]

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        self.game.sprite_manager.draw_chest(
            screen,
            (450, 340),
            "open",
            t,
            fallback=lambda s: draw_chest_fallback(s, (450, 340), t, open_amount=1.0, shake=0.0),
        )

        # Parrot on the right, speech bubble above — no overlap with password box
        emotion = "cheer" if self.parrot_emotion == "cheer" else "talk"
        parrot_x, parrot_y = 820, 440
        parrot_bob_y = parrot_y + int(math.sin(t * 3.0) * 5)
        self.game.sprite_manager.draw_parrot(
            screen,
            (parrot_x, parrot_bob_y),
            emotion,
            t,
            fallback=lambda s: draw_parrot_fallback(s, parrot_x, parrot_bob_y, t,
                                                     emotion="cheer" if emotion == "cheer" else "happy"),
        )

        # Speech bubble — top-right, doesn't overlap title or password box
        bubble_rect = pygame.Rect(440, 14, 440, 100)
        self.draw_speech_bubble(self.parrot_line, tail_x=760, tail_y=parrot_bob_y - 120,
                                bubble_rect=bubble_rect, font=self.game.fonts.tiny)

        # Password display box
        box = pygame.Rect(80, 182, 740, 68)
        pygame.draw.rect(screen, WHITE, box, border_radius=18)
        pygame.draw.rect(screen, BLACK, box, width=5, border_radius=18)

        # Title drawn after box so it sits on top
        draw_text_outline(screen, "Build Your Own Strong Password!", self.game.fonts.small, YELLOW, BLACK, (360, 130), center=True)

        shown = self.password if self.password else "(click buttons below)"
        if len(shown) > 30:
            shown = shown[:27] + "..."
        draw_text_outline(screen, shown, self.game.fonts.med, BLUE, BLACK, box.center, center=True)

        # Strength bar at y=260, h=52 — gradient from red to yellow to green
        x, y, w, h = 130, 260, 640, 52
        pygame.draw.rect(screen, (217, 233, 220), (x - 6, y - 6, w + 12, h + 12), border_radius=16)
        pygame.draw.rect(screen, BLACK, (x - 6, y - 6, w + 12, h + 12), width=4, border_radius=16)
        pygame.draw.rect(screen, (80, 105, 86), (x, y, w, h), border_radius=14)
        fill = int(w * (self.strength / 100))
        if fill > 0:
            # Gradient color: red(0%) -> orange(30%) -> yellow(60%) -> green(100%)
            s = self.strength / 100.0
            if s < 0.5:
                r = 230
                g = int(80 + 175 * (s / 0.5))
                b = 50
            else:
                r = int(230 - 154 * ((s - 0.5) / 0.5))
                g = int(255 - 59 * ((s - 0.5) / 0.5))
                b = int(50 + 40 * ((s - 0.5) / 0.5))
            bar_color = (r, g, b)
            pygame.draw.rect(screen, bar_color, (x, y, fill, h), border_radius=14)
        # Strength label lives inside the bar — consistent small font, no extra text below buttons
        if self.strength >= 100:
            draw_text_outline(screen, "TREASURE-SAFE!  ★ 100%", self.game.fonts.small, GREEN, BLACK, (450, y + h // 2), center=True)
        else:
            draw_text_outline(screen, f"Strength: {self.strength}%", self.game.fonts.small, YELLOW, BLACK, (450, y + h // 2), center=True)

        self.add_letter_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.add_number_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.add_symbol_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.backspace_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.clear_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        if not self.is_presentation:
            self.finish_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        # Show character portrait based on current strength milestone
        if self.strength >= 80:
            self.draw_character_portrait("captain", (60, 300), 50)
        elif self.strength >= 25:
            self.draw_character_portrait("nina", (60, 300), 50)

        self.draw_particles(self.sparkles)
        self.draw_particles(self.confetti)


class ParentReportScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.back_button = Button((670, 530, 210, 58), "BACK", (77, 151, 252), (104, 171, 255), pulse=False)
        self.clear_button = Button((20, 530, 260, 58), "CLEAR PROGRESS", (205, 89, 79), (230, 111, 101), pulse=False)
        self.confirm = False
        self.confirm_yes = Button((300, 350, 140, 64), "YES", (99, 187, 95), (122, 210, 118), pulse=False)
        self.confirm_no = Button((460, 350, 140, 64), "NO", (189, 101, 97), (211, 126, 120), pulse=False)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.confirm:
                if self.confirm_yes.clicked(pos):
                    self.game.save_manager.clear_progress_keep_settings()
                    self.confirm = False
                    self.game.audio.play_sfx("click")
                    return
                if self.confirm_no.clicked(pos):
                    self.confirm = False
                    self.game.audio.play_sfx("click")
                    return

            if self.back_button.clicked(pos):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("landing")
                return

            if self.clear_button.clicked(pos):
                self.confirm = True
                self.game.audio.play_sfx("click")
                return

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        panel = pygame.Rect(30, 50, 840, 460)
        draw_panel(screen, panel, bg_color=(240, 245, 255), border_color=(64, 90, 140))
        draw_text_outline(screen, "Parent / Teacher Report", self.game.fonts.big, DARK_BLUE, BLACK, (450, 96), center=True)

        summary = self.game.save_manager.parent_summary()

        draw_text_outline(screen, f"Sessions: {summary['sessions']}", self.game.fonts.small, BLACK, WHITE, (90, 150), center=False)
        mins = int(summary["total_time_seconds"] // 60)
        draw_text_outline(screen, f"Play Time: {mins} min", self.game.fonts.small, BLACK, WHITE, (90, 188), center=False)
        draw_text_outline(screen, f"Hint Use / Round: {summary['hint_rate']:.2f}", self.game.fonts.small, BLACK, WHITE, (90, 226), center=False)
        draw_text_outline(screen, f"Builder 80+: {summary['builder_80_count']}", self.game.fonts.small, BLACK, WHITE, (90, 264), center=False)
        draw_text_outline(screen, f"Builder 100: {summary['builder_100_count']}", self.game.fonts.small, BLACK, WHITE, (90, 302), center=False)

        averages = summary["avg_attempts"]
        draw_text_outline(screen, "Average Attempts", self.game.fonts.small, BLUE, BLACK, (510, 150), center=True)
        y = 194
        for diff in DIFFICULTY_ORDER:
            label = self.game.difficulty_manager.get_config(diff).label
            draw_text_outline(screen, f"{label}: {averages[diff]:.2f}", self.game.fonts.small, BLACK, WHITE, (450, y), center=False)
            y += 38

        draw_text_outline(screen, "Recent Rounds", self.game.fonts.small, BLUE, BLACK, (620, 320), center=True)
        y = 350
        for row in summary["recent_rounds"][:6]:
            line = (
                f"{row.get('difficulty', '?')}: tries={row.get('attempts', 0)}, "
                f"hints={row.get('hints_used', 0)}, stars={row.get('stars_awarded', 0)}"
            )
            draw_text_outline(screen, line, self.game.fonts.tiny, BLACK, WHITE, (450, y), center=False)
            y += 28

        self.back_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.clear_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        if self.confirm:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))

            box = pygame.Rect(220, 250, 460, 190)
            draw_panel(screen, box, bg_color=(255, 247, 240), border_color=(120, 70, 60))
            draw_text_outline(screen, "Clear all progress?", self.game.fonts.med, RED, BLACK, (450, 292), center=True)
            draw_text_outline(screen, "Settings (mute/volume) will stay saved.", self.game.fonts.tiny, BLACK, WHITE, (450, 322), center=True)
            self.confirm_yes.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            self.confirm_no.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)


class FinaleScene(BaseScene):
    """Final celebration scene for presentation mode."""

    def __init__(self, game):
        super().__init__(game)
        self.confetti: list[Particle] = []
        self.sparkles: list[Particle] = []
        self.spawn_timer = 0.0

    def enter(self, payload=None):
        self.completed = False
        self.confetti.clear()
        self.sparkles.clear()
        self.spawn_timer = 0.0
        self._spawn_confetti()
        self.game.audio.play_sfx("confetti")
        self.game.audio.play_sfx("reward")

    def _spawn_confetti(self):
        for _ in range(200):
            self.confetti.append(
                Particle(
                    x=random.uniform(50, WIDTH - 50),
                    y=random.uniform(-50, 150),
                    vx=random.uniform(-80, 80),
                    vy=random.uniform(30, 200),
                    size=random.uniform(4, 9),
                    life=random.uniform(3.0, 5.0),
                    max_life=5.0,
                    color=random.choice([RED, YELLOW, GREEN, BLUE, ORANGE, GOLD, WHITE, CYAN]),
                    gravity=180,
                )
            )

    def update(self, dt):
        for p in self.confetti:
            p.update(dt)
        self.confetti = [p for p in self.confetti if p.alive()]

        for p in self.sparkles:
            p.update(dt)
        self.sparkles = [p for p in self.sparkles if p.alive()]

        # Keep spawning confetti
        self.spawn_timer += dt
        if self.spawn_timer >= 3.0 and len(self.confetti) < 50:
            self._spawn_confetti()
            self.spawn_timer = 0.0

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 20, 38, 140))
        screen.blit(overlay, (0, 0))

        # Big finale title with gentle pulse
        title_scale = 1.0 + 0.03 * math.sin(t * 2)
        draw_text_outline(screen, "You Did It, Brave Pirates!", self.game.fonts.huge, YELLOW, BLACK, (450, 100), center=True)

        # Golden rule — pulsing glow
        pulse = abs(math.sin(t * 2.5))
        glow_color = (
            int(255 * 0.7 + 255 * 0.3 * pulse),
            int(220 * 0.7 + 35 * 0.3 * pulse),
            int(50 + 50 * pulse),
        )
        # Draw golden glow behind text
        glow_rect = pygame.Rect(100, 156, 700, 50)
        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        glow_surf.fill((*glow_color, int(60 * pulse)))
        screen.blit(glow_surf, glow_rect.topleft)
        draw_text_outline(screen, "YOUR PASSWORD IS YOUR TREASURE!", self.game.fonts.med, glow_color, BLACK, (450, 180), center=True)

        # Character lineup
        chars = [
            ("virgil", 150),
            ("captain", 350),
            ("nina", 550),
            ("gibbs", 750),
        ]

        for char_id, x in chars:
            if char_id == "virgil":
                self.game.sprite_manager.draw_parrot(screen, (x, 330), "cheer", t)
                draw_text_outline(screen, "Virgil", self.game.fonts.tiny, YELLOW, BLACK, (x, 430), center=True)
            else:
                self.draw_character_portrait(char_id, (x, 330), 100)
                from .dialogue import CHARACTERS
                name = CHARACTERS.get(char_id, {}).get("name", char_id)
                draw_text_outline(screen, name, self.game.fonts.tiny, WHITE, BLACK, (x, 400), center=True)

        # Key takeaways
        tips = [
            "Strong passwords: mix LETTERS + NUMBERS + SYMBOLS",
            "Keep personal info PRIVATE: name, address, birthday",
            "Only share passwords with trusted grown-ups",
        ]
        y = 460
        for tip in tips:
            draw_text_outline(screen, tip, self.game.fonts.tiny, YELLOW, BLACK, (450, y), center=True)
            y += 30

        # Farewell
        draw_text_outline(screen, "Stay safe on the seven seas of the internet!", self.game.fonts.small, CYAN, BLACK, (450, 560), center=True)

        self.draw_particles(self.confetti)
        self.draw_particles(self.sparkles)
