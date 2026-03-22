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

    def enter(self, payload=None):
        return None

    def handle_event(self, event):
        return None

    def update(self, dt):
        return None

    def draw(self, screen):
        return None

    def draw_world(self, t):
        draw_background(self.game.screen, WIDTH, HEIGHT, t, self.game.wave_phase)
        self.game.sprite_manager.draw_world_overlays(self.game.screen, t)

    def draw_speech_bubble(self, text, tail_x=560, tail_y=170):
        bubble = pygame.Rect(92, 18, 716, 150)
        pygame.draw.rect(self.game.screen, WHITE, bubble, border_radius=26)
        pygame.draw.rect(self.game.screen, BLACK, bubble, width=5, border_radius=26)

        tail = [(tail_x - 40, tail_y), (tail_x, tail_y + 30), (tail_x + 30, tail_y)]
        pygame.draw.polygon(self.game.screen, WHITE, tail)
        pygame.draw.polygon(self.game.screen, BLACK, tail, width=5)

        lines = wrap_text(text, self.game.fonts.small, bubble.width - 40)
        yy = bubble.top + 22
        for line in lines[:3]:
            draw_text_outline(self.game.screen, line, self.game.fonts.small, BLACK, YELLOW, (bubble.centerx, yy), center=True)
            yy += 40

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

        self.skip_button = Button((736, 10, 148, 48), "SKIP", (110, 76, 45), (130, 94, 58), pulse=False)
        self.choice_a_button = Button((118, 458, 300, 78), "CHOICE A", (82, 112, 82), (102, 131, 98), pulse=False)
        self.choice_b_button = Button((482, 458, 300, 78), "CHOICE B", (147, 88, 66), (170, 106, 80), pulse=False)
        self.disembark_button = Button((240, 540, 420, 64), "DISEMBARK!", (176, 124, 60), (198, 145, 78))

        self.questions = [
            {
                "trigger": 0.22,
                "question": "A stranger online asks for your full name and home address. What do you do?",
                "choices": ("KEEP SECRET!", "TELL THEM"),
                "responses": (
                    "Brilliant! Never share your address with strangers online!",
                    "Oh no! Your home address is secret treasure — never share it!",
                ),
                "best": 0,
            },
            {
                "trigger": 0.50,
                "question": "Which password is harder for sneaky pirates to crack?",
                "choices": ("Sun$et#42!", "fluffy"),
                "responses": (
                    "Aye! Mixing letters, numbers and symbols makes super-strong passwords!",
                    "Too easy to guess! Always mix letters, numbers AND symbols!",
                ),
                "best": 0,
            },
            {
                "trigger": 0.78,
                "question": "Your friend wants your password so they can help you. What do you do?",
                "choices": ("KEEP SECRET!", "TELL THEM"),
                "responses": (
                    "Well done! Only share passwords with trusted grown-ups like parents!",
                    "Watch out! Even good friends should not get your password!",
                ),
                "best": 0,
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
        self.progress = 0.0
        self.question_cursor = 0
        self.awaiting_choice = False
        self.active_question = None
        self.status_line = "Captain's Log: Set sail for Password Island! Learn to keep your treasure safe!"
        self.response_timer = 0.0
        self.disembark_ready = False
        self.auto_land_timer = 0.0

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
        self.response_timer = 1.7
        if idx == self.active_question["best"]:
            self.game.audio.play_sfx("success")
        else:
            self.game.audio.play_sfx("clunk")
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
        for idx in range(6):
            dist = 18 + idx * 14 + int((t * 70) % 12)
            wx = int(x + math.cos(back) * dist)
            wy = int(y + math.sin(back) * dist)
            radius = max(2, 7 - idx)
            pygame.draw.circle(screen, (204, 216, 204), (wx, wy), radius, width=2)

    def _draw_galleon(self, screen, pos, heading, t):
        ship = pygame.Surface((168, 118), pygame.SRCALPHA)
        cx, cy = 84, 58
        bob = math.sin(t * 6.0) * 2.5
        cy = int(cy + bob)

        pygame.draw.polygon(ship, (80, 47, 27), [(22, cy + 12), (146, cy + 12), (130, cy + 34), (36, cy + 34)])
        pygame.draw.polygon(ship, (102, 63, 36), [(30, cy + 6), (140, cy + 6), (146, cy + 12), (22, cy + 12)])
        pygame.draw.rect(ship, (196, 148, 72), (60, cy + 18, 46, 8), border_radius=4)

        pygame.draw.line(ship, (86, 52, 29), (77, cy + 8), (77, cy - 46), 5)
        pygame.draw.line(ship, (86, 52, 29), (101, cy + 8), (101, cy - 30), 4)
        pygame.draw.polygon(ship, (232, 228, 211), [(77, cy - 44), (77, cy + 4), (122, cy - 18)])
        pygame.draw.polygon(ship, (205, 199, 181), [(101, cy - 28), (101, cy + 2), (130, cy - 14)])
        pygame.draw.circle(ship, (57, 57, 57), (92, cy - 20), 7, width=2)
        pygame.draw.line(ship, (57, 57, 57), (87, cy - 20), (97, cy - 20), 2)
        pygame.draw.line(ship, (57, 57, 57), (92, cy - 25), (92, cy - 15), 2)

        pygame.draw.circle(ship, (235, 201, 110), (124, cy - 15), 6)
        pygame.draw.circle(ship, (255, 245, 193), (124, cy - 15), 3)
        for spark_x in (50, 93, 132):
            spark_y = cy - 24 + int(math.sin(t * 7.0 + spark_x) * 4)
            pygame.draw.circle(ship, (248, 225, 162), (spark_x, spark_y), 2)

        rotated = pygame.transform.rotozoom(ship, -math.degrees(heading), 1.0)
        rect = rotated.get_rect(center=(int(pos[0]), int(pos[1])))
        screen.blit(rotated, rect)

    def _draw_shark(self, screen, x, y, t):
        fin_sway = math.sin(t * 7.5) * 6.0
        body = pygame.Rect(int(x - 34), int(y - 6), 68, 26)
        pygame.draw.ellipse(screen, (124, 139, 143), body)
        pygame.draw.ellipse(screen, (94, 105, 108), body, width=3)
        fin = [
            (int(x - 2 + fin_sway), int(y - 28)),
            (int(x - 12 + fin_sway), int(y - 2)),
            (int(x + 8 + fin_sway), int(y - 4)),
        ]
        pygame.draw.polygon(screen, (106, 121, 125), fin)
        pygame.draw.circle(screen, WHITE, (int(x + 16), int(y + 2)), 5)
        pygame.draw.circle(screen, BLACK, (int(x + 17), int(y + 2)), 2)
        pygame.draw.arc(screen, BLACK, (int(x + 10), int(y + 2), 16, 10), 0.2, math.pi - 0.2, 2)
        pygame.draw.arc(screen, (224, 233, 226), (int(x - 22), int(y - 15), 24, 15), 0.25, math.pi - 0.25, 2)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_s):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("landing")
                return
            if self.disembark_ready and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("landing")
                return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        if self.skip_button.clicked(event.pos):
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
            self.game.switch_scene("landing")

    def update(self, dt):
        if self.response_timer > 0:
            self.response_timer -= dt

        if self.disembark_ready:
            self.auto_land_timer += dt
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
            self.status_line = "Land ho! You've learned to guard your personal treasure. Well done, Captain!"
            self.game.audio.play_sfx("reward")

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self._draw_chart_background(screen, t)
        self._draw_route(screen)

        ship_x, ship_y, heading = self._route_position(self.progress)
        shark_x = ship_x - 52
        shark_y = ship_y + 28 + math.sin(t * 4.4) * 4.0

        self._draw_ship_wake(screen, ship_x, ship_y, heading, t)
        self._draw_shark(screen, shark_x, shark_y, t)
        self._draw_galleon(screen, (ship_x, ship_y), heading, t)

        title_panel = pygame.Rect(164, 8, 572, 66)
        draw_panel(screen, title_panel, bg_color=(78, 52, 32), border_color=(184, 143, 88))
        draw_text_outline(screen, "Charted Voyage To Password Island", self.game.fonts.med, (245, 213, 133), BLACK, (450, 39), center=True)

        status_panel = pygame.Rect(96, 84, 708, 70)
        draw_panel(screen, status_panel, bg_color=(86, 64, 46), border_color=(198, 159, 103))
        for idx, line in enumerate(wrap_text(self.status_line, self.game.fonts.tiny, status_panel.width - 34)[:2]):
            draw_text_outline(
                screen,
                line,
                self.game.fonts.tiny,
                (247, 226, 174),
                BLACK,
                (status_panel.centerx, status_panel.top + 18 + idx * 24),
                center=True,
            )

        progress_pct = int(self.progress * 100)
        progress_text = f"Route Progress: {progress_pct}%"
        draw_text_outline(screen, progress_text, self.game.fonts.tiny, (88, 56, 31), (240, 220, 177), (154, 564), center=False)

        self.skip_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        if self.awaiting_choice and self.active_question is not None:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((28, 19, 13, 112))
            screen.blit(shade, (0, 0))

            q_panel = pygame.Rect(86, 336, 728, 220)
            draw_panel(screen, q_panel, bg_color=(98, 71, 49), border_color=(204, 165, 108))
            draw_text_outline(screen, "Crew Question", self.game.fonts.small, (248, 216, 138), BLACK, (450, q_panel.top + 28), center=True)

            q_lines = wrap_text(self.active_question["question"], self.game.fonts.tiny, q_panel.width - 46)
            for idx, line in enumerate(q_lines[:2]):
                draw_text_outline(
                    screen,
                    line,
                    self.game.fonts.tiny,
                    (247, 229, 184),
                    BLACK,
                    (q_panel.centerx, q_panel.top + 82 + idx * 24),
                    center=True,
                )

            self.choice_a_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            self.choice_b_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        elif self.disembark_ready:
            self.disembark_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            draw_text_outline(screen, "Press Enter or click Disembark", self.game.fonts.tiny, (244, 222, 173), BLACK, (450, 500), center=True)


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

        self.parrot_pos = (640, 250)
        self.chest_pos = (450, 340)

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

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        self.game.sprite_manager.draw_chest(
            screen,
            self.chest_pos,
            "closed",
            t,
            fallback=lambda s: draw_chest_fallback(s, self.chest_pos, t, open_amount=0.0, shake=0.0),
        )
        self.game.sprite_manager.draw_parrot(
            screen,
            self.parrot_pos,
            "idle",
            t,
            fallback=lambda s: draw_parrot_fallback(s, self.parrot_pos[0], self.parrot_pos[1], t, emotion="happy"),
        )

        draw_text_outline(screen, "Pirate Password Chest", self.game.fonts.huge, YELLOW, BLACK, (450, 208), center=True)
        draw_text_outline(screen, "Arrr You Safe?", self.game.fonts.med, WHITE, BLACK, (450, 296), center=True)

        self.draw_speech_bubble("Ahoy! Protect your info online — and never share your password!", tail_x=628, tail_y=168)

        self.play_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.diff_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.settings_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        stats = self.game.save_manager.stats
        info_panel = pygame.Rect(18, 456, 262, 132)
        draw_panel(screen, info_panel, bg_color=(39, 70, 132), border_color=(188, 214, 255))
        badge_rect = pygame.Rect(32, 476, 72, 72)
        self.game.sprite_manager.draw_badge_icon(screen, badge_rect)
        draw_text_outline(screen, f"Stars: {stats['total_stars']}", self.game.fonts.small, WHITE, BLACK, (120, 490), center=False)
        draw_text_outline(screen, "Last Sticker:", self.game.fonts.tiny, YELLOW, BLACK, (120, 526), center=False)
        reward = stats["last_reward"] if stats["last_reward"] else "None yet"
        reward = self._truncate_to_width(reward, 150)
        draw_text_outline(screen, reward, self.game.fonts.tiny, WHITE, BLACK, (120, 554), center=False)

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
        self.virgil_idle_quotes = [
            "Arrr! Never share your home address with strangers online!",
            "Yo-ho-ho! Your birthday is secret treasure — keep it private!",
            "Blimey! A strong password mixes LETTERS, NUMBERS and SYMBOLS!",
            "Ahoy! Never use your pet's name as a password — pirates guess that!",
            "Squawk! Only share your password with a trusted grown-up like a parent!",
            "Yarr! Strong passwords make sneaky sharks cry salty tears!",
            "Heave-ho! Captain Virgil says: never click links from strangers!",
            "Shiver me timbers! Your school name is private pirate info!",
            "Arrr! A password like 'MyD0g$Fido' is WAY stronger than 'fido'!",
            "Blimey biscuits! Never tell ANYONE your password — it's your secret treasure!",
        ]
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
        self.config = self.game.difficulty_manager.get_config(self.game.current_difficulty)
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
        shade.fill((6, 8, 18, int(90 + self.cinematic_zoom * 92)))
        screen.blit(shade, (0, 0))

        source = pygame.Rect(300, 232, 300, 190)
        target = pygame.Rect(74, 64, 752, 476)
        panel = pygame.Rect(
            int(source.x + (target.x - source.x) * self.cinematic_zoom),
            int(source.y + (target.y - source.y) * self.cinematic_zoom),
            int(source.width + (target.width - source.width) * self.cinematic_zoom),
            int(source.height + (target.height - source.height) * self.cinematic_zoom),
        )

        pygame.draw.rect(screen, (40, 23, 12), panel.inflate(12, 12), border_radius=30)
        pygame.draw.rect(screen, (99, 57, 24), panel, border_radius=28)
        pygame.draw.rect(screen, (221, 174, 70), panel, width=5, border_radius=28)
        glow = pygame.Rect(panel.left + 30, panel.top + 24, panel.width - 60, 44)
        pygame.draw.ellipse(screen, (255, 223, 104, 70), glow)

        draw_text_outline(
            screen,
            "Spanish Gold Coins, XVII Century",
            self.game.fonts.small,
            YELLOW,
            BLACK,
            (panel.centerx, panel.top + 42),
            center=True,
        )
        draw_text_outline(
            screen,
            "Click the treasure for coin-clink FX",
            self.game.fonts.tiny,
            WHITE,
            BLACK,
            (panel.centerx, panel.top + 80),
            center=True,
        )

        coin_area = pygame.Rect(panel.left + 56, panel.top + 116, panel.width - 112, panel.height - 156)
        pygame.draw.rect(screen, (92, 56, 24), coin_area, border_radius=20)
        pygame.draw.rect(screen, (157, 109, 48), coin_area, width=3, border_radius=20)

        self.coin_hotspots = []
        cols = 8
        rows = 4
        for row in range(rows):
            for col in range(cols):
                wobble = math.sin(t * 2.7 + row * 0.8 + col * 0.55)
                px = coin_area.left + 54 + col * ((coin_area.width - 108) // max(1, cols - 1))
                py = coin_area.top + 44 + row * ((coin_area.height - 88) // max(1, rows - 1))
                py -= int(abs(wobble) * 8)
                radius = int(22 - row * 2.4)
                draw_spanish_gold_coin(screen, (px, py), radius, t + row * 0.2, stamp_phase=col * 0.4)
                hotspot = pygame.Rect(px - radius, py - radius, radius * 2, radius * 2)
                self.coin_hotspots.append(hotspot)

        highlight = pygame.Rect(coin_area.left + 16, coin_area.top + 18, coin_area.width - 32, 26)
        pygame.draw.ellipse(screen, (255, 250, 197, 60), highlight)

    def _resolve_success(self):
        self.win = True
        self.chest_state = "closed"
        self.parrot_emotion = "cheer"
        self.parrot_line = "Yarr! The lock pops free. Treasure reveal incoming!"
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
        self.parrot_line = self.game.difficulty_manager.random_tip(self.config.key)
        self.parrot_emotion = "angry"
        self.chest_state = "shake"
        self.shake_timer = 0.38
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

            if self.cinematic_zoom > 0.7 and self.parrot_line != "Aye! XVII-century Spanish doubloons. Tap them to hear the clink!":
                self.parrot_line = "Aye! XVII-century Spanish doubloons. Tap them to hear the clink!"

        if not self.win:
            self.virgil_quote_timer += dt
            if self.virgil_quote_timer >= self.virgil_next_quote_delay:
                self.parrot_line = self._next_virgil_quote()
                self.last_virgil_quote = self.parrot_line
                self.parrot_emotion = random.choice(["talk", "surprised"])
                self.virgil_quote_timer = 0.0
                self.virgil_next_quote_delay = random.uniform(6.0, 12.0)

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)
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

        draw_text_outline(screen, "Virgil", self.game.fonts.tiny, YELLOW, BLACK, (self.virgil_pos[0], virgil_y + 108), center=True)
        self.draw_speech_bubble(self.parrot_line, tail_x=self.virgil_pos[0] - 16, tail_y=virgil_y + 36)

        title = "Chest Unlocked! Treasure Reveal" if self.win else f"Crack the {self.config.length}-char code!"
        title_color = YELLOW if self.win else ORANGE
        draw_text_outline(screen, title, self.game.fonts.big, title_color, BLACK, (450, 198), center=True)
        diff_line = "Legendary Reward Sequence" if self.win else f"Difficulty: {self.config.label}"
        draw_text_outline(screen, diff_line, self.game.fonts.small, CYAN, BLACK, (450, 274), center=True)

        if not self.win:
            for dial in self.dials:
                dial.draw(screen, self.game.fonts)

        if not self.win:
            self.try_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.home_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        if self.win:
            self.lesson_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
            if self.cinematic_zoom > 0.78:
                draw_text_outline(
                    screen,
                    "Click coins for clink FX",
                    self.game.fonts.tiny,
                    WHITE,
                    BLACK,
                    (450, 560),
                    center=True,
                )

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
        self.to_builder_button = Button((80, 492, 380, 74), "BUILD STRONG PASSWORD", (84, 190, 96), (110, 214, 122), pulse=False)
        self.play_again_button = Button((470, 492, 340, 74), "PLAY AGAIN", (255, 172, 50), (255, 196, 80), pulse=False)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.to_builder_button.clicked(event.pos):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("builder")
                return
            if self.play_again_button.clicked(event.pos):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("crack")
                return

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 20, 38, 170))
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(70, 74, 760, 512)
        draw_panel(screen, panel)

        draw_text_outline(screen, "Yarr! Bigger code space = stronger lock!", self.game.fonts.med, RED, BLACK, (450, 118), center=True)

        result = self.game.last_round_result or {}
        stars = result.get("stars_awarded", 0)
        summary = f"Round Stars: {stars}"
        draw_text_outline(screen, summary, self.game.fonts.small, BLUE, BLACK, (450, 160), center=True)

        lines = self.game.difficulty_manager.lesson_lines(self.game.current_difficulty)
        y = 202
        for line in lines:
            draw_text_outline(screen, line, self.game.fonts.small, BLACK, YELLOW, (450, y), center=True)
            y += 44

        example = "Strong example: C@pt@in$tar42!"
        draw_text_outline(screen, example, self.game.fonts.small, DARK_BLUE, BLACK, (450, 462), center=True)

        self.to_builder_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.play_again_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        tip_panel = pygame.Rect(70, 572, 760, 22)
        pygame.draw.rect(screen, (255, 248, 215), tip_panel, border_radius=6)
        pygame.draw.rect(screen, (180, 140, 50), tip_panel, width=2, border_radius=6)
        draw_text_outline(screen, "Remember: Never share passwords or personal info with strangers!", self.game.fonts.tiny, BLACK, YELLOW, (450, 583), center=True)


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
        self.password = ""
        self.strength = 0
        self.parrot_line = "Mix letters, numbers and symbols for a treasure-proof password!"
        self.parrot_emotion = "talk"
        self.confetti.clear()
        self.sparkles.clear()
        self.confetti_done = False
        self.saved_strength = False

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

        if self.strength >= 100 and not self.confetti_done:
            self.confetti_done = True
            self.parrot_line = "Now THAT is a pirate-strong password!"
            self.parrot_emotion = "cheer"
            self._spawn_confetti()
            self.game.audio.play_sfx("confetti")
            self.game.audio.play_sfx("reward")
        elif self.strength >= 80:
            self.parrot_line = "Yarr! Very strong!"
            self.parrot_emotion = "cheer"
            self.game.audio.play_sfx("click")
        elif self.strength >= 50:
            self.parrot_line = "Nice! Add symbols for extra strength."
            self.parrot_emotion = "talk"
            self.game.audio.play_sfx("click")
        else:
            self.parrot_line = "Good start! Keep building."
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

        # Parrot at far right with custom side speech bubble
        emotion = "cheer" if self.parrot_emotion == "cheer" else "talk"
        self.game.sprite_manager.draw_parrot(
            screen,
            (790, 150),
            emotion,
            t,
            fallback=lambda s: draw_parrot_fallback(s, 790, 150, t, emotion="cheer" if emotion == "cheer" else "happy"),
        )
        bubble = pygame.Rect(470, 14, 400, 110)
        pygame.draw.rect(screen, WHITE, bubble, border_radius=22)
        pygame.draw.rect(screen, BLACK, bubble, width=4, border_radius=22)
        tail = [(770, 124), (790, 150), (805, 124)]
        pygame.draw.polygon(screen, WHITE, tail)
        pygame.draw.polygon(screen, BLACK, tail, width=4)
        bubble_lines = wrap_text(self.parrot_line, self.game.fonts.tiny, bubble.width - 24)
        yy = bubble.top + 20
        for line in bubble_lines[:3]:
            draw_text_outline(screen, line, self.game.fonts.tiny, BLACK, YELLOW, (bubble.centerx, yy), center=True)
            yy += 32

        # Password display box (y=182, no overlap with bubble at y=14-124)
        box = pygame.Rect(80, 182, 740, 68)
        pygame.draw.rect(screen, WHITE, box, border_radius=18)
        pygame.draw.rect(screen, BLACK, box, width=5, border_radius=18)

        # Title drawn after box so it sits on top
        draw_text_outline(screen, "Build Your Own Strong Password!", self.game.fonts.small, YELLOW, BLACK, (450, 174), center=True)

        shown = self.password if self.password else "(click buttons below)"
        if len(shown) > 30:
            shown = shown[:27] + "..."
        draw_text_outline(screen, shown, self.game.fonts.med, BLUE, BLACK, box.center, center=True)

        # Strength bar at y=260, h=52
        x, y, w, h = 130, 260, 640, 52
        pygame.draw.rect(screen, (217, 233, 220), (x - 6, y - 6, w + 12, h + 12), border_radius=16)
        pygame.draw.rect(screen, BLACK, (x - 6, y - 6, w + 12, h + 12), width=4, border_radius=16)
        pygame.draw.rect(screen, (80, 105, 86), (x, y, w, h), border_radius=14)
        fill = int(w * (self.strength / 100))
        if fill > 0:
            pygame.draw.rect(screen, GREEN, (x, y, fill, h), border_radius=14)
        draw_text_outline(screen, f"Strength: {self.strength}%", self.game.fonts.small, YELLOW, BLACK, (450, y + h // 2), center=True)

        self.add_letter_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.add_number_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.add_symbol_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.backspace_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.clear_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.finish_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        if self.strength >= 100:
            draw_text_outline(screen, "TREASURE-SAFE PASSWORD!", self.game.fonts.med, GREEN, BLACK, (450, 515), center=True)
        else:
            tip_panel = pygame.Rect(130, 504, 640, 26)
            pygame.draw.rect(screen, (255, 252, 220), tip_panel, border_radius=8)
            pygame.draw.rect(screen, (200, 160, 50), tip_panel, width=2, border_radius=8)
            draw_text_outline(screen, "Tip: Don't use your real name or birthday in your password!", self.game.fonts.tiny, (80, 50, 10), YELLOW, (450, 517), center=True)

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
