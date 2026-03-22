# === SCROLL PANEL ===
# The Ancient Pirate Scroll — a beautiful fixed bottom panel that displays
# EVERY text message in the game. Inspired by classic LucasArts adventure
# game text areas (Monkey Island, Day of the Tentacle).
#
# Drop-in class: call .update(dt) and .draw(surface, t) each frame.
# Route text with .show_message(text, style, duration, important).
#
# EASY TO CHANGE PARCHMENT COLORS — all defined as constants below.

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from .constants import BLACK, FONT_NAME, GOLD, HEIGHT, WHITE, WIDTH, YELLOW

# === PARCHMENT COLORS (EASY TO CHANGE) ===
PARCHMENT_BASE = (226, 198, 141)
PARCHMENT_LIGHT = (238, 218, 172)
PARCHMENT_DARK = (195, 165, 110)
PARCHMENT_GRAIN_A = (198, 168, 120)
PARCHMENT_GRAIN_B = (182, 145, 91)
GOLD_BORDER_OUTER = (210, 165, 60)
GOLD_BORDER_INNER = (180, 140, 50)
GOLD_BRIGHT = (245, 210, 60)
GOLD_CORNER = (230, 190, 55)
INK_BROWN = (70, 45, 22)
INK_SHADOW = (40, 25, 12)
GRID_LINE_COLOR = (205, 180, 130)
CURL_SHADOW = (160, 130, 85)
TEAR_EDGE = (190, 160, 110)

# === SCROLL DIMENSIONS (EASY TO CHANGE) ===
SCROLL_WIDTH = WIDTH  # 900
SCROLL_HEIGHT = 150
SCROLL_Y = HEIGHT - SCROLL_HEIGHT  # 450
SCROLL_X = 0
SCROLL_PAD_X = 40  # text padding from edges
SCROLL_PAD_Y = 16
SCROLL_TEXT_WIDTH = SCROLL_WIDTH - SCROLL_PAD_X * 2 - 30  # usable text width

# === ANIMATION TIMING (EASY TO CHANGE) ===
FADE_IN_DURATION = 0.4  # seconds for ink fade-in
AUTO_CLEAR_DURATION = 8.0  # default seconds before auto-clear
UNROLL_DURATION = 0.3  # scroll unroll ease-out
SPARKLE_COUNT = 10  # gold sparkles on important messages
SPARKLE_LIFETIME = 2.0
MAX_MESSAGES = 3
MAX_LINES_PER_MESSAGE = 4
ICON_PULSE_SPEED = 3.0

# === TEXT STYLE COLORS ===
STYLE_COLORS = {
    "dialogue": INK_BROWN,
    "teaching": (30, 100, 40),
    "warning": (180, 40, 40),
    "success": (180, 145, 30),
    "hint": (40, 120, 160),
}

STYLE_OUTLINE = {
    "dialogue": (255, 235, 180),
    "teaching": (200, 255, 210),
    "warning": (255, 200, 200),
    "success": (255, 240, 180),
    "hint": (200, 235, 255),
}

STYLE_PREFIX = {
    "teaching": ">> ",
    "warning": "!! ",
    "success": "** ",
    "hint": "~~ ",
}


# === SPARKLE PARTICLE ===
@dataclass
class _ScrollSparkle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: tuple

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0

    def draw(self, surface: pygame.Surface) -> None:
        alpha = max(0.0, self.life / self.max_life)
        r = max(1, int(self.size * alpha))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), r)


# === SCROLL MESSAGE ===
@dataclass
class _ScrollMessage:
    text: str
    style: str = "dialogue"
    duration: float = AUTO_CLEAR_DURATION
    important: bool = False
    age: float = 0.0
    alpha: float = 0.0  # ramps 0→255 during fade-in
    _wrapped_lines: list[str] = field(default_factory=list)
    _line_surfaces: list[tuple[pygame.Surface, pygame.Surface]] | None = None


# === SCROLL PANEL CLASS ===
class ScrollPanel:
    """The Ancient Pirate Scroll — single source of truth for all game text."""

    def __init__(self) -> None:
        # Messages queue (newest first)
        self._messages: list[_ScrollMessage] = []

        # Font for scroll text (28px bold, accessible)
        self._font = pygame.font.SysFont(FONT_NAME, 28, bold=True)
        self._small_font = pygame.font.SysFont(FONT_NAME, 22, bold=True)

        # Cached parchment background (static elements pre-rendered)
        self._bg_cache: pygame.Surface | None = None
        self._build_bg_cache()

        # Sparkle particles
        self._sparkles: list[_ScrollSparkle] = []

        # Scroll unroll animation
        self._unroll_progress = 1.0  # 0 = rolled up, 1 = fully open
        self._unroll_target = 1.0

        # Icon pulse timer
        self._icon_pulse = 0.0
        self._icon_active = False

        # Text surface cache
        self._text_cache: dict[tuple[str, tuple], pygame.Surface] = {}

        # Tear edge points (pre-computed for the torn top edge)
        self._tear_points = self._generate_tear_points()

    # === PUBLIC API ===

    def show_message(self, text: str, style: str = "dialogue",
                     duration: float = AUTO_CLEAR_DURATION,
                     important: bool = False) -> None:
        """Add a message to the scroll."""
        if not text or not text.strip():
            return

        # Don't add duplicate of the current top message
        if self._messages and self._messages[0].text == text and self._messages[0].style == style:
            # Reset its timer instead
            self._messages[0].age = 0.0
            self._messages[0].duration = duration
            return

        prefix = STYLE_PREFIX.get(style, "")
        msg = _ScrollMessage(
            text=prefix + text,
            style=style,
            duration=duration,
            important=important,
            age=0.0,
            alpha=0.0,
        )
        msg._wrapped_lines = self._wrap_text(msg.text)

        # Insert at front (newest first)
        self._messages.insert(0, msg)

        # Trim to max
        while len(self._messages) > MAX_MESSAGES:
            self._messages.pop()

        # Trigger icon pulse
        self._icon_active = True
        self._icon_pulse = 0.0

        # Spawn sparkles for important messages
        if important:
            self._spawn_sparkles()

    def clear(self) -> None:
        """Clear all messages."""
        self._messages.clear()
        self._sparkles.clear()

    def update(self, dt: float) -> None:
        """Update animations, timers, auto-clear."""
        # Update messages
        expired = []
        for i, msg in enumerate(self._messages):
            msg.age += dt
            # Fade-in
            if msg.alpha < 255:
                msg.alpha = min(255.0, msg.alpha + (255.0 / FADE_IN_DURATION) * dt)
            # Auto-clear check
            if msg.age >= msg.duration:
                expired.append(i)

        # Remove expired (iterate in reverse to preserve indices)
        for i in reversed(expired):
            if i < len(self._messages):
                self._messages.pop(i)

        # Update sparkles
        self._sparkles = [s for s in self._sparkles if s.update(dt)]

        # Update icon pulse
        if self._icon_active:
            self._icon_pulse += dt * ICON_PULSE_SPEED
            if self._icon_pulse > math.pi * 4:
                self._icon_active = False

        # Unroll animation
        if self._unroll_progress < self._unroll_target:
            self._unroll_progress = min(self._unroll_target,
                                        self._unroll_progress + dt / UNROLL_DURATION)

    def draw(self, surface: pygame.Surface, t: float) -> None:
        """Draw the scroll panel at screen bottom."""
        # Draw cached parchment background
        if self._bg_cache is not None:
            surface.blit(self._bg_cache, (SCROLL_X, SCROLL_Y))

        # Draw animated parchment curl on top edge
        self._draw_torn_top_edge(surface, t)

        # Draw gold corner flourishes (animated subtle glow)
        self._draw_corner_flourishes(surface, t)

        # Draw messages (newest at top)
        self._draw_messages(surface, t)

        # Draw sparkle particles
        for sparkle in self._sparkles:
            sparkle.draw(surface)

        # Draw scroll icon (top-right corner)
        self._draw_scroll_icon(surface, t)

    @property
    def has_messages(self) -> bool:
        """True if any visible messages."""
        return len(self._messages) > 0

    # === BACKGROUND CACHE ===

    def _build_bg_cache(self) -> None:
        """Pre-render all static parchment elements to a cached surface."""
        cache = pygame.Surface((SCROLL_WIDTH, SCROLL_HEIGHT), pygame.SRCALPHA)

        # Parchment base fill
        pygame.draw.rect(cache, PARCHMENT_BASE, (0, 8, SCROLL_WIDTH, SCROLL_HEIGHT - 8),
                         border_radius=6)

        # Subtle vertical gradient (lighter at top, darker at bottom)
        for y in range(10, SCROLL_HEIGHT):
            p = (y - 10) / max(1, SCROLL_HEIGHT - 10)
            r = int(PARCHMENT_LIGHT[0] * (1 - p) + PARCHMENT_DARK[0] * p)
            g = int(PARCHMENT_LIGHT[1] * (1 - p) + PARCHMENT_DARK[1] * p)
            b = int(PARCHMENT_LIGHT[2] * (1 - p) + PARCHMENT_DARK[2] * p)
            pygame.draw.line(cache, (r, g, b), (4, y), (SCROLL_WIDTH - 4, y))

        # Faint map-grid lines
        for gx in range(30, SCROLL_WIDTH, 42):
            pygame.draw.line(cache, (*GRID_LINE_COLOR, 50),
                             (gx, 14), (gx, SCROLL_HEIGHT - 6), 1)
        for gy in range(20, SCROLL_HEIGHT, 38):
            pygame.draw.line(cache, (*GRID_LINE_COLOR, 50),
                             (8, gy), (SCROLL_WIDTH - 8, gy), 1)

        # Parchment grain (noise dots and stain ellipses)
        for i in range(80):
            px = (i * 67 + 43) % (SCROLL_WIDTH - 16) + 8
            py = (i * 41 + 29) % (SCROLL_HEIGHT - 20) + 12
            r = 1 + (i % 2)
            shade = 198 + (i % 19)
            pygame.draw.circle(cache, (shade, shade - 18, shade - 42), (px, py), r)

        for i in range(18):
            cx = (i * 113 + 79) % (SCROLL_WIDTH - 40) + 20
            cy = (i * 89 + 37) % (SCROLL_HEIGHT - 24) + 14
            w = 20 + (i % 4) * 6
            h = 8 + (i % 5) * 3
            pygame.draw.ellipse(cache, (*PARCHMENT_GRAIN_B, 35), (cx, cy, w, h), width=1)

        # Scroll curl shadows (left and right edges)
        curl_width = 22
        for x in range(curl_width):
            p = x / curl_width
            alpha = int(65 * (1 - p))
            # Left curl
            pygame.draw.line(cache, (*CURL_SHADOW, alpha),
                             (x + 2, 12), (x + 2, SCROLL_HEIGHT - 4), 1)
            # Right curl
            pygame.draw.line(cache, (*CURL_SHADOW, alpha),
                             (SCROLL_WIDTH - x - 3, 12),
                             (SCROLL_WIDTH - x - 3, SCROLL_HEIGHT - 4), 1)

        # Gold ornate border — outer
        border_rect = pygame.Rect(2, 10, SCROLL_WIDTH - 4, SCROLL_HEIGHT - 12)
        pygame.draw.rect(cache, GOLD_BORDER_OUTER, border_rect, width=4, border_radius=8)
        # Gold ornate border — inner
        inner_rect = border_rect.inflate(-12, -12)
        pygame.draw.rect(cache, GOLD_BORDER_INNER, inner_rect, width=2, border_radius=6)

        self._bg_cache = cache

    # === TORN TOP EDGE ===

    def _generate_tear_points(self) -> list[tuple[int, int]]:
        """Pre-compute the irregular torn edge along the top of the scroll."""
        points = []
        random.seed(42)  # deterministic tears
        x = 0
        while x < SCROLL_WIDTH:
            tear_y = random.randint(-3, 5)
            points.append((x, tear_y))
            x += random.randint(8, 18)
        points.append((SCROLL_WIDTH, 0))
        random.seed()  # re-randomize
        return points

    def _draw_torn_top_edge(self, surface: pygame.Surface, t: float) -> None:
        """Draw the animated torn parchment edge along the top of the scroll."""
        # Sine-wave curl animation on the top edge
        curl_phase = t * 1.5
        points = []
        for bx, base_tear in self._tear_points:
            curl = math.sin(curl_phase + bx * 0.032) * 2.5
            sy = SCROLL_Y + 8 + base_tear + int(curl)
            points.append((bx, sy))

        # Close the polygon to cover the top edge area
        if len(points) >= 2:
            # Add bottom corners to fill
            closed = [(0, SCROLL_Y + 14)] + points + [(SCROLL_WIDTH, SCROLL_Y + 14)]
            pygame.draw.polygon(surface, PARCHMENT_BASE, closed)

            # Draw the torn edge line itself
            pygame.draw.lines(surface, TEAR_EDGE, False, points, 2)

            # Subtle shadow below the torn edge
            shadow_points = [(px, py + 2) for px, py in points]
            pygame.draw.lines(surface, (*CURL_SHADOW, 80), False, shadow_points, 1)

    # === CORNER FLOURISHES ===

    def _draw_corner_flourishes(self, surface: pygame.Surface, t: float) -> None:
        """Draw ornate gold corner decorations with subtle glow."""
        glow = int(200 + 55 * math.sin(t * 2.0))
        col = (min(255, glow), min(255, int(glow * 0.82)), min(255, int(glow * 0.25)))

        corners = [
            (SCROLL_X + 12, SCROLL_Y + 18),      # top-left
            (SCROLL_X + SCROLL_WIDTH - 12, SCROLL_Y + 18),  # top-right
            (SCROLL_X + 12, SCROLL_Y + SCROLL_HEIGHT - 10),  # bottom-left
            (SCROLL_X + SCROLL_WIDTH - 12, SCROLL_Y + SCROLL_HEIGHT - 10),  # bottom-right
        ]

        for cx, cy in corners:
            # Diamond shape
            size = 6
            diamond = [(cx, cy - size), (cx + size, cy),
                       (cx, cy + size), (cx - size, cy)]
            pygame.draw.polygon(surface, col, diamond)
            pygame.draw.polygon(surface, GOLD_BORDER_OUTER, diamond, width=1)

            # Small radiating lines
            for angle_off in (-0.8, -0.4, 0.4, 0.8):
                lx = cx + int(math.cos(angle_off) * 10)
                ly = cy + int(math.sin(angle_off) * 10)
                pygame.draw.line(surface, (*GOLD_BORDER_INNER, 140),
                                 (cx, cy), (lx, ly), 1)

    # === TEXT RENDERING ===

    def _wrap_text(self, text: str) -> list[str]:
        """Word-wrap text to fit the scroll panel width."""
        words = text.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if self._font.size(test)[0] <= SCROLL_TEXT_WIDTH:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines[:MAX_LINES_PER_MESSAGE]

    def _render_text_line(self, text: str, color: tuple,
                          outline_color: tuple) -> pygame.Surface:
        """Render a text line with outline/shadow, using cache."""
        key = (text, color, outline_color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached

        base = self._font.render(text, True, color)
        outline_surf = self._font.render(text, True, outline_color)
        result = pygame.Surface(
            (base.get_width() + 4, base.get_height() + 4), pygame.SRCALPHA
        )
        # Shadow/outline offsets
        for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1)]:
            result.blit(outline_surf, (ox + 2, oy + 2))
        result.blit(base, (2, 2))

        self._text_cache[key] = result
        if len(self._text_cache) > 512:
            self._text_cache.clear()
            self._text_cache[key] = result
        return result

    def _draw_messages(self, surface: pygame.Surface, t: float) -> None:
        """Draw all queued messages in the scroll area."""
        if not self._messages:
            # Show idle text when no messages
            idle_surf = self._render_text_line(
                "~ The Ancient Pirate Scroll awaits your adventure... ~",
                (*PARCHMENT_GRAIN_B, 120), (*PARCHMENT_DARK, 60)
            )
            idle_rect = idle_surf.get_rect(
                center=(SCROLL_X + SCROLL_WIDTH // 2, SCROLL_Y + SCROLL_HEIGHT // 2 + 4)
            )
            surface.blit(idle_surf, idle_rect)
            return

        # Draw messages — newest at top
        y_cursor = SCROLL_Y + SCROLL_PAD_Y + 6
        line_h = self._font.get_height() + 4

        for msg_idx, msg in enumerate(self._messages):
            if y_cursor >= SCROLL_Y + SCROLL_HEIGHT - 10:
                break

            style = msg.style
            color = STYLE_COLORS.get(style, INK_BROWN)
            outline = STYLE_OUTLINE.get(style, (255, 235, 180))

            # Apply alpha for fade-in and age-based fade for older messages
            msg_alpha = min(255, int(msg.alpha))
            if msg_idx > 0:
                # Older messages fade slightly
                age_fade = max(100, 255 - msg_idx * 50)
                msg_alpha = min(msg_alpha, age_fade)

            for line_text in msg._wrapped_lines:
                if y_cursor >= SCROLL_Y + SCROLL_HEIGHT - 10:
                    break

                line_surf = self._render_text_line(line_text, color, outline)

                if msg_alpha < 255:
                    # Apply alpha via a temporary surface
                    alpha_surf = line_surf.copy()
                    alpha_surf.set_alpha(msg_alpha)
                    surface.blit(alpha_surf, (SCROLL_X + SCROLL_PAD_X, y_cursor))
                else:
                    surface.blit(line_surf, (SCROLL_X + SCROLL_PAD_X, y_cursor))

                y_cursor += line_h

            # Small gap between messages
            y_cursor += 4

    # === SPARKLES ===

    def _spawn_sparkles(self) -> None:
        """Spawn gold sparkle particles across the scroll surface."""
        for _ in range(SPARKLE_COUNT):
            self._sparkles.append(_ScrollSparkle(
                x=random.uniform(SCROLL_X + 30, SCROLL_X + SCROLL_WIDTH - 30),
                y=random.uniform(SCROLL_Y + 20, SCROLL_Y + SCROLL_HEIGHT - 20),
                vx=random.uniform(-15, 15),
                vy=random.uniform(-20, -5),
                life=random.uniform(1.0, SPARKLE_LIFETIME),
                max_life=SPARKLE_LIFETIME,
                size=random.uniform(2, 4),
                color=random.choice([GOLD_BRIGHT, GOLD_CORNER, YELLOW,
                                     (255, 230, 140), WHITE]),
            ))

    # === SCROLL ICON ===

    def _draw_scroll_icon(self, surface: pygame.Surface, t: float) -> None:
        """Draw a small rolled-parchment icon in the top-right corner."""
        ix = SCROLL_X + SCROLL_WIDTH - 32
        iy = SCROLL_Y + 16

        # Pulse when new message arrives
        alpha = 180
        if self._icon_active:
            pulse = abs(math.sin(self._icon_pulse))
            alpha = int(180 + 75 * pulse)

        col = (*PARCHMENT_DARK, min(255, alpha))

        # Small rolled parchment shape
        icon_surf = pygame.Surface((20, 24), pygame.SRCALPHA)
        # Roll body
        pygame.draw.rect(icon_surf, col, (3, 2, 14, 18), border_radius=3)
        pygame.draw.rect(icon_surf, (*GOLD_BORDER_OUTER, min(255, alpha)),
                         (3, 2, 14, 18), width=1, border_radius=3)
        # Roll ends (circles at top and bottom)
        pygame.draw.ellipse(icon_surf, col, (2, 0, 16, 6))
        pygame.draw.ellipse(icon_surf, col, (2, 16, 16, 6))
        pygame.draw.ellipse(icon_surf, (*GOLD_BORDER_OUTER, min(255, alpha)),
                            (2, 0, 16, 6), width=1)
        # Small lines to suggest text
        for ly in (7, 11, 15):
            pygame.draw.line(icon_surf, (*INK_BROWN, min(255, alpha - 40)),
                             (6, ly), (14, ly), 1)

        surface.blit(icon_surf, (ix, iy))
