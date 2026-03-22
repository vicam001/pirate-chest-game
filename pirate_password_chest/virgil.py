# === VIRGIL CLASS ===
# The star character: a wise-cracking pirate parrot with Hollywood-quality animation.
# Bright red-and-green macaw with eye-patch, golden pirate hat, earring.
# Drop-in class: call .update(dt) and .draw(surface) each frame.
# Trigger states with .talk(text), .laugh(), .surprise(), .cheer(), .fly_in().
#
# EASY TO CHANGE COLORS OR ADD SPRITES LATER
# Every color is defined as a named constant at the top of the class.

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from .constants import BLACK, FONT_NAME, GOLD, WHITE, YELLOW


# === ANIMATION STATES ===
STATE_IDLE = "idle"
STATE_WING_FLAP = "wing_flap"
STATE_TALKING = "talking"
STATE_LAUGH = "laugh"
STATE_SURPRISED = "surprised"
STATE_CHEER = "cheer"
STATE_FLY_IN = "fly_in"


@dataclass
class _Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: tuple
    gravity: float = 120.0

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = max(0.0, self.life / self.max_life)
        r = max(1, int(self.size * alpha))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), r)


# ---------------------------------------------------------------------------
# EASY TO CHANGE COLORS OR ADD SPRITES LATER
# ---------------------------------------------------------------------------
# Body plumage
BODY_RED = (210, 48, 38)
BODY_RED_LIGHT = (235, 85, 65)
BODY_RED_DARK = (165, 32, 26)
BELLY_CREAM = (255, 230, 185)
BELLY_OUTLINE = (210, 180, 130)

# Wing plumage
WING_GREEN = (32, 162, 75)
WING_GREEN_LIGHT = (60, 195, 105)
WING_GREEN_DARK = (22, 120, 55)
WING_TIP_BLUE = (40, 100, 200)
WING_TIP_YELLOW = (255, 220, 50)

# Tail feathers
TAIL_RED = (200, 45, 35)
TAIL_BLUE = (48, 120, 200)
TAIL_GREEN = (38, 155, 70)
TAIL_YELLOW = (250, 210, 50)

# Head
HEAD_RED = (220, 55, 40)
HEAD_LIGHT = (240, 100, 80)
CHEEK_WHITE = (255, 250, 240)

# Beak
BEAK_DARK = (30, 30, 32)
BEAK_GRAY = (55, 52, 50)
BEAK_HIGHLIGHT = (80, 75, 72)

# Eye
EYE_WHITE = (255, 255, 252)
IRIS_GOLD = (200, 160, 40)
PUPIL = (10, 10, 12)
EYE_OUTLINE = (40, 30, 25)

# Accessories
HAT_GOLD = (220, 180, 50)
HAT_DARK = (170, 130, 30)
HAT_BAND = (60, 35, 20)
FEATHER_WHITE = (255, 250, 245)
EYEPATCH_BLACK = (25, 22, 20)
EYEPATCH_STRAP = (50, 40, 30)
EARRING_GOLD = (245, 210, 60)

# Feet
FEET_GRAY = (90, 85, 80)
FEET_DARK = (60, 55, 50)


class Virgil:
    """Virgil the pirate parrot -- the star of the show."""

    def __init__(self, x: int = 700, y: int = 350) -> None:
        # Position (center of the character)
        self.x = float(x)
        self.y = float(y)
        self.target_x = float(x)
        self.target_y = float(y)

        # State machine
        self.state = STATE_IDLE
        self._state_timer = 0.0
        self._prev_state = STATE_IDLE

        # Wing angle (degrees, 0 = flat along body)
        self._wing_angle = 0.0
        self._wing_target = 0.0
        self._wing_frame = 0  # for flap cycle

        # Beak
        self._beak_open = 0.0  # 0 closed, 1 fully open

        # Head tilt
        self._head_tilt = 0.0  # degrees

        # Eye
        self._blink_timer = 0.0
        self._blink_interval = random.uniform(2.5, 5.0)
        self._is_blinking = False
        self._blink_duration = 0.12
        self._pupil_offset_x = 0.0
        self._pupil_offset_y = 0.0

        # Hat bounce
        self._hat_bounce = 0.0

        # Breathing
        self._breath_phase = 0.0

        # Speech
        self._speech_text = ""
        self._speech_display = ""
        self._speech_timer = 0.0
        self._speech_duration = 0.0
        self._speech_char_timer = 0.0
        self._speech_char_index = 0
        self._speech_font = pygame.font.SysFont(FONT_NAME, 28, bold=True)
        self._speech_active = False
        self._speech_show_bubble = True
        self._speech_cache_text = ""
        self._speech_cache_lines: list[str] = []
        self._speech_cache_surfaces: list[tuple[pygame.Surface, pygame.Surface]] = []
        self._speech_cache_size = (100, 60)

        # Particles
        self._particles: list[_Particle] = []

        # FlyIn
        self._fly_in_start_x = 0.0
        self._fly_in_start_y = 0.0

        # Laugh specifics
        self._laugh_shake = 0.0

        # Cached surfaces for rotated wings (avoid per-frame allocation)
        self._wing_surface_r = self._build_wing_surface()
        self._wing_surface_l = pygame.transform.flip(self._wing_surface_r, True, False)

        # Ticks reference
        self._t = 0.0
        self._last_cheer_sparkle_step = -1

        # Pre-allocated head surface (avoid per-frame allocation)
        self._head_surf = pygame.Surface((200, 200), pygame.SRCALPHA)

        # State handlers (avoid per-frame dict creation)
        self._state_handlers = {
            STATE_IDLE: self._update_idle,
            STATE_WING_FLAP: self._update_wing_flap,
            STATE_TALKING: self._update_talking,
            STATE_LAUGH: self._update_laugh,
            STATE_SURPRISED: self._update_surprised,
            STATE_CHEER: self._update_cheer,
            STATE_FLY_IN: self._update_fly_in,
        }

        # Visibility
        self.visible = True

    def _build_wing_surface(self) -> pygame.Surface:
        wing_surface = pygame.Surface((40, 80), pygame.SRCALPHA)
        pygame.draw.ellipse(wing_surface, WING_GREEN, (4, 0, 32, 65))
        pygame.draw.ellipse(wing_surface, WING_GREEN_LIGHT, (8, 4, 24, 45))
        pygame.draw.ellipse(wing_surface, WING_TIP_BLUE, (6, 48, 28, 16))
        pygame.draw.ellipse(wing_surface, WING_TIP_YELLOW, (8, 58, 24, 14))
        for fi in range(3):
            fy = 14 + fi * 16
            pygame.draw.line(wing_surface, WING_GREEN_DARK, (10, fy), (30, fy + 2), 1)
        pygame.draw.ellipse(wing_surface, WING_GREEN_DARK, (4, 0, 32, 65), width=2)
        return wing_surface

    # === PUBLIC API ===

    def talk(self, text: str, duration_seconds: float = 3.0) -> None:
        self._speech_text = text
        self._speech_display = ""
        self._speech_char_index = 0
        self._speech_char_timer = 0.0
        self._speech_timer = 0.0
        self._speech_duration = duration_seconds
        self._speech_active = True
        self._speech_show_bubble = True
        self._set_state(STATE_TALKING)

    def laugh(self) -> None:
        self._set_state(STATE_LAUGH)
        self._spawn_feather_particles()

    def surprise(self) -> None:
        self._set_state(STATE_SURPRISED)

    def cheer(self) -> None:
        self._set_state(STATE_CHEER)
        self._spawn_sparkle_particles()

    def fly_in(self, land_x: float | None = None, land_y: float | None = None) -> None:
        self._fly_in_start_x = self.target_x + 500
        self._fly_in_start_y = self.target_y - 350
        self.x = self._fly_in_start_x
        self.y = self._fly_in_start_y
        if land_x is not None:
            self.target_x = land_x
        if land_y is not None:
            self.target_y = land_y
        self._set_state(STATE_FLY_IN)

    def set_position(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.target_x = x
        self.target_y = y

    def set_idle_text(self, text: str, show_bubble: bool = True) -> None:
        """Set text to show without changing state to talking."""
        if self.state == STATE_TALKING and text == self._speech_text:
            return
        if (
            self._speech_active
            and self._speech_text == text
            and self._speech_duration >= 999.0
            and self._speech_show_bubble == bool(text) and bool(text) == show_bubble
        ):
            return
        self._speech_text = text
        self._speech_display = text
        self._speech_char_index = len(text)
        self._speech_timer = 0.0
        self._speech_duration = 999.0
        self._speech_active = bool(text)
        self._speech_show_bubble = show_bubble and bool(text)

    def clear_speech(self) -> None:
        self._speech_active = False
        self._speech_show_bubble = False
        self._speech_text = ""
        self._speech_display = ""

    @property
    def is_talking(self) -> bool:
        return self.state == STATE_TALKING

    @property
    def is_busy(self) -> bool:
        return self.state in (STATE_FLY_IN, STATE_LAUGH, STATE_SURPRISED, STATE_CHEER)

    # === STATE MACHINE ===

    def _set_state(self, state: str) -> None:
        self._prev_state = self.state
        self.state = state
        self._state_timer = 0.0
        self._last_cheer_sparkle_step = -1
        if state == STATE_LAUGH:
            self._laugh_shake = 0.0

    def update(self, dt: float) -> None:
        if not self.visible:
            return
        self._t += dt
        self._state_timer += dt
        self._breath_phase += dt * 2.8

        # Blink logic (runs in every state)
        self._update_blink(dt)

        # State-specific update
        handler = self._state_handlers.get(self.state, self._update_idle)
        handler(dt)

        # Smooth wing angle
        self._wing_angle += (self._wing_target - self._wing_angle) * min(1.0, dt * 18)

        # Smooth head tilt toward zero when idle
        if self.state == STATE_IDLE:
            target_tilt = math.sin(self._t * 0.7) * 4
            self._head_tilt += (target_tilt - self._head_tilt) * min(1.0, dt * 3)

        # Hat bounce decay
        self._hat_bounce *= max(0, 1.0 - dt * 8)

        # Particles
        self._particles = [p for p in self._particles if p.update(dt)]

        # Speech timer
        if self._speech_active:
            self._speech_timer += dt
            # Letter-by-letter reveal
            if self._speech_char_index < len(self._speech_text):
                self._speech_char_timer += dt
                chars_per_sec = 40
                while (self._speech_char_timer >= 1.0 / chars_per_sec
                       and self._speech_char_index < len(self._speech_text)):
                    self._speech_char_timer -= 1.0 / chars_per_sec
                    self._speech_char_index += 1
                    self._speech_display = self._speech_text[:self._speech_char_index]
            # Auto-hide after duration (only if all text revealed)
            if (self._speech_char_index >= len(self._speech_text)
                    and self._speech_timer >= self._speech_duration):
                self._speech_active = False

    # --- State updaters ---

    def _update_idle(self, dt: float) -> None:
        # Gentle breathing wing motion
        self._wing_target = 3 + math.sin(self._breath_phase) * 3
        # Occasional random head tilt already handled above
        self._beak_open *= max(0, 1.0 - dt * 10)

    def _update_wing_flap(self, dt: float) -> None:
        # 4-frame flap cycle
        cycle = (self._state_timer * 8) % 4
        if cycle < 1:
            self._wing_target = 35
        elif cycle < 2:
            self._wing_target = 10
        elif cycle < 3:
            self._wing_target = 35
        else:
            self._wing_target = 5
        if self._state_timer > 0.8:
            self._set_state(STATE_IDLE)

    def _update_talking(self, dt: float) -> None:
        # Beak opens/closes in sync with "speech"
        talk_cycle = math.sin(self._state_timer * 14)
        self._beak_open = max(0, talk_cycle) * 0.8
        # Gentle wing movement
        self._wing_target = 5 + math.sin(self._state_timer * 3) * 4
        # Slight head bob
        self._head_tilt = math.sin(self._state_timer * 4) * 3
        # Done talking when speech finishes
        if not self._speech_active:
            self._set_state(STATE_IDLE)

    def _update_laugh(self, dt: float) -> None:
        # Head thrown back, wings shaking
        self._head_tilt = -15 + math.sin(self._state_timer * 20) * 5
        self._laugh_shake = math.sin(self._state_timer * 25) * 4
        self._wing_target = 20 + math.sin(self._state_timer * 12) * 15
        self._beak_open = 0.6 + math.sin(self._state_timer * 10) * 0.3
        self._hat_bounce = abs(math.sin(self._state_timer * 8)) * 6
        self._is_blinking = True  # eyes closed in joy
        if self._state_timer > 1.8:
            self._is_blinking = False
            self._set_state(STATE_IDLE)

    def _update_surprised(self, dt: float) -> None:
        # Eyes wide, feathers ruffled, quick flutter
        self._head_tilt = 8
        self._wing_target = 25 + math.sin(self._state_timer * 18) * 10
        self._beak_open = 0.5
        self._hat_bounce = 4
        self._pupil_offset_y = -2  # pupils look up
        if self._state_timer > 1.2:
            self._pupil_offset_y = 0
            self._set_state(STATE_IDLE)

    def _update_cheer(self, dt: float) -> None:
        # Wild flapping + hat bouncing + sparkles
        self._wing_target = 35 * abs(math.sin(self._state_timer * 10))
        self._hat_bounce = abs(math.sin(self._state_timer * 7)) * 8
        self._head_tilt = math.sin(self._state_timer * 6) * 8
        self._beak_open = 0.3 + abs(math.sin(self._state_timer * 5)) * 0.4
        # Continuous sparkles
        sparkle_step = int(self._state_timer * 15)
        if sparkle_step % 3 == 0 and sparkle_step != self._last_cheer_sparkle_step:
            self._last_cheer_sparkle_step = sparkle_step
            self._spawn_sparkle_particles(count=2)
        if self._state_timer > 2.5:
            self._set_state(STATE_IDLE)

    def _update_fly_in(self, dt: float) -> None:
        # Entrance from top-right with flapping
        progress = min(1.0, self._state_timer / 1.2)
        ease = progress * progress * (3 - 2 * progress)  # smoothstep
        self.x = self._fly_in_start_x + (self.target_x - self._fly_in_start_x) * ease
        self.y = self._fly_in_start_y + (self.target_y - self._fly_in_start_y) * ease
        # Vigorous flapping during flight
        self._wing_target = 35 * abs(math.sin(self._state_timer * 12))
        self._head_tilt = math.sin(self._state_timer * 5) * 6
        if progress >= 1.0:
            self.x = self.target_x
            self.y = self.target_y
            self._hat_bounce = 6  # landing bounce
            self._set_state(STATE_IDLE)

    # --- Blink ---

    def _update_blink(self, dt: float) -> None:
        if self.state == STATE_LAUGH:
            return  # laugh handles its own blink
        self._blink_timer += dt
        if self._is_blinking:
            if self._blink_timer >= self._blink_duration:
                self._is_blinking = False
                self._blink_timer = 0.0
                self._blink_interval = random.uniform(2.5, 5.0)
        else:
            if self._blink_timer >= self._blink_interval:
                self._is_blinking = True
                self._blink_timer = 0.0

    # === DRAWING ===
    # Virgil is drawn as a cartoon parrot viewed from 3/4 angle.
    # Key proportions: BIG head (~45% of height), small body, wings at SIDES.
    # y coordinate = center of body. Head sits above.

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        t = self._t
        ix = int(self.x)
        iy = int(self.y)
        breath = math.sin(self._breath_phase) * 1.5
        shake_x = int(self._laugh_shake) if self.state == STATE_LAUGH else 0
        bx = ix + shake_x  # base x with shake

        # Draw order: tail -> left wing -> feet -> body -> right wing -> head -> particles -> speech
        self._draw_tail(surface, bx, iy, t)
        self._draw_wing(surface, bx, iy, breath, side=-1)  # left wing BEHIND body
        self._draw_feet(surface, bx, iy)
        self._draw_body(surface, bx, iy, breath)
        self._draw_wing(surface, bx, iy, breath, side=1)   # right wing IN FRONT
        self._draw_head(surface, bx, iy, breath, t)
        self._draw_particles(surface)
        if self._speech_active and self._speech_show_bubble and self._speech_display:
            self._draw_speech_bubble(surface, ix, iy)

    # --- Tail feathers (fan downward behind body) ---
    def _draw_tail(self, surface: pygame.Surface, x: int, y: int, t: float) -> None:
        wag = math.sin(t * 3.5) * 4
        colors = [TAIL_RED, TAIL_BLUE, TAIL_GREEN, TAIL_YELLOW, TAIL_RED]
        base_y = y + 40
        for i, col in enumerate(colors):
            angle = 1.2 + (i - 2) * 0.18 + math.sin(t * 2.8 + i * 0.7) * 0.05
            tx = x - 10 + i * 5 + int(wag * 0.15)
            length = 50 - abs(i - 2) * 6
            ex = tx + int(math.cos(angle) * length)
            ey = base_y + int(math.sin(angle) * length)
            w = max(2, 6 - abs(i - 2))
            pygame.draw.line(surface, col, (tx, base_y), (ex, ey), w)
            # Rounded feather tip
            pygame.draw.ellipse(surface, col, (ex - w, ey - 2, w * 2, 6))

    # --- Feet ---
    def _draw_feet(self, surface: pygame.Surface, x: int, y: int) -> None:
        for fx_off in (-12, 8):
            fy = y + 48
            leg_x = x + fx_off
            # Leg
            pygame.draw.line(surface, FEET_GRAY, (leg_x, fy), (leg_x, fy + 14), 4)
            # Three toes spread forward
            for ta in (-0.6, 0.0, 0.6):
                tx = leg_x + int(math.cos(ta) * 10)
                ty = fy + 14 + int(abs(math.sin(ta + 1.0)) * 4) + 3
                pygame.draw.line(surface, FEET_GRAY, (leg_x, fy + 14), (tx, ty), 3)
                pygame.draw.circle(surface, FEET_DARK, (tx, ty), 2)

    # --- Body (smaller, egg-shaped, below the big head) ---
    def _draw_body(self, surface: pygame.Surface, x: int, y: int, breath: float) -> None:
        b = int(breath)
        # Main red body — egg shape
        bw, bh = 56, 62
        body_rect = (x - bw // 2, y + b, bw, bh)
        pygame.draw.ellipse(surface, BODY_RED, body_rect)
        # Lighter front
        fw, fh = 38, 42
        pygame.draw.ellipse(surface, BODY_RED_LIGHT, (x - fw // 2, y + 8 + b, fw, fh))
        # Cream belly
        cw, ch = 28, 30
        pygame.draw.ellipse(surface, BELLY_CREAM, (x - cw // 2, y + 14 + b, cw, ch))
        pygame.draw.ellipse(surface, BELLY_OUTLINE, (x - cw // 2, y + 14 + b, cw, ch), width=1)
        # Feather arcs
        for fy in range(10, 52, 14):
            pygame.draw.arc(surface, BODY_RED_DARK,
                            (x - 20, y + fy + b, 40, 8), 0.3, math.pi - 0.3, 1)
        # Outline
        pygame.draw.ellipse(surface, BODY_RED_DARK, body_rect, width=2)

    # --- Single wing (called once for left=-1, once for right=1) ---
    def _draw_wing(self, surface: pygame.Surface, x: int, y: int,
                   breath: float, side: int) -> None:
        b = int(breath)
        angle = self._wing_angle

        ws = self._wing_surface_l if side == -1 else self._wing_surface_r

        # Rotate around the SHOULDER (top of the wing surface)
        rot_angle = angle * side
        # Pivot is at the top-center of the wing surface
        rotated = pygame.transform.rotate(ws, rot_angle)

        # Shoulder position: at the side of the body, near the top
        shoulder_x = x + side * 28
        shoulder_y = y + 8 + b

        # After rotation, we need to offset so the shoulder stays in place
        rw, rh = rotated.get_size()
        # The pivot was at (20, 0) in the original surface
        pivot_in_orig = (20 if side == 1 else 20, 0)
        # After rotation, find where that pivot ended up
        cos_a = math.cos(math.radians(-rot_angle))
        sin_a = math.sin(math.radians(-rot_angle))
        orig_cx, orig_cy = ws.get_width() / 2, ws.get_height() / 2
        dx = pivot_in_orig[0] - orig_cx
        dy = pivot_in_orig[1] - orig_cy
        new_dx = dx * cos_a - dy * sin_a
        new_dy = dx * sin_a + dy * cos_a
        pivot_in_rotated = (rw / 2 + new_dx, rh / 2 + new_dy)

        blit_x = shoulder_x - pivot_in_rotated[0]
        blit_y = shoulder_y - pivot_in_rotated[1]
        surface.blit(rotated, (int(blit_x), int(blit_y)))

    # --- Head (BIG, with hat, eye-patch, earring, beak) ---
    def _draw_head(self, surface: pygame.Surface, x: int, y: int,
                   breath: float, t: float) -> None:
        b = int(breath)
        hx = x
        hy = y - 22 + b  # head sits on top of body
        tilt = self._head_tilt

        # Head surface — large enough for hat + feather plume
        HS = 200  # head surface size
        head_surf = self._head_surf
        head_surf.fill((0, 0, 0, 0))
        cx, cy = HS // 2, HS // 2 + 10  # center of face within head surface

        # --- Main head shape ---
        head_r = 36
        pygame.draw.circle(head_surf, HEAD_RED, (cx, cy), head_r)
        # Highlight on forehead
        pygame.draw.circle(head_surf, HEAD_LIGHT, (cx - 6, cy - 14), 18)
        # White cheek patch (macaw bare skin area — left cheek)
        pygame.draw.ellipse(head_surf, CHEEK_WHITE, (cx - 32, cy + 4, 24, 18))
        pygame.draw.ellipse(head_surf, (225, 218, 210), (cx - 32, cy + 4, 24, 18), width=1)
        # Head outline
        pygame.draw.circle(head_surf, BODY_RED_DARK, (cx, cy), head_r, width=2)

        # --- Left eye (visible, BIG and expressive) ---
        ex_l, ey_l = cx - 12, cy - 4
        ew, eh = 22, 20
        # White
        pygame.draw.ellipse(head_surf, EYE_WHITE, (ex_l - ew // 2, ey_l - eh // 2, ew, eh))
        if self._is_blinking:
            pygame.draw.arc(head_surf, EYE_OUTLINE,
                            (ex_l - 8, ey_l - 2, 16, 10), 0.3, math.pi - 0.3, 3)
        else:
            px = ex_l + int(self._pupil_offset_x)
            py = ey_l + int(self._pupil_offset_y)
            pygame.draw.circle(head_surf, IRIS_GOLD, (px, py), 7)
            pygame.draw.circle(head_surf, PUPIL, (px, py), 4)
            pygame.draw.circle(head_surf, WHITE, (px + 3, py - 3), 2)
            pygame.draw.circle(head_surf, (230, 235, 245), (px - 1, py + 2), 1)
        pygame.draw.ellipse(head_surf, EYE_OUTLINE, (ex_l - ew // 2, ey_l - eh // 2, ew, eh), width=2)

        # --- Right eye — eye-patch ---
        ex_r, ey_r = cx + 14, cy - 4
        # Strap across head
        pygame.draw.line(head_surf, EYEPATCH_STRAP, (cx - 28, cy - 22), (ex_r + 12, ey_r - 6), 3)
        pygame.draw.line(head_surf, EYEPATCH_STRAP, (ex_r + 12, ey_r - 6), (ex_r + 6, ey_r + 14), 3)
        # Patch
        pygame.draw.circle(head_surf, EYEPATCH_BLACK, (ex_r, ey_r), 11)
        pygame.draw.circle(head_surf, (50, 45, 40), (ex_r, ey_r), 11, width=2)
        # Skull on patch
        pygame.draw.circle(head_surf, (190, 185, 175), (ex_r, ey_r - 1), 4)
        for sx_off in (-2, 2):
            pygame.draw.circle(head_surf, EYEPATCH_BLACK, (ex_r + sx_off, ey_r - 2), 1)
        pygame.draw.line(head_surf, (190, 185, 175), (ex_r - 3, ey_r + 2), (ex_r + 3, ey_r + 2), 1)

        # --- Beak (large, bright yellow-orange, VISIBLE) ---
        beak_open = int(self._beak_open * 10)
        bk_x = cx + 20  # beak starts right of center
        bk_y = cy + 4
        # Upper beak (large, curved, bright)
        upper = [(bk_x, bk_y - 4), (bk_x + 30, bk_y + 2),
                 (bk_x + 26, bk_y + 10), (bk_x, bk_y + 6)]
        pygame.draw.polygon(head_surf, (250, 200, 50), upper)
        pygame.draw.polygon(head_surf, (200, 150, 30), upper, width=2)
        # Hook curve at tip
        pygame.draw.arc(head_surf, (200, 150, 30), (bk_x + 20, bk_y, 14, 14), -0.6, 1.2, 2)
        # Nostril
        pygame.draw.circle(head_surf, (180, 130, 25), (bk_x + 12, bk_y + 1), 2)
        # Lower beak
        lower = [(bk_x, bk_y + 8 + beak_open),
                 (bk_x + 22, bk_y + 12 + beak_open),
                 (bk_x, bk_y + 14 + beak_open)]
        pygame.draw.polygon(head_surf, (230, 180, 40), lower)
        pygame.draw.polygon(head_surf, (180, 130, 25), lower, width=1)
        # Mouth interior
        if self._beak_open > 0.15:
            mouth = [(bk_x + 2, bk_y + 6), (bk_x + 20, bk_y + 10),
                     (bk_x + 18, bk_y + 10 + beak_open), (bk_x + 2, bk_y + 8 + beak_open)]
            pygame.draw.polygon(head_surf, (160, 55, 65), mouth)
            # Tongue
            pygame.draw.ellipse(head_surf, (200, 90, 100),
                                (bk_x + 4, bk_y + 8 + beak_open // 2, 10, 5))

        # --- Earring (gold hoop on left side) ---
        ear_x, ear_y = cx - 30, cy + 16
        pygame.draw.circle(head_surf, EARRING_GOLD, (ear_x, ear_y), 5, width=2)
        pygame.draw.circle(head_surf, (255, 235, 100), (ear_x + 1, ear_y - 2), 2)

        # --- Pirate hat (sits ON TOP of head, clearly above) ---
        hat_y_off = -int(self._hat_bounce)
        hat_cy = cy - 40 + hat_y_off  # well above the head
        # Brim (wide ellipse)
        brim_w, brim_h = 80, 14
        pygame.draw.ellipse(head_surf, HAT_DARK,
                            (cx - brim_w // 2, hat_cy + 12, brim_w, brim_h))
        pygame.draw.ellipse(head_surf, HAT_GOLD,
                            (cx - brim_w // 2 + 2, hat_cy + 13, brim_w - 4, brim_h - 2))
        # Crown (tricorn — upward triangle)
        crown_h = 24
        crown = [(cx - 28, hat_cy + 16), (cx, hat_cy - crown_h + 8), (cx + 28, hat_cy + 16)]
        pygame.draw.polygon(head_surf, HAT_DARK, crown)
        inner_crown = [(cx - 22, hat_cy + 14), (cx, hat_cy - crown_h + 12), (cx + 22, hat_cy + 14)]
        pygame.draw.polygon(head_surf, HAT_GOLD, inner_crown)
        # Band
        pygame.draw.line(head_surf, HAT_BAND, (cx - 24, hat_cy + 14), (cx + 24, hat_cy + 14), 3)
        # Skull emblem
        pygame.draw.circle(head_surf, (235, 230, 220), (cx, hat_cy + 6), 5)
        pygame.draw.circle(head_surf, HAT_DARK, (cx - 2, hat_cy + 5), 1)
        pygame.draw.circle(head_surf, HAT_DARK, (cx + 2, hat_cy + 5), 1)
        pygame.draw.line(head_surf, (210, 205, 195), (cx - 3, hat_cy + 9), (cx + 3, hat_cy + 9), 1)
        # Crossbones behind skull
        pygame.draw.line(head_surf, (210, 205, 195), (cx - 6, hat_cy + 2), (cx + 6, hat_cy + 10), 1)
        pygame.draw.line(head_surf, (210, 205, 195), (cx + 6, hat_cy + 2), (cx - 6, hat_cy + 10), 1)
        # White feather plume (curves upward from right side of hat)
        fw = math.sin(t * 4) * 3
        f_base = (cx + 18, hat_cy)
        f_mid = (cx + 28 + int(fw), hat_cy - 16)
        f_tip = (cx + 22 + int(fw * 1.5), hat_cy - 32)
        pygame.draw.line(head_surf, FEATHER_WHITE, f_base, f_mid, 3)
        pygame.draw.line(head_surf, FEATHER_WHITE, f_mid, f_tip, 2)
        pygame.draw.circle(head_surf, FEATHER_WHITE, f_tip, 3)
        # Feather barbs
        for fb in range(4):
            bp = 0.2 + fb * 0.22
            bfx = int(f_base[0] + (f_tip[0] - f_base[0]) * bp)
            bfy = int(f_base[1] + (f_tip[1] - f_base[1]) * bp)
            pygame.draw.line(head_surf, (245, 240, 235),
                             (bfx, bfy), (bfx + 5 + int(fw * 0.4), bfy - 5), 1)

        # --- Emotion overlays ---
        if self.state == STATE_SURPRISED:
            for i in range(5):
                ang = -1.0 + i * 0.5 + math.sin(t * 8) * 0.1
                lx = cx + int(math.cos(ang) * 42)
                ly = cy + int(math.sin(ang) * 42)
                lx2 = cx + int(math.cos(ang) * 50)
                ly2 = cy + int(math.sin(ang) * 50)
                pygame.draw.line(head_surf, YELLOW, (lx, ly), (lx2, ly2), 3)

        if self.state == STATE_CHEER:
            for i in range(4):
                ang = t * 3 + i * 1.6
                sx = cx + int(math.cos(ang) * 46)
                sy = cy + int(math.sin(ang) * 46)
                pygame.draw.line(head_surf, GOLD, (sx - 5, sy), (sx + 5, sy), 2)
                pygame.draw.line(head_surf, GOLD, (sx, sy - 5), (sx, sy + 5), 2)

        # Emotion expressions
        if self.state == STATE_LAUGH:
            # Rosy cheeks
            pygame.draw.circle(head_surf, (255, 140, 120), (cx - 24, cy + 12), 6)

        if self.state == STATE_CHEER:
            pygame.draw.circle(head_surf, (255, 160, 140), (cx - 24, cy + 12), 5)

        # Rotate head by tilt and blit
        if abs(tilt) > 0.5:
            rotated_head = pygame.transform.rotate(head_surf, tilt)
        else:
            rotated_head = head_surf
        rr = rotated_head.get_rect(center=(hx, hy))
        surface.blit(rotated_head, rr)

    # --- Particles ---
    def _draw_particles(self, surface: pygame.Surface) -> None:
        for p in self._particles:
            p.draw(surface)

    # --- Speech bubble ---
    def _draw_speech_bubble(self, surface: pygame.Surface, x: int, y: int) -> None:
        text = self._speech_display
        if not text:
            return

        font = self._speech_font
        if text != self._speech_cache_text:
            max_w = 340
            words = text.split(" ")
            lines: list[str] = []
            current = ""
            for word in words:
                test = (current + " " + word).strip()
                if font.size(test)[0] <= max_w:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
            lines = lines[:4]

            line_h = font.get_height() + 4
            text_h = len(lines) * line_h
            text_w = max(font.size(line)[0] for line in lines) if lines else 100
            pad = 18
            self._speech_cache_text = text
            self._speech_cache_lines = lines
            self._speech_cache_size = (text_w + pad * 2, text_h + pad * 2)
            self._speech_cache_surfaces = []
            for line in lines:
                outline = font.render(line, True, BLACK)
                base = font.render(line, True, YELLOW)
                self._speech_cache_surfaces.append((outline, base))

        lines = self._speech_cache_lines
        line_h = font.get_height() + 4
        pad = 18
        bw, bh = self._speech_cache_size

        bubble_left = x > 620
        bubble_above = y > 190
        bx = int(x - bw - 54) if bubble_left else int(x + 34)
        by = int(y - 110 - bh) if bubble_above else int(y + 54)
        bx = max(8, min(900 - bw - 8, bx))
        by = max(8, min(600 - bh - 8, by))

        bubble_rect = pygame.Rect(bx, by, bw, bh)

        # Draw Monkey Island style oval bubble
        pygame.draw.ellipse(surface, WHITE, bubble_rect.inflate(8, 8))
        pygame.draw.ellipse(surface, BLACK, bubble_rect.inflate(8, 8), width=3)
        pygame.draw.ellipse(surface, WHITE, bubble_rect)

        # Tail points toward Virgil, and flips under the bubble near the top edge.
        tail_target_x = int(x - 8) if bubble_left else int(x + 16)
        tail_target_y = int(y - 22) if bubble_above else int(y + 8)
        tail_left = max(bubble_rect.left + 18, min(bubble_rect.right - 18, tail_target_x - 10))
        tail_right = max(bubble_rect.left + 18, min(bubble_rect.right - 18, tail_target_x + 10))
        if bubble_above:
            tail_y = bubble_rect.bottom
            tail_pts = [(tail_left, tail_y - 4), (tail_target_x, tail_target_y), (tail_right, tail_y - 4)]
        else:
            tail_y = bubble_rect.top
            tail_pts = [(tail_left, tail_y + 4), (tail_target_x, tail_target_y), (tail_right, tail_y + 4)]
        pygame.draw.polygon(surface, WHITE, tail_pts)
        pygame.draw.polygon(surface, BLACK, tail_pts, width=3)
        base_y = tail_y - 2 if bubble_above else tail_y + 2
        pygame.draw.line(surface, WHITE, (tail_left - 2, base_y), (tail_right + 2, base_y), 5)

        # Draw text
        ty = bubble_rect.top + pad
        for outline, base in self._speech_cache_surfaces:
            lx = bubble_rect.centerx - base.get_width() // 2
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                surface.blit(outline, (lx + ox, ty + oy))
            surface.blit(base, (lx, ty))
            ty += line_h

    # === PARTICLES ===

    def _spawn_sparkle_particles(self, count: int = 12) -> None:
        for _ in range(count):
            ang = random.uniform(0, math.pi * 2)
            speed = random.uniform(40, 140)
            self._particles.append(_Particle(
                x=self.x + random.uniform(-20, 20),
                y=self.y - 20 + random.uniform(-20, 10),
                vx=math.cos(ang) * speed,
                vy=math.sin(ang) * speed - 30,
                life=random.uniform(0.5, 1.2),
                max_life=1.2,
                size=random.uniform(3, 6),
                color=random.choice([GOLD, YELLOW, WHITE, (255, 220, 100)]),
                gravity=60,
            ))

    def _spawn_feather_particles(self, count: int = 8) -> None:
        feather_colors = [BODY_RED, WING_GREEN, TAIL_BLUE, TAIL_YELLOW, HEAD_RED]
        for _ in range(count):
            self._particles.append(_Particle(
                x=self.x + random.uniform(-30, 30),
                y=self.y - 10 + random.uniform(-20, 10),
                vx=random.uniform(-60, 60),
                vy=random.uniform(-80, -20),
                life=random.uniform(0.8, 1.8),
                max_life=1.8,
                size=random.uniform(3, 5),
                color=random.choice(feather_colors),
                gravity=100,
            ))


# === WRONG-GUESS TEACHING LINES ===
# Virgil says one of these (rotated) on every wrong password guess.

VIRGIL_WRONG_GUESS_LINES = [
    "Arrr! That be weaker than a jellyfish handshake! Try more symbols, matey!",
    "Shiver me timbers! Even me pet crab could guess that! Mix in some numbers!",
    "Blimey! That password be as easy as 'password'! Add UPPER and lower letters!",
    "Crackers and cannonballs! A pirate's parrot could crack that! Make it LONGER!",
    "Yo ho NO! That be shorter than me attention span! Keep building, captain!",
    "Walk the plank with THAT password! Toss in a symbol like @ or # -- arrr!",
    "Squawk! Me grandma's parrot uses stronger passwords -- and she be a GHOST!",
    "Barnacles! A one-legged pirate could hop past that lock! Add more variety!",
]
