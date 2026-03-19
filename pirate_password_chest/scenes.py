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
from .visuals import Particle, draw_background, draw_chest_fallback, draw_parrot_fallback


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

        self.draw_speech_bubble("Ahoy! Protect your treasure with strong passwords, matey!", tail_x=628, tail_y=168)

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

        self.try_button = Button((650, 340, 230, 120), "TRY!", (255, 124, 33), (255, 156, 70), text_color=YELLOW)
        self.hint_button = Button((20, 340, 250, 92), "HINT", (85, 155, 255), (110, 180, 255))
        self.home_button = Button((20, 448, 250, 92), "LANDING", (151, 102, 222), (178, 131, 242), pulse=False)
        self.lesson_button = Button((650, 470, 230, 92), "LESSON", (90, 191, 102), (115, 212, 128), pulse=False)

        self.sparkles: list[Particle] = []
        self.treasure: list[Particle] = []

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
        self.sparkles.clear()
        self.treasure.clear()

    def _build_dials(self, config: DifficultyConfig):
        dials = []
        if config.length == 4:
            xs = [285 + i * 110 for i in range(4)]
            for x in xs:
                dials.append(DialWheel(config.symbols, DialLayout(x, 355, 54)))
        elif config.length == 6:
            xs = [160 + i * 115 for i in range(6)]
            for x in xs:
                dials.append(DialWheel(config.symbols, DialLayout(x, 355, 46)))
        else:
            xs = [190 + i * 170 for i in range(4)]
            for x in xs:
                dials.append(DialWheel(config.symbols, DialLayout(x, 300, 40)))
            for x in xs:
                dials.append(DialWheel(config.symbols, DialLayout(x, 430, 40)))
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

    def _resolve_success(self):
        self.win = True
        self.chest_state = "open"
        self.parrot_emotion = "cheer"
        self.parrot_line = "Yarr! You cracked it! Weak locks fall fast!"
        self._spawn_win_particles()
        self.game.audio.play_sfx("success")

        elapsed = (pygame.time.get_ticks() - self.start_ticks) / 1000.0
        stars = self.game.save_manager.compute_stars(self.attempts, self.hints_used, elapsed)
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "difficulty": self.config.key,
            "code_length": self.config.length,
            "charset_type": "numeric" if self.config.key in ("easy", "medium") else "mixed",
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
            self.parrot_line = "No more hints, captain!"
            self.parrot_emotion = "surprised"
            return
        idx = random.choice(hidden)
        self.revealed[idx] = self.secret[idx]
        self.hints_used += 1
        self.parrot_line = f"Hint ho! Position {idx + 1} is '{self.secret[idx]}'"
        self.parrot_emotion = "talk"
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
            if self.lesson_button.clicked(pos):
                self.game.audio.play_sfx("click")
                self.game.switch_scene("lesson")
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

        if self.hint_button.clicked(pos):
            self._reveal_hint()

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

    def draw(self, screen):
        t = pygame.time.get_ticks() / 1000.0
        self.draw_world(t)

        self.game.sprite_manager.draw_chest(
            screen,
            (450, 340),
            self.chest_state,
            t,
            fallback=lambda s: draw_chest_fallback(s, (450, 340), t, open_amount=1.0 if self.win else 0.0, shake=1.0 if self.chest_state == "shake" else 0.0),
        )

        emotion_map = {"talk": "talk", "angry": "angry", "surprised": "surprised", "cheer": "cheer"}
        emotion = emotion_map.get(self.parrot_emotion, "idle")
        self.game.sprite_manager.draw_parrot(
            screen,
            (575, 175),
            emotion,
            t,
            fallback=lambda s: draw_parrot_fallback(s, 575, 175, t, emotion=emotion),
        )

        self.draw_speech_bubble(self.parrot_line, tail_x=560, tail_y=168)

        draw_text_outline(screen, f"Crack the {self.config.length}-char code!", self.game.fonts.big, YELLOW, BLACK, (450, 198), center=True)
        draw_text_outline(screen, f"Difficulty: {self.config.label}", self.game.fonts.small, CYAN, BLACK, (450, 274), center=True)

        for dial in self.dials:
            dial.draw(screen, self.game.fonts)

        self.try_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.hint_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.home_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        if self.win:
            self.lesson_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        tries_rect = pygame.Rect(666, 250, 212, 60)
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


class LessonScene(BaseScene):
    def __init__(self, game):
        super().__init__(game)
        self.to_builder_button = Button((205, 496, 490, 78), "BUILD STRONG PASSWORD", (84, 190, 96), (110, 214, 122), pulse=False)
        self.play_again_button = Button((305, 550, 290, 45), "PLAY AGAIN", (255, 172, 50), (255, 196, 80), pulse=False)

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
        y = 210
        for line in lines:
            draw_text_outline(screen, line, self.game.fonts.small, BLACK, YELLOW, (450, y), center=True)
            y += 52

        example = "Example: MyPirateIsland$42!"
        draw_text_outline(screen, example, self.game.fonts.small, DARK_BLUE, BLACK, (450, 430), center=True)

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
        self.password = ""
        self.strength = 0
        self.parrot_line = "Build a mighty password with letters, numbers, and symbols!"
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
        emotion = "cheer" if self.parrot_emotion == "cheer" else "talk"
        self.game.sprite_manager.draw_parrot(
            screen,
            (575, 175),
            emotion,
            t,
            fallback=lambda s: draw_parrot_fallback(s, 575, 175, t, emotion="cheer" if emotion == "cheer" else "happy"),
        )

        self.draw_speech_bubble(self.parrot_line, tail_x=560, tail_y=168)

        draw_text_outline(screen, "Build Your Own Strong Password!", self.game.fonts.big, YELLOW, BLACK, (450, 190), center=True)

        box = pygame.Rect(80, 120, 740, 82)
        pygame.draw.rect(screen, WHITE, box, border_radius=18)
        pygame.draw.rect(screen, BLACK, box, width=5, border_radius=18)

        shown = self.password if self.password else "(click buttons below)"
        if len(shown) > 30:
            shown = shown[:27] + "..."
        draw_text_outline(screen, shown, self.game.fonts.med, BLUE, BLACK, box.center, center=True)

        x, y, w, h = 130, 235, 640, 62
        pygame.draw.rect(screen, (217, 233, 220), (x - 6, y - 6, w + 12, h + 12), border_radius=16)
        pygame.draw.rect(screen, BLACK, (x - 6, y - 6, w + 12, h + 12), width=4, border_radius=16)
        pygame.draw.rect(screen, (80, 105, 86), (x, y, w, h), border_radius=14)
        fill = int(w * (self.strength / 100))
        if fill > 0:
            pygame.draw.rect(screen, GREEN, (x, y, fill, h), border_radius=14)
        draw_text_outline(screen, f"Strength: {self.strength}%", self.game.fonts.med, YELLOW, BLACK, (450, y + h // 2), center=True)

        self.add_letter_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.add_number_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.add_symbol_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.backspace_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.clear_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)
        self.finish_button.draw(screen, self.game.fonts, t, mouse_pos=self.game.mouse_virtual_pos)

        if self.strength >= 100:
            draw_text_outline(screen, "TREASURE-SAFE PASSWORD!", self.game.fonts.med, GREEN, BLACK, (450, 520), center=True)

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
        draw_text_outline(screen, f"Easy: {averages['easy']:.2f}", self.game.fonts.small, BLACK, WHITE, (450, 194), center=False)
        draw_text_outline(screen, f"Medium: {averages['medium']:.2f}", self.game.fonts.small, BLACK, WHITE, (450, 232), center=False)
        draw_text_outline(screen, f"Hard: {averages['hard']:.2f}", self.game.fonts.small, BLACK, WHITE, (450, 270), center=False)

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
