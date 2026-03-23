# === VIRGIL CLASS ===
# The star character: a wise-cracking pirate parrot with premium cartoon-quality
# animation. Vibrant scarlet-red macaw body, emerald-green wings/tail, golden-
# yellow beak and feet, cute pirate flair (eye-patch, tricorne hat, earring).
#
# Drop-in class: call .update(dt) and .draw(surface) each frame.
# Trigger states with .talk(text), .laugh(), .surprise(), .cheer(), .fly_in().
#
# === METHOD CALL REFERENCE (for main game loop) ===
#   virgil.update(dt)                       — call every frame
#   virgil.draw(surface)                    — call every frame
#   virgil.talk(text, duration, show_bubble) — speech + beak animation
#   virgil.laugh()                          — head back, wing flaps, squint eyes
#   virgil.surprise()                       — eyes enlarge, feather ruffle
#   virgil.cheer()                          — wild flapping, sparkles, tail wag
#   virgil.fly_in(land_x, land_y)           — spiral entrance from off-screen
#   virgil.set_position(x, y)              — snap position
#   virgil.is_talking  (property)           — True while in talking state
#   virgil.is_busy     (property)           — True during fly_in/laugh/surprise/cheer
#
# Example scene triggers:
#   wrong guess  → virgil.laugh() + virgil.talk("Arrr, too weak matey!")
#   correct guess→ virgil.cheer()
#   hint given   → virgil.talk(hint_text, duration_seconds=2.5)
#   new scene    → virgil.fly_in(land_x=760, land_y=320)
#   shock moment → virgil.surprise()
#
# EASY TO TUNE SIZES / COLORS — every value is a named constant below.

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Tuple

import pygame

try:
    import pygame.gfxdraw  # anti-aliased drawing where available
    HAS_GFXDRAW = True
except ImportError:
    HAS_GFXDRAW = False

from .constants import BLACK, FONT_NAME, GOLD, WHITE, YELLOW


# === ANIMATION STATES ===
STATE_IDLE = "idle"
STATE_WING_FLAP = "wing_flap"
STATE_TALKING = "talking"
STATE_LAUGH = "laugh"
STATE_SURPRISED = "surprised"
STATE_CHEER = "cheer"
STATE_FLY_IN = "fly_in"


# === PARTICLE SYSTEM ===

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

# === BODY PLUMAGE ===
BODY_RED = (210, 48, 38)
BODY_RED_LIGHT = (235, 85, 65)
BODY_RED_LIGHTER = (245, 120, 95)
BODY_RED_DARK = (165, 32, 26)
BODY_RED_DARKER = (130, 24, 18)
BELLY_CREAM = (255, 200, 100)
BELLY_OUTLINE = (210, 160, 70)
BODY_ORANGE = (255, 165, 60)

# === WING PLUMAGE ===
WING_RED = (210, 48, 38)
WING_ORANGE = (255, 180, 40)
WING_GREEN = (32, 162, 75)
WING_GREEN_LIGHT = (60, 195, 105)
WING_GREEN_DARK = (22, 120, 55)
WING_TIP_BLUE = (40, 100, 200)
WING_TIP_YELLOW = (255, 220, 50)

# === TAIL FEATHERS ===
TAIL_RED = (200, 45, 35)
TAIL_BLUE = (48, 120, 200)
TAIL_GREEN = (38, 155, 70)
TAIL_YELLOW = (250, 210, 50)

# === HEAD ===
HEAD_RED = (220, 55, 40)
HEAD_LIGHT = (240, 100, 80)
HEAD_LIGHTER = (250, 140, 110)
CHEEK_WHITE = (255, 250, 240)
HEAD_GREEN_TUFT = (45, 180, 75)

# === BEAK (golden-yellow macaw beak) ===
BEAK_GOLD = (235, 190, 45)
BEAK_GOLD_LIGHT = (255, 220, 90)
BEAK_GOLD_DARK = (180, 140, 30)
BEAK_HIGHLIGHT = (255, 240, 150)

# === EYE ===
EYE_WHITE = (255, 255, 252)
IRIS_GOLD = (200, 160, 40)
PUPIL = (10, 10, 12)
EYE_OUTLINE = (40, 30, 25)
CATCHLIGHT = (255, 255, 255)

# === ACCESSORIES ===
HAT_GOLD = (220, 180, 50)
HAT_GOLD_LIGHT = (245, 210, 80)
HAT_DARK = (170, 130, 30)
HAT_BAND = (60, 35, 20)
PLUME_RED = (220, 45, 40)
PLUME_RED_LIGHT = (245, 80, 65)
EYEPATCH_BLACK = (25, 22, 20)
EYEPATCH_STRAP = (50, 40, 30)
SKULL_SILVER = (200, 195, 190)
EARRING_GOLD = (245, 210, 60)

# === FEET (golden-yellow) ===
FEET_GOLD = (220, 180, 50)
FEET_GOLD_DARK = (180, 140, 30)

# === SHADOW ===
SHADOW_COLOR = (40, 20, 15)

# === RIM / HIGHLIGHT ===
RIM_GOLD = (255, 235, 150)
RIM_WHITE = (255, 250, 240)


def _aa_circle(surf: pygame.Surface, x: int, y: int, r: int, color: tuple) -> None:
    """Draw an anti-aliased filled circle using gfxdraw if available."""
    if HAS_GFXDRAW and r > 1:
        pygame.gfxdraw.aacircle(surf, x, y, r, color)
        pygame.gfxdraw.filled_circle(surf, x, y, r, color)
    else:
        pygame.draw.circle(surf, color, (x, y), r)


def _ease_out_sine(t: float) -> float:
    return math.sin(t * math.pi * 0.5)


def _ease_in_out(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


class Virgil:
    """Virgil the pirate parrot -- the star of the show.

    A vibrant scarlet-red macaw with emerald-green wings, golden-yellow beak,
    pirate hat, eye-patch, and earring. Fully procedurally drawn with
    pygame.draw calls. Supports idle, talking, laugh, surprise, cheer, and
    fly-in animation states with smooth transitions.
    """

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

        # === WING ===
        self._wing_angle = 0.0
        self._wing_target = 0.0
        self._wing_frame = 0

        # === BEAK ===
        self._beak_open = 0.0  # 0 closed, 1 fully open

        # === HEAD ===
        self._head_tilt = 0.0  # degrees
        self._head_bob_y = 0.0  # vertical offset for talking

        # === EYE ===
        self._blink_timer = 0.0
        self._blink_interval = random.uniform(2.5, 5.0)
        self._is_blinking = False
        self._blink_duration = 0.12
        self._pupil_offset_x = 0.0
        self._pupil_offset_y = 0.0
        self._eye_scale = 1.0  # 1.0 normal, 1.5 for surprise
        self._eye_squint = 0.0  # 0 = normal, 1 = fully squinted

        # === EYEBROW ===
        self._eyebrow_angle = 0.0  # degrees, positive = raised, negative = furrowed

        # === HAT ===
        self._hat_bounce = 0.0

        # === BREATHING / BODY SCALE ===
        self._breath_phase = 0.0
        self._body_scale = 1.0  # for fly-in scaling

        # === FEATHER SWAY ===
        self._feather_sway = 0.0  # wing-tip feather oscillation

        # === TAIL ===
        self._tail_wag = 0.0  # horizontal offset for cheer

        # === IDLE HEAD TILT ===
        self._idle_tilt_timer = 0.0
        self._idle_tilt_interval = random.uniform(4.0, 7.0)
        self._idle_tilt_target = 0.0

        # === SPEECH ===
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

        # === PARTICLES ===
        self._particles: list[_Particle] = []

        # === FLY-IN ===
        self._fly_in_start_x = 0.0
        self._fly_in_start_y = 0.0

        # === LAUGH ===
        self._laugh_shake = 0.0

        # === CACHED SURFACES ===
        self._wing_surface_r = self._build_wing_surface()
        self._wing_surface_l = pygame.transform.flip(self._wing_surface_r, True, False)
        self._body_base_surface = self._build_body_surface()

        # Ticks reference
        self._t = 0.0
        self._last_cheer_sparkle_step = -1

        # Pre-allocated head surface
        self._head_surf = pygame.Surface((220, 220), pygame.SRCALPHA)

        # Shadow surface (semi-transparent)
        self._shadow_surf = pygame.Surface((80, 20), pygame.SRCALPHA)
        pygame.draw.ellipse(self._shadow_surf, (*SHADOW_COLOR, 60), (0, 0, 80, 20))

        # State handlers
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

    # === CACHED SURFACE BUILDERS ===

    def _build_wing_surface(self) -> pygame.Surface:
        """Build a single wing with layered color bands and feather detail."""
        wing_surface = pygame.Surface((50, 90), pygame.SRCALPHA)
        # Top section: RED (shoulder area)
        pygame.draw.ellipse(wing_surface, WING_RED, (5, 0, 40, 32))
        pygame.draw.ellipse(wing_surface, BODY_RED_LIGHT, (10, 4, 28, 20))
        # Upper-middle: ORANGE/YELLOW
        pygame.draw.ellipse(wing_surface, WING_ORANGE, (5, 20, 40, 28))
        # Lower section: GREEN (emerald)
        pygame.draw.ellipse(wing_surface, WING_GREEN, (5, 40, 40, 28))
        pygame.draw.ellipse(wing_surface, WING_GREEN_LIGHT, (10, 44, 30, 20))
        # Tip: BLUE + YELLOW
        pygame.draw.ellipse(wing_surface, WING_TIP_BLUE, (7, 60, 36, 20))
        pygame.draw.ellipse(wing_surface, WING_TIP_YELLOW, (10, 68, 30, 16))
        # Feather separation lines
        for fi in range(5):
            fy = 10 + fi * 15
            pygame.draw.line(wing_surface, WING_GREEN_DARK, (12, fy), (38, fy + 2), 1)
        # Rim highlight on leading edge
        pygame.draw.arc(wing_surface, RIM_GOLD, (4, 0, 42, 70), 0.5, 2.5, 1)
        # Overall outline
        pygame.draw.ellipse(wing_surface, BODY_RED_DARK, (5, 0, 40, 75), width=2)
        return wing_surface

    def _build_body_surface(self) -> pygame.Surface:
        """Build the static body base with gradient shading."""
        bw, bh = 66, 66
        pad = 6
        surf = pygame.Surface((bw + pad * 2, bh + pad * 2), pygame.SRCALPHA)
        cx, cy = surf.get_width() // 2, surf.get_height() // 2

        # Gradient: dark outer → light inner via concentric ellipses
        for i, (w_frac, h_frac, color) in enumerate([
            (1.0, 1.0, BODY_RED_DARKER),
            (0.95, 0.95, BODY_RED_DARK),
            (0.88, 0.88, BODY_RED),
            (0.78, 0.78, BODY_RED_LIGHT),
            (0.65, 0.68, BODY_RED_LIGHTER),
        ]):
            ew = int(bw * w_frac)
            eh = int(bh * h_frac)
            pygame.draw.ellipse(surf, color, (cx - ew // 2, cy - eh // 2, ew, eh))

        # Orange chest band
        ow, oh = 38, 22
        pygame.draw.ellipse(surf, BODY_ORANGE, (cx - ow // 2, cy + 4, ow, oh))
        # Cream belly
        cw_b, ch_b = 30, 32
        pygame.draw.ellipse(surf, BELLY_CREAM, (cx - cw_b // 2, cy + 8, cw_b, ch_b))
        pygame.draw.ellipse(surf, BELLY_OUTLINE, (cx - cw_b // 2, cy + 8, cw_b, ch_b), width=1)
        # Feather arc details
        for fy in range(8, 54, 12):
            pygame.draw.arc(surf, BODY_RED_DARK,
                            (cx - 24, cy - 8 + fy, 48, 8), 0.3, math.pi - 0.3, 1)
        # Rim highlight (top-left)
        pygame.draw.arc(surf, RIM_GOLD, (cx - bw // 2 + 2, cy - bh // 2 + 2, bw - 4, bh - 4),
                        1.8, 3.2, 1)
        # Outer outline
        pygame.draw.ellipse(surf, BODY_RED_DARK, (cx - bw // 2, cy - bh // 2, bw, bh), width=2)
        return surf

    # === PUBLIC API ===

    def talk(self, text: str, duration_seconds: float = 3.0,
             show_bubble: bool = False) -> None:
        self._speech_text = text
        self._speech_display = ""
        self._speech_char_index = 0
        self._speech_char_timer = 0.0
        self._speech_timer = 0.0
        self._speech_duration = duration_seconds
        self._speech_active = True
        self._speech_show_bubble = show_bubble
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
        self._body_scale = 0.3
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

    def set_idle_text(self, text: str, show_bubble: bool = False) -> None:
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
        if state == STATE_SURPRISED:
            self._eye_scale = 1.5
        if state != STATE_SURPRISED:
            self._eye_scale = 1.0
        if state not in (STATE_LAUGH, STATE_TALKING):
            self._eye_squint = 0.0
        if state != STATE_FLY_IN:
            self._body_scale = 1.0

    def update(self, dt: float) -> None:
        if not self.visible:
            return
        self._t += dt
        self._state_timer += dt
        self._breath_phase += dt * 2.8

        # Blink logic (runs in every state)
        self._update_blink(dt)

        # Feather sway (always)
        self._feather_sway = math.sin(self._t * 2.2) * 6

        # State-specific update
        handler = self._state_handlers.get(self.state, self._update_idle)
        handler(dt)

        # Smooth wing angle
        self._wing_angle += (self._wing_target - self._wing_angle) * min(1.0, dt * 18)

        # Smooth head tilt toward target when idle
        if self.state == STATE_IDLE:
            self._idle_tilt_timer += dt
            if self._idle_tilt_timer >= self._idle_tilt_interval:
                self._idle_tilt_timer = 0.0
                self._idle_tilt_interval = random.uniform(4.0, 7.0)
                self._idle_tilt_target = random.uniform(-6, 6)
            self._head_tilt += (self._idle_tilt_target - self._head_tilt) * min(1.0, dt * 2.5)

        # Hat bounce decay
        self._hat_bounce *= max(0, 1.0 - dt * 8)

        # Head bob decay (smooth return to 0)
        self._head_bob_y *= max(0, 1.0 - dt * 6)

        # Eye scale smooth return to 1.0
        if self.state != STATE_SURPRISED:
            self._eye_scale += (1.0 - self._eye_scale) * min(1.0, dt * 5)

        # Eye squint decay
        if self.state not in (STATE_LAUGH, STATE_TALKING):
            self._eye_squint *= max(0, 1.0 - dt * 4)

        # Eyebrow smooth return
        if self.state == STATE_IDLE:
            self._eyebrow_angle *= max(0, 1.0 - dt * 3)

        # Tail wag decay
        if self.state != STATE_CHEER:
            self._tail_wag *= max(0, 1.0 - dt * 5)

        # Body scale smooth return
        if self.state != STATE_FLY_IN:
            self._body_scale += (1.0 - self._body_scale) * min(1.0, dt * 4)

        # Particles
        self._particles = [p for p in self._particles if p.update(dt)]

        # Speech timer
        if self._speech_active:
            self._speech_timer += dt
            if self._speech_char_index < len(self._speech_text):
                self._speech_char_timer += dt
                chars_per_sec = 40
                while (self._speech_char_timer >= 1.0 / chars_per_sec
                       and self._speech_char_index < len(self._speech_text)):
                    self._speech_char_timer -= 1.0 / chars_per_sec
                    self._speech_char_index += 1
                    self._speech_display = self._speech_text[:self._speech_char_index]
            if (self._speech_char_index >= len(self._speech_text)
                    and self._speech_timer >= self._speech_duration):
                self._speech_active = False

    # --- State updaters ---

    def _update_idle(self, dt: float) -> None:
        # Gentle breathing wing motion
        self._wing_target = 3 + math.sin(self._breath_phase) * 3
        # Beak closes smoothly
        self._beak_open *= max(0, 1.0 - dt * 10)
        # Eyebrow neutral
        self._eyebrow_angle *= max(0, 1.0 - dt * 3)

    def _update_wing_flap(self, dt: float) -> None:
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
        # Beak opens/closes rhythmically — 3 states via sine
        talk_cycle = math.sin(self._state_timer * 14)
        self._beak_open = max(0, talk_cycle) * 0.8
        # Gentle wing movement
        self._wing_target = 5 + math.sin(self._state_timer * 3) * 4
        # Head bob forward (small vertical offset)
        self._head_bob_y = math.sin(self._state_timer * 6) * 2.5
        # Slight head tilt
        self._head_tilt = math.sin(self._state_timer * 4) * 3
        # Eyes periodically half-close then open wide
        eye_cycle = math.sin(self._state_timer * 3.5)
        self._eye_squint = max(0, eye_cycle) * 0.4
        # Eyebrow slight raise when talking
        self._eyebrow_angle = 5 + math.sin(self._state_timer * 5) * 3
        # Done talking when speech finishes
        if not self._speech_active:
            self._set_state(STATE_IDLE)

    def _update_laugh(self, dt: float) -> None:
        t = self._state_timer
        # Head thrown back 25 degrees with shake
        self._head_tilt = -25 + math.sin(t * 22) * 5
        self._laugh_shake = math.sin(t * 25) * 4
        # 3 distinct wing flaps over 1.8s
        flap_phase = t * 5.0  # ~3 flaps in 1.8s
        self._wing_target = 10 + abs(math.sin(flap_phase * math.pi)) * 30
        # Beak wide open
        self._beak_open = 0.7 + math.sin(t * 10) * 0.25
        # Hat bounces twice (at ~0.4s and ~1.0s)
        bounce1 = max(0, 1.0 - abs(t - 0.4) * 6) * 8
        bounce2 = max(0, 1.0 - abs(t - 1.0) * 6) * 6
        self._hat_bounce = max(bounce1, bounce2)
        # Eyes squint in joy (not fully closed)
        self._eye_squint = 0.7
        self._is_blinking = False
        # Eyebrow raised in delight
        self._eyebrow_angle = 12
        # Rosy cheeks handled in draw
        if t > 1.8:
            self._eye_squint = 0.0
            self._set_state(STATE_IDLE)

    def _update_surprised(self, dt: float) -> None:
        t = self._state_timer
        # Eyes enlarge 150% for 0.4s then shrink back
        if t < 0.4:
            self._eye_scale = 1.5
        else:
            self._eye_scale = 1.5 - min(1.0, (t - 0.4) * 2.5) * 0.5
        # Head tilted up
        self._head_tilt = 8
        # Single quick wing flap (up fast, down slow)
        if t < 0.3:
            self._wing_target = 40
        elif t < 0.6:
            self._wing_target = 5
        else:
            self._wing_target = 3 + math.sin(self._breath_phase) * 3
        # Beak half open
        self._beak_open = 0.5 * max(0, 1.0 - t * 0.8)
        self._hat_bounce = max(0, 5 * (1.0 - t * 1.2))
        self._pupil_offset_y = -2
        # Eyebrow raised high
        self._eyebrow_angle = 15
        if t > 1.2:
            self._pupil_offset_y = 0
            self._eyebrow_angle = 0
            self._set_state(STATE_IDLE)

    def _update_cheer(self, dt: float) -> None:
        t = self._state_timer
        # Rapid 6-8 frame wing flap loop
        flap_phase = t * 12  # fast flapping
        self._wing_target = 5 + abs(math.sin(flap_phase * math.pi)) * 35
        # Hat bouncing wildly
        self._hat_bounce = abs(math.sin(t * 8)) * 8
        # Head tilting
        self._head_tilt = math.sin(t * 6) * 8
        # Beak opening/closing
        self._beak_open = 0.3 + abs(math.sin(t * 5)) * 0.4
        # Tail wags left-right
        self._tail_wag = math.sin(t * 10) * 8
        # Eyebrow excited
        self._eyebrow_angle = 10
        # Continuous sparkles (orbiting)
        sparkle_step = int(t * 15)
        if sparkle_step % 3 == 0 and sparkle_step != self._last_cheer_sparkle_step:
            self._last_cheer_sparkle_step = sparkle_step
            # Spawn particles in an orbit pattern
            orbit_angle = t * 4
            for i in range(2):
                a = orbit_angle + i * math.pi
                ox = math.cos(a) * 50
                oy = math.sin(a) * 30
                self._particles.append(_Particle(
                    x=self.x + ox,
                    y=self.y - 20 + oy,
                    vx=math.cos(a) * 30,
                    vy=-40 + random.uniform(-20, 0),
                    life=0.8,
                    max_life=0.8,
                    size=random.uniform(3, 6),
                    color=random.choice([GOLD, YELLOW, WHITE, (255, 220, 100)]),
                    gravity=40,
                ))
        if t > 2.5:
            self._set_state(STATE_IDLE)

    def _update_fly_in(self, dt: float) -> None:
        t = self._state_timer
        duration = 1.4
        progress = min(1.0, t / duration)
        ease = _ease_in_out(progress)
        # Spiral path: sine offset on x
        spiral_x = math.sin(progress * math.pi * 3) * 40 * (1.0 - progress)
        self.x = self._fly_in_start_x + (self.target_x - self._fly_in_start_x) * ease + spiral_x
        self.y = self._fly_in_start_y + (self.target_y - self._fly_in_start_y) * ease
        # Scale grows from 0.3 to 1.0
        self._body_scale = 0.3 + 0.7 * ease
        # Vigorous flapping during flight
        self._wing_target = 35 * abs(math.sin(t * 12))
        self._head_tilt = math.sin(t * 5) * 6
        if progress >= 1.0:
            # Landing bounce
            bounce_t = t - duration
            if bounce_t < 0.15:
                self.y = self.target_y - 8 * math.sin(bounce_t / 0.15 * math.pi)
            else:
                self.x = self.target_x
                self.y = self.target_y
                self._hat_bounce = 6
                self._spawn_feather_particles(count=5)
                self._set_state(STATE_IDLE)

    # --- Blink ---

    def _update_blink(self, dt: float) -> None:
        if self.state == STATE_LAUGH:
            return
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
    # Key proportions: BIG head (~45% of height), plump body, short legs.
    # y coordinate = center of body. Head sits above.

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return
        t = self._t
        ix = int(self.x)
        iy = int(self.y)
        breath = math.sin(self._breath_phase) * 1.5
        shake_x = int(self._laugh_shake) if self.state == STATE_LAUGH else 0
        bx = ix + shake_x
        scale = self._body_scale

        # === DROP SHADOW ===
        shadow_w = int(80 * scale)
        shadow_h = int(20 * scale)
        if shadow_w > 4 and shadow_h > 2:
            shadow = pygame.transform.smoothscale(self._shadow_surf, (shadow_w, shadow_h))
            surface.blit(shadow, (bx - shadow_w // 2, iy + int(56 * scale)))

        # Draw order: tail -> left wing -> feet -> body -> right wing -> head -> particles -> speech
        self._draw_tail(surface, bx, iy, t, scale)
        self._draw_wing(surface, bx, iy, breath, side=-1, scale=scale)
        self._draw_feet(surface, bx, iy, scale)
        self._draw_body(surface, bx, iy, breath, scale)
        self._draw_wing(surface, bx, iy, breath, side=1, scale=scale)
        self._draw_head(surface, bx, iy, breath, t, scale)
        self._draw_particles(surface)
        if self._speech_active and self._speech_show_bubble and self._speech_display:
            self._draw_speech_bubble(surface, ix, iy)

    # === TAIL FEATHERS ===
    def _draw_tail(self, surface: pygame.Surface, x: int, y: int, t: float,
                   scale: float = 1.0) -> None:
        wag = math.sin(t * 3.5) * 4 + self._tail_wag
        colors = [TAIL_RED, TAIL_GREEN, TAIL_BLUE, TAIL_YELLOW, TAIL_GREEN, TAIL_RED]
        base_y = y + int(40 * scale)
        for i, col in enumerate(colors):
            angle = 1.2 + (i - 2.5) * 0.16 + math.sin(t * 2.8 + i * 0.7) * 0.05
            tx = x - 12 + int(i * 5 * scale) + int(wag * 0.15)
            length = int((70 - abs(i - 2.5) * 8) * scale)
            ex = tx + int(math.cos(angle) * length)
            ey = base_y + int(math.sin(angle) * length)
            w = max(2, int((9 - abs(i - 2.5) * 1.2) * scale))
            # Gradient: draw 2-3 overlapping lines with color shift
            dark_col = tuple(max(0, c - 35) for c in col)
            pygame.draw.line(surface, dark_col, (tx, base_y), (ex, ey), w + 1)
            pygame.draw.line(surface, col, (tx, base_y), (ex, ey), w)
            # Lighter center stripe
            light_col = tuple(min(255, c + 40) for c in col)
            if w > 3:
                pygame.draw.line(surface, light_col, (tx, base_y), (ex, ey), max(1, w - 3))
            # Rounded feather tip
            pygame.draw.ellipse(surface, col, (ex - w, ey - 2, w * 2, max(4, int(8 * scale))))

    # === FEET ===
    def _draw_feet(self, surface: pygame.Surface, x: int, y: int,
                   scale: float = 1.0) -> None:
        for fx_off in (-12, 8):
            fy = y + int(48 * scale)
            leg_x = x + int(fx_off * scale)
            leg_w = max(3, int(5 * scale))
            leg_len = int(14 * scale)
            # Leg
            pygame.draw.line(surface, FEET_GOLD, (leg_x, fy), (leg_x, fy + leg_len), leg_w)
            # Rim highlight on leg
            pygame.draw.line(surface, FEET_GOLD_DARK, (leg_x + 1, fy), (leg_x + 1, fy + leg_len), 1)
            # Three toes spread forward
            toe_len = int(10 * scale)
            for ta in (-0.6, 0.0, 0.6):
                tx = leg_x + int(math.cos(ta) * toe_len)
                ty = fy + leg_len + int(abs(math.sin(ta + 1.0)) * 4 * scale) + int(3 * scale)
                toe_w = max(2, int(3 * scale))
                pygame.draw.line(surface, FEET_GOLD, (leg_x, fy + leg_len), (tx, ty), toe_w)
                # Tiny claw
                _aa_circle(surface, tx, ty, max(1, int(2 * scale)), FEET_GOLD_DARK)

    # === BODY ===
    def _draw_body(self, surface: pygame.Surface, x: int, y: int,
                   breath: float, scale: float = 1.0) -> None:
        b = int(breath)
        # Breathing scale: body pulses 98-102%
        breath_scale = 1.0 + math.sin(self._breath_phase) * 0.02
        total_scale = scale * breath_scale

        bw, bh = self._body_base_surface.get_size()
        sw = max(4, int(bw * total_scale))
        sh = max(4, int(bh * total_scale))
        scaled = pygame.transform.smoothscale(self._body_base_surface, (sw, sh))
        surface.blit(scaled, (x - sw // 2, y + b - sh // 2 + int(4 * scale)))

    # === WING (single, called for left=-1 and right=1) ===
    def _draw_wing(self, surface: pygame.Surface, x: int, y: int,
                   breath: float, side: int, scale: float = 1.0) -> None:
        b = int(breath)
        angle = self._wing_angle

        ws = self._wing_surface_l if side == -1 else self._wing_surface_r

        # Scale wing if needed
        if abs(scale - 1.0) > 0.01:
            ww, wh = ws.get_size()
            ws = pygame.transform.smoothscale(ws, (max(4, int(ww * scale)),
                                                    max(4, int(wh * scale))))

        rot_angle = angle * side
        rotated = pygame.transform.rotate(ws, rot_angle)

        shoulder_x = x + int(side * 28 * scale)
        shoulder_y = y + int(8 * scale) + b

        rw, rh = rotated.get_size()
        pivot_in_orig = (ws.get_width() // 2, 0)
        orig_cx, orig_cy = ws.get_width() / 2, ws.get_height() / 2
        dx = pivot_in_orig[0] - orig_cx
        dy = pivot_in_orig[1] - orig_cy
        cos_a = math.cos(math.radians(-rot_angle))
        sin_a = math.sin(math.radians(-rot_angle))
        new_dx = dx * cos_a - dy * sin_a
        new_dy = dx * sin_a + dy * cos_a
        pivot_in_rotated = (rw / 2 + new_dx, rh / 2 + new_dy)

        blit_x = shoulder_x - pivot_in_rotated[0]
        blit_y = shoulder_y - pivot_in_rotated[1]
        surface.blit(rotated, (int(blit_x), int(blit_y)))

        # === WING-TIP FEATHER SWAY ===
        # Draw 3-4 individual longer feathers extending from wing bottom
        sway = self._feather_sway
        wing_bottom_x = shoulder_x + int(side * 8 * scale)
        wing_bottom_y = shoulder_y + int(65 * scale)
        feather_colors = [WING_GREEN, WING_TIP_BLUE, WING_TIP_YELLOW, WING_GREEN_LIGHT]
        for fi in range(4):
            f_angle = (1.3 + fi * 0.15 + sway * 0.015) * side
            f_len = int((18 + fi * 5) * scale)
            fx = wing_bottom_x + int(fi * 4 * side * scale)
            fy = wing_bottom_y - int(fi * 8 * scale)
            fex = fx + int(math.cos(f_angle + 1.2) * f_len)
            fey = fy + int(math.sin(f_angle + 1.2) * f_len)
            fw = max(1, int((3 - fi * 0.5) * scale))
            pygame.draw.line(surface, feather_colors[fi % len(feather_colors)],
                             (fx, fy), (fex, fey), fw)

    # === HEAD (big, with hat, eye-patch, earring, beak, eyebrows) ===
    def _draw_head(self, surface: pygame.Surface, x: int, y: int,
                   breath: float, t: float, scale: float = 1.0) -> None:
        b = int(breath)
        hx = x
        hy = y - int(22 * scale) + b + int(self._head_bob_y)
        tilt = self._head_tilt

        HS = 220
        head_surf = self._head_surf
        head_surf.fill((0, 0, 0, 0))
        cx, cy = HS // 2, HS // 2 + 12

        head_r = int(40 * scale)

        # === MAIN HEAD SHAPE (gradient via concentric circles) ===
        for r_frac, color in [
            (1.0, BODY_RED_DARK),
            (0.92, HEAD_RED),
            (0.82, HEAD_LIGHT),
            (0.55, HEAD_LIGHTER),
        ]:
            r = int(head_r * r_frac)
            if r > 0:
                _aa_circle(head_surf, cx - int(2 * r_frac), cy - int(6 * r_frac), r, color)

        # Main head circle on top
        _aa_circle(head_surf, cx, cy, head_r, HEAD_RED)
        # Highlight on forehead
        _aa_circle(head_surf, cx - 6, cy - int(16 * scale), int(20 * scale), HEAD_LIGHT)
        _aa_circle(head_surf, cx - 8, cy - int(20 * scale), int(10 * scale), HEAD_LIGHTER)

        # White cheek patch (macaw bare skin area)
        cheek_rect = (cx - int(36 * scale), cy + int(4 * scale), int(26 * scale), int(20 * scale))
        pygame.draw.ellipse(head_surf, CHEEK_WHITE, cheek_rect)
        pygame.draw.ellipse(head_surf, (225, 218, 210), cheek_rect, width=1)

        # Rim highlight (top-left arc)
        if head_r > 8:
            pygame.draw.arc(head_surf, RIM_GOLD,
                            (cx - head_r + 2, cy - head_r + 2, head_r * 2 - 4, head_r * 2 - 4),
                            1.8, 3.2, 1)

        # Head outline
        pygame.draw.circle(head_surf, BODY_RED_DARK, (cx, cy), head_r, width=2)

        # Green feather tufts at top
        for tuft_i, tuft_off in enumerate([-10, -3, 3, 10]):
            tuft_x = cx + int(tuft_off * scale)
            tuft_y_base = cy - head_r + int(2 * scale)
            tuft_y_tip = tuft_y_base - int((12 + tuft_i % 2 * 5) * scale)
            sway_off = math.sin(t * 2.5 + tuft_i * 0.8) * 2
            pygame.draw.line(head_surf, HEAD_GREEN_TUFT,
                             (tuft_x, tuft_y_base),
                             (int(tuft_x + tuft_off * 0.3 + sway_off), tuft_y_tip), max(2, int(3 * scale)))
            _aa_circle(head_surf, int(tuft_x + tuft_off * 0.3 + sway_off), tuft_y_tip,
                       max(2, int(3 * scale)), HEAD_GREEN_TUFT)

        # === LEFT EYE (visible, BIG and expressive) ===
        e_scale = self._eye_scale
        squint = self._eye_squint
        ex_l, ey_l = cx - int(12 * scale), cy - int(4 * scale)
        ew = int(22 * scale * e_scale)
        eh = int(20 * scale * e_scale * (1.0 - squint * 0.5))  # squint reduces height

        # White of eye
        eye_rect = (ex_l - ew // 2, ey_l - eh // 2, ew, eh)
        pygame.draw.ellipse(head_surf, EYE_WHITE, eye_rect)

        if self._is_blinking or squint > 0.8:
            # Closed/squinted eye — curved arc
            arc_y = ey_l - int(2 * scale)
            arc_w = int(16 * scale * e_scale)
            pygame.draw.arc(head_surf, EYE_OUTLINE,
                            (ex_l - arc_w // 2, arc_y, arc_w, int(10 * scale)),
                            0.3, math.pi - 0.3, max(2, int(3 * scale)))
        else:
            px = ex_l + int(self._pupil_offset_x)
            py = ey_l + int(self._pupil_offset_y)
            iris_r = max(3, int(7 * scale * e_scale))
            pupil_r = max(2, int(4 * scale * e_scale))
            _aa_circle(head_surf, px, py, iris_r, IRIS_GOLD)
            _aa_circle(head_surf, px, py, pupil_r, PUPIL)
            # Catchlights (two: big and small)
            cl_r1 = max(1, int(2.5 * scale * e_scale))
            cl_r2 = max(1, int(1.2 * scale * e_scale))
            _aa_circle(head_surf, px + int(3 * scale), py - int(3 * scale), cl_r1, CATCHLIGHT)
            _aa_circle(head_surf, px - int(1 * scale), py + int(2 * scale), cl_r2, (230, 235, 245))

        pygame.draw.ellipse(head_surf, EYE_OUTLINE, eye_rect, width=2)

        # === EYEBROW FEATHERS ===
        eb_angle = self._eyebrow_angle
        eb_x = ex_l
        eb_y = ey_l - eh // 2 - int(4 * scale)
        eb_len = int(10 * scale)
        rad = math.radians(-eb_angle)
        for eb_off in (-4, 4):
            bx1 = eb_x + int(eb_off * scale)
            by1 = eb_y
            bx2 = bx1 + int(math.cos(rad - 0.3) * eb_len * (1 if eb_off > 0 else -1))
            by2 = by1 + int(math.sin(rad - 0.3) * eb_len)
            pygame.draw.line(head_surf, BODY_RED_DARK, (bx1, by1), (bx2, by2),
                             max(2, int(3 * scale)))

        # === RIGHT EYE — EYE-PATCH ===
        ex_r, ey_r = cx + int(14 * scale), cy - int(4 * scale)
        # Strap across head
        strap_w = max(2, int(3 * scale))
        pygame.draw.line(head_surf, EYEPATCH_STRAP,
                         (cx - int(28 * scale), cy - int(22 * scale)),
                         (ex_r + int(12 * scale), ey_r - int(6 * scale)), strap_w)
        pygame.draw.line(head_surf, EYEPATCH_STRAP,
                         (ex_r + int(12 * scale), ey_r - int(6 * scale)),
                         (ex_r + int(6 * scale), ey_r + int(14 * scale)), strap_w)
        # Patch
        patch_r = int(11 * scale)
        _aa_circle(head_surf, ex_r, ey_r, patch_r, EYEPATCH_BLACK)
        pygame.draw.circle(head_surf, (50, 45, 40), (ex_r, ey_r), patch_r, width=2)
        # Silver skull charm
        skull_r = max(2, int(4 * scale))
        _aa_circle(head_surf, ex_r, ey_r - int(1 * scale), skull_r, SKULL_SILVER)
        for sx_off in (-2, 2):
            _aa_circle(head_surf, ex_r + int(sx_off * scale), ey_r - int(2 * scale),
                       max(1, int(1 * scale)), EYEPATCH_BLACK)
        pygame.draw.line(head_surf, SKULL_SILVER,
                         (ex_r - int(3 * scale), ey_r + int(2 * scale)),
                         (ex_r + int(3 * scale), ey_r + int(2 * scale)), 1)
        # Crossbones
        pygame.draw.line(head_surf, SKULL_SILVER,
                         (ex_r - int(5 * scale), ey_r + int(0 * scale)),
                         (ex_r + int(5 * scale), ey_r + int(5 * scale)), 1)
        pygame.draw.line(head_surf, SKULL_SILVER,
                         (ex_r + int(5 * scale), ey_r + int(0 * scale)),
                         (ex_r - int(5 * scale), ey_r + int(5 * scale)), 1)

        # === BEAK (golden-yellow, large, curved) ===
        beak_open = int(self._beak_open * 10)
        bk_x = cx + int(22 * scale)
        bk_y = cy + int(4 * scale)
        bk_s = scale

        # Upper beak
        upper = [
            (bk_x, bk_y - int(5 * bk_s)),
            (bk_x + int(36 * bk_s), bk_y + int(2 * bk_s)),
            (bk_x + int(32 * bk_s), bk_y + int(12 * bk_s)),
            (bk_x, bk_y + int(7 * bk_s)),
        ]
        pygame.draw.polygon(head_surf, BEAK_GOLD, upper)
        # Highlight on upper beak
        highlight = [
            (bk_x + int(2 * bk_s), bk_y - int(3 * bk_s)),
            (bk_x + int(28 * bk_s), bk_y + int(1 * bk_s)),
            (bk_x + int(24 * bk_s), bk_y + int(6 * bk_s)),
            (bk_x + int(2 * bk_s), bk_y + int(3 * bk_s)),
        ]
        pygame.draw.polygon(head_surf, BEAK_GOLD_LIGHT, highlight)
        # Top rim highlight
        rim_pts = [
            (bk_x + int(2 * bk_s), bk_y - int(4 * bk_s)),
            (bk_x + int(30 * bk_s), bk_y + int(0 * bk_s)),
        ]
        pygame.draw.line(head_surf, BEAK_HIGHLIGHT, rim_pts[0], rim_pts[1],
                         max(1, int(1 * bk_s)))
        pygame.draw.polygon(head_surf, BEAK_GOLD_DARK, upper, width=2)
        # Hook curve at tip
        pygame.draw.arc(head_surf, BEAK_GOLD_DARK,
                        (bk_x + int(26 * bk_s), bk_y, int(14 * bk_s), int(14 * bk_s)),
                        -0.6, 1.2, 2)
        # Nostril
        _aa_circle(head_surf, bk_x + int(14 * bk_s), bk_y + int(1 * bk_s),
                   max(1, int(2 * bk_s)), BEAK_GOLD_DARK)

        # Lower beak
        lower = [
            (bk_x, bk_y + int(9 * bk_s) + beak_open),
            (bk_x + int(26 * bk_s), bk_y + int(13 * bk_s) + beak_open),
            (bk_x, bk_y + int(15 * bk_s) + beak_open),
        ]
        pygame.draw.polygon(head_surf, BEAK_GOLD_DARK, lower)
        pygame.draw.polygon(head_surf, (160, 130, 25), lower, width=1)

        # Mouth interior when open
        if self._beak_open > 0.15:
            mouth = [
                (bk_x + int(2 * bk_s), bk_y + int(7 * bk_s)),
                (bk_x + int(24 * bk_s), bk_y + int(11 * bk_s)),
                (bk_x + int(22 * bk_s), bk_y + int(11 * bk_s) + beak_open),
                (bk_x + int(2 * bk_s), bk_y + int(9 * bk_s) + beak_open),
            ]
            pygame.draw.polygon(head_surf, (160, 55, 65), mouth)
            # Tongue
            tongue_w = int(12 * bk_s)
            tongue_h = int(5 * bk_s)
            pygame.draw.ellipse(head_surf, (200, 90, 100),
                                (bk_x + int(4 * bk_s),
                                 bk_y + int(9 * bk_s) + beak_open // 2,
                                 tongue_w, tongue_h))

        # === EARRING (gold hoop on left side) ===
        ear_x, ear_y = cx - int(30 * scale), cy + int(16 * scale)
        ear_r = max(3, int(5 * scale))
        pygame.draw.circle(head_surf, EARRING_GOLD, (ear_x, ear_y), ear_r, width=max(1, int(2 * scale)))
        _aa_circle(head_surf, ear_x + int(1 * scale), ear_y - int(2 * scale),
                   max(1, int(2 * scale)), (255, 235, 100))

        # === PIRATE HAT (golden tricorne with red feather plume) ===
        hat_y_off = -int(self._hat_bounce)
        hat_cy = cy - int(40 * scale) + hat_y_off
        # Brim (wide ellipse)
        brim_w, brim_h = int(80 * scale), int(14 * scale)
        pygame.draw.ellipse(head_surf, HAT_DARK,
                            (cx - brim_w // 2, hat_cy + int(12 * scale), brim_w, brim_h))
        pygame.draw.ellipse(head_surf, HAT_GOLD,
                            (cx - brim_w // 2 + 2, hat_cy + int(13 * scale),
                             brim_w - 4, brim_h - 2))
        # Brim rim highlight
        pygame.draw.arc(head_surf, HAT_GOLD_LIGHT,
                        (cx - brim_w // 2 + 1, hat_cy + int(12 * scale), brim_w - 2, brim_h),
                        0.2, math.pi - 0.2, 1)
        # Crown (tricorn — upward triangle)
        crown_h = int(24 * scale)
        crown_hw = int(28 * scale)
        crown = [(cx - crown_hw, hat_cy + int(16 * scale)),
                 (cx, hat_cy - crown_h + int(8 * scale)),
                 (cx + crown_hw, hat_cy + int(16 * scale))]
        pygame.draw.polygon(head_surf, HAT_DARK, crown)
        inner_hw = int(22 * scale)
        inner_crown = [(cx - inner_hw, hat_cy + int(14 * scale)),
                       (cx, hat_cy - crown_h + int(12 * scale)),
                       (cx + inner_hw, hat_cy + int(14 * scale))]
        pygame.draw.polygon(head_surf, HAT_GOLD, inner_crown)
        # Crown rim highlight
        pygame.draw.line(head_surf, HAT_GOLD_LIGHT,
                         (cx - inner_hw + 3, hat_cy + int(13 * scale)),
                         (cx, hat_cy - crown_h + int(13 * scale)), 1)
        # Band
        pygame.draw.line(head_surf, HAT_BAND,
                         (cx - int(24 * scale), hat_cy + int(14 * scale)),
                         (cx + int(24 * scale), hat_cy + int(14 * scale)),
                         max(2, int(3 * scale)))
        # Skull emblem
        skull_cx, skull_cy = cx, hat_cy + int(6 * scale)
        _aa_circle(head_surf, skull_cx, skull_cy, max(3, int(5 * scale)), (235, 230, 220))
        _aa_circle(head_surf, skull_cx - int(2 * scale), skull_cy - int(1 * scale),
                   max(1, int(1 * scale)), HAT_DARK)
        _aa_circle(head_surf, skull_cx + int(2 * scale), skull_cy - int(1 * scale),
                   max(1, int(1 * scale)), HAT_DARK)
        pygame.draw.line(head_surf, (210, 205, 195),
                         (skull_cx - int(3 * scale), skull_cy + int(3 * scale)),
                         (skull_cx + int(3 * scale), skull_cy + int(3 * scale)), 1)
        # Crossbones
        cb_s = int(6 * scale)
        pygame.draw.line(head_surf, (210, 205, 195),
                         (skull_cx - cb_s, skull_cy - int(2 * scale)),
                         (skull_cx + cb_s, skull_cy + int(4 * scale)), 1)
        pygame.draw.line(head_surf, (210, 205, 195),
                         (skull_cx + cb_s, skull_cy - int(2 * scale)),
                         (skull_cx - cb_s, skull_cy + int(4 * scale)), 1)

        # === RED FEATHER PLUME (curves upward from right side of hat) ===
        fw = math.sin(t * 4) * 3
        f_base_x = cx + int(18 * scale)
        f_base_y = hat_cy
        f_mid_x = f_base_x + int((12 + fw) * scale)
        f_mid_y = f_base_y - int(18 * scale)
        f_tip_x = f_base_x + int((8 + fw * 1.5) * scale)
        f_tip_y = f_base_y - int(35 * scale)
        # Main plume strokes (multiple for thickness / gradient)
        pygame.draw.line(head_surf, PLUME_RED, (f_base_x, f_base_y), (f_mid_x, f_mid_y),
                         max(2, int(4 * scale)))
        pygame.draw.line(head_surf, PLUME_RED, (f_mid_x, f_mid_y), (f_tip_x, f_tip_y),
                         max(2, int(3 * scale)))
        # Lighter center highlight
        pygame.draw.line(head_surf, PLUME_RED_LIGHT,
                         (f_base_x + 1, f_base_y), (f_mid_x + 1, f_mid_y),
                         max(1, int(2 * scale)))
        pygame.draw.line(head_surf, PLUME_RED_LIGHT,
                         (f_mid_x + 1, f_mid_y), (f_tip_x + 1, f_tip_y),
                         max(1, int(1 * scale)))
        _aa_circle(head_surf, f_tip_x, f_tip_y, max(2, int(3 * scale)), PLUME_RED)
        # Feather barbs
        for fb in range(5):
            bp = 0.15 + fb * 0.2
            bfx = int(f_base_x + (f_tip_x - f_base_x) * bp)
            bfy = int(f_base_y + (f_tip_y - f_base_y) * bp)
            barb_dir = 1 if fb % 2 == 0 else -1
            pygame.draw.line(head_surf, PLUME_RED_LIGHT,
                             (bfx, bfy),
                             (bfx + int((5 + fw * 0.4) * barb_dir), bfy - int(4 * scale)), 1)

        # === EMOTION OVERLAYS ===

        # Surprised: jagged feather ruffle lines around head
        if self.state == STATE_SURPRISED:
            for i in range(7):
                ang = -1.2 + i * 0.4 + math.sin(t * 8) * 0.1
                r_inner = int(head_r * 1.1)
                r_outer = int(head_r * 1.3)
                lx1 = cx + int(math.cos(ang) * r_inner)
                ly1 = cy + int(math.sin(ang) * r_inner)
                # Jagged: alternate short and long
                jag = 8 if i % 2 == 0 else 4
                lx2 = cx + int(math.cos(ang) * (r_outer + jag))
                ly2 = cy + int(math.sin(ang) * (r_outer + jag))
                pygame.draw.line(head_surf, YELLOW, (lx1, ly1), (lx2, ly2), 2)

        # Cheer: golden cross marks orbiting
        if self.state == STATE_CHEER:
            for i in range(5):
                ang = t * 3.5 + i * 1.26
                r_orbit = int(head_r * 1.2)
                sx = cx + int(math.cos(ang) * r_orbit)
                sy = cy + int(math.sin(ang) * r_orbit)
                mark_s = int(5 * scale)
                pygame.draw.line(head_surf, GOLD, (sx - mark_s, sy), (sx + mark_s, sy), 2)
                pygame.draw.line(head_surf, GOLD, (sx, sy - mark_s), (sx, sy + mark_s), 2)

        # Rosy cheeks for laugh & cheer
        if self.state == STATE_LAUGH:
            _aa_circle(head_surf, cx - int(24 * scale), cy + int(12 * scale),
                       int(6 * scale), (255, 140, 120))
        if self.state == STATE_CHEER:
            _aa_circle(head_surf, cx - int(24 * scale), cy + int(12 * scale),
                       int(5 * scale), (255, 160, 140))

        # Rotate head by tilt and blit
        if abs(tilt) > 0.5:
            rotated_head = pygame.transform.rotate(head_surf, tilt)
        else:
            rotated_head = head_surf
        rr = rotated_head.get_rect(center=(hx, hy))
        surface.blit(rotated_head, rr)

    # === PARTICLES ===
    def _draw_particles(self, surface: pygame.Surface) -> None:
        for p in self._particles:
            p.draw(surface)

    # === SPEECH BUBBLE ===
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

        # Monkey Island style oval bubble
        pygame.draw.ellipse(surface, WHITE, bubble_rect.inflate(8, 8))
        pygame.draw.ellipse(surface, BLACK, bubble_rect.inflate(8, 8), width=3)
        pygame.draw.ellipse(surface, WHITE, bubble_rect)

        # Tail points toward Virgil
        tail_target_x = int(x - 8) if bubble_left else int(x + 16)
        tail_target_y = int(y - 22) if bubble_above else int(y + 8)
        tail_left = max(bubble_rect.left + 18, min(bubble_rect.right - 18, tail_target_x - 10))
        tail_right = max(bubble_rect.left + 18, min(bubble_rect.right - 18, tail_target_x + 10))
        if bubble_above:
            tail_y = bubble_rect.bottom
            tail_pts = [(tail_left, tail_y - 4), (tail_target_x, tail_target_y),
                        (tail_right, tail_y - 4)]
        else:
            tail_y = bubble_rect.top
            tail_pts = [(tail_left, tail_y + 4), (tail_target_x, tail_target_y),
                        (tail_right, tail_y + 4)]
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

    # === PARTICLE SPAWNERS ===

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
        feather_colors = [BODY_RED, WING_GREEN, TAIL_BLUE, TAIL_YELLOW, HEAD_RED, PLUME_RED]
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
    "Ha! I've seen treasure maps harder to read than THAT password! Spice it up!",
    "Sweet salty seahorses! That's the code to me birdseed jar, not a TREASURE chest!",
    "SQUAWK! Even Davy Jones' locker has a better combination -- and he's DEAD!",
    "Thundering typhoons! A monkey with a keyboard could type that by ACCIDENT!",
    "Flapping flounders! That password is so short, it fits on a grain of sand!",
    "Avast! Me eye-patch has more complexity than that! Throw in some chaos, matey!",
    "Virgil wants a STRONGER password! Mix letters, numbers, AND symbols -- SQUAWK!",
]
