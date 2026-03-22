"""Manager classes: save, audio, and sprites."""

from __future__ import annotations

import json
import math
import os
import shutil
import time
from array import array
from dataclasses import dataclass
from pathlib import Path

import pygame

from .constants import (
    BLACK,
    DIFFICULTY_ORDER,
    GREEN,
    MIXER_BUFFER,
    MIXER_CHANNELS,
    MIXER_FREQUENCY,
    MIXER_SIZE,
    SAVE_FILE,
    SAVE_SCHEMA_VERSION,
    WHITE,
)
from .visuals import draw_chest_fallback, draw_parrot_fallback


@dataclass
class Animation:
    frames: list[pygame.Surface]
    fps: float

    def frame_at(self, t):
        if not self.frames:
            return None
        idx = int(t * self.fps) % len(self.frames)
        return self.frames[idx]


class SaveManager:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.path = self.root_dir / SAVE_FILE
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        self.data = self._load_or_create()

    def _default_data(self):
        return {
            "version": SAVE_SCHEMA_VERSION,
            "profile": "default",
            "sessions": 0,
            "total_time_seconds": 0.0,
            "settings": {
                "mute": False,
                "music_volume": 0.65,
                "sfx_volume": 0.85,
                "fullscreen": False,
            },
            "stats": {
                "rounds_played": {diff: 0 for diff in DIFFICULTY_ORDER},
                "rounds_won": {diff: 0 for diff in DIFFICULTY_ORDER},
                "total_hints": 0,
                "total_attempts": 0,
                "best_builder_strength": 0,
                "builder_80_count": 0,
                "builder_100_count": 0,
                "total_stars": 0,
                "stickers_unlocked": [],
                "last_reward": "",
                "round_results": [],
            },
        }

    def _load_or_create(self):
        if not self.path.exists():
            data = self._default_data()
            self._atomic_save(data)
            return data

        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            stamp = int(time.time())
            backup = self.path.with_suffix(f".corrupt.{stamp}.json")
            try:
                shutil.copy2(self.path, backup)
            except OSError:
                pass
            data = self._default_data()
            self._atomic_save(data)
            return data

        data = self._migrate(raw)
        self._atomic_save(data)
        return data

    def _migrate(self, raw):
        data = self._default_data()
        if not isinstance(raw, dict):
            return data

        settings = raw.get("settings", {})
        stats = raw.get("stats", {})

        data["version"] = SAVE_SCHEMA_VERSION
        data["profile"] = str(raw.get("profile", "default"))
        data["sessions"] = int(raw.get("sessions", 0))
        data["total_time_seconds"] = float(raw.get("total_time_seconds", 0.0))

        data["settings"]["mute"] = bool(settings.get("mute", data["settings"]["mute"]))
        data["settings"]["music_volume"] = self._clamp01(float(settings.get("music_volume", data["settings"]["music_volume"])))
        data["settings"]["sfx_volume"] = self._clamp01(float(settings.get("sfx_volume", data["settings"]["sfx_volume"])))
        data["settings"]["fullscreen"] = bool(settings.get("fullscreen", data["settings"]["fullscreen"]))

        for diff in DIFFICULTY_ORDER:
            data["stats"]["rounds_played"][diff] = int(stats.get("rounds_played", {}).get(diff, 0))
            data["stats"]["rounds_won"][diff] = int(stats.get("rounds_won", {}).get(diff, 0))

        data["stats"]["total_hints"] = int(stats.get("total_hints", 0))
        data["stats"]["total_attempts"] = int(stats.get("total_attempts", 0))
        data["stats"]["best_builder_strength"] = int(stats.get("best_builder_strength", 0))
        data["stats"]["builder_80_count"] = int(stats.get("builder_80_count", 0))
        data["stats"]["builder_100_count"] = int(stats.get("builder_100_count", 0))
        data["stats"]["total_stars"] = int(stats.get("total_stars", 0))

        stickers = stats.get("stickers_unlocked", [])
        if isinstance(stickers, list):
            data["stats"]["stickers_unlocked"] = [str(s) for s in stickers][:50]

        data["stats"]["last_reward"] = str(stats.get("last_reward", ""))

        rounds = stats.get("round_results", [])
        if isinstance(rounds, list):
            cleaned = []
            for item in rounds[-200:]:
                if isinstance(item, dict):
                    cleaned.append(item)
            data["stats"]["round_results"] = cleaned

        return data

    def _atomic_save(self, data):
        try:
            tmp = self.path.with_suffix(".tmp")
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass

    @staticmethod
    def _clamp01(value):
        return max(0.0, min(1.0, value))

    def save(self):
        self._atomic_save(self.data)

    def increment_session(self):
        self.data["sessions"] += 1
        self.save()

    def add_session_time(self, dt):
        self.data["total_time_seconds"] += max(0.0, dt)

    @property
    def settings(self):
        return self.data["settings"]

    @property
    def stats(self):
        return self.data["stats"]

    def set_settings(
        self,
        mute: bool | None = None,
        music_volume: float | None = None,
        sfx_volume: float | None = None,
        fullscreen: bool | None = None,
    ):
        if mute is not None:
            self.settings["mute"] = bool(mute)
        if music_volume is not None:
            self.settings["music_volume"] = self._clamp01(float(music_volume))
        if sfx_volume is not None:
            self.settings["sfx_volume"] = self._clamp01(float(sfx_volume))
        if fullscreen is not None:
            self.settings["fullscreen"] = bool(fullscreen)
        self.save()

    def record_builder_strength(self, strength: int):
        strength = int(max(0, min(100, strength)))
        self.stats["best_builder_strength"] = max(self.stats["best_builder_strength"], strength)
        if strength >= 80:
            self.stats["builder_80_count"] += 1
        if strength >= 100:
            self.stats["builder_100_count"] += 1
            self._unlock_sticker("Strong Password Pro")
            if self.stats["builder_100_count"] >= 5:
                self._unlock_sticker("Security Legend")
        self.save()

    def compute_stars(self, attempts, hints_used, solve_seconds):
        stars = 3
        if attempts > 6:
            stars -= 1
        if hints_used > 0:
            stars -= 1
        if solve_seconds > 90:
            stars -= 1
        return max(1, stars)

    def record_round(self, result: dict):
        difficulty = result.get("difficulty", "easy")
        played_map = self.stats["rounds_played"]
        won_map = self.stats["rounds_won"]

        if difficulty in played_map:
            played_map[difficulty] += 1
        solved = bool(result.get("solved", False))
        if solved and difficulty in won_map:
            won_map[difficulty] += 1

        attempts = int(result.get("attempts", 0))
        hints_used = int(result.get("hints_used", 0))
        solve_seconds = float(result.get("solve_seconds", 0.0))

        self.stats["total_attempts"] += attempts
        self.stats["total_hints"] += hints_used

        stars = int(result.get("stars_awarded", 0))
        if solved and stars <= 0:
            stars = self.compute_stars(attempts, hints_used, solve_seconds)
        result["stars_awarded"] = stars

        self.stats["total_stars"] += stars
        self.stats["round_results"].append(result)
        self.stats["round_results"] = self.stats["round_results"][-200:]

        if solved:
            self._unlock_sticker("First Treasure")
            if difficulty == "hard":
                self._unlock_sticker("Hard Mode Hero")
            if attempts <= 3 and hints_used == 0:
                self._unlock_sticker("Swift Captain")
            if self.stats["total_stars"] >= 20:
                self._unlock_sticker("Star Collector")

        self.save()

    def _unlock_sticker(self, name):
        stickers = self.stats["stickers_unlocked"]
        if name not in stickers:
            stickers.append(name)
            self.stats["last_reward"] = name

    def clear_progress_keep_settings(self):
        settings = dict(self.settings)
        fresh = self._default_data()
        fresh["settings"] = settings
        fresh["sessions"] = self.data.get("sessions", 0)
        fresh["total_time_seconds"] = self.data.get("total_time_seconds", 0.0)
        self.data = fresh
        self.save()

    def parent_summary(self):
        rounds = self.stats["round_results"]
        by_diff = {diff: [] for diff in DIFFICULTY_ORDER}
        solved_rounds = []
        hint_total = 0

        for row in rounds:
            diff = row.get("difficulty", "easy")
            attempts = int(row.get("attempts", 0))
            hints = int(row.get("hints_used", 0))
            hint_total += hints
            if diff in by_diff:
                by_diff[diff].append(attempts)
            if row.get("solved"):
                solved_rounds.append(row)

        avg_attempts = {}
        for diff, values in by_diff.items():
            if values:
                avg_attempts[diff] = sum(values) / len(values)
            else:
                avg_attempts[diff] = 0.0

        hint_rate = 0.0
        if rounds:
            hint_rate = hint_total / len(rounds)

        return {
            "sessions": self.data["sessions"],
            "total_time_seconds": self.data["total_time_seconds"],
            "avg_attempts": avg_attempts,
            "hint_rate": hint_rate,
            "builder_80_count": self.stats["builder_80_count"],
            "builder_100_count": self.stats["builder_100_count"],
            "recent_rounds": rounds[-8:][::-1],
        }


class AudioManager:
    def __init__(self, root_dir: str | Path, settings: dict):
        self.root_dir = Path(root_dir)
        self.available = False
        self.muted = bool(settings.get("mute", False))
        self.music_volume = float(settings.get("music_volume", 0.6))
        self.sfx_volume = float(settings.get("sfx_volume", 0.8))
        self._sfx_turn = 0

        self.sfx: dict[str, pygame.mixer.Sound] = {}
        self.music_track: pygame.mixer.Sound | None = None
        self.music_channel = None
        self.sfx_channels = []

        self._init_mixer()
        self._load_assets()
        self._apply_volume()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=MIXER_FREQUENCY,
                    size=MIXER_SIZE,
                    channels=MIXER_CHANNELS,
                    buffer=MIXER_BUFFER,
                )
            self.available = True
            self.music_channel = pygame.mixer.Channel(0)
            self.sfx_channels = [pygame.mixer.Channel(i) for i in range(1, 8)]
        except pygame.error:
            self.available = False

    def _load_assets(self):
        if not self.available:
            return

        # Real files are preferred; generated tones are fallback.
        self.sfx["click"] = self._load_or_tone("assets/audio/sfx/click.wav", 640, 0.05)
        self.sfx["dial"] = self._load_or_tone("assets/audio/sfx/dial.wav", 520, 0.06)
        self.sfx["clunk"] = self._load_or_tone("assets/audio/sfx/clunk.wav", 180, 0.18)
        self.sfx["success"] = self._load_or_tone("assets/audio/sfx/success.wav", 900, 0.25)
        self.sfx["confetti"] = self._load_or_tone("assets/audio/sfx/confetti.wav", 760, 0.16)
        self.sfx["reward"] = self._load_or_tone("assets/audio/sfx/reward.wav", 990, 0.22)
        self.sfx["coins_clink"] = self._load_or_custom("assets/audio/sfx/coins_clink.wav", self._coin_clink)

        music_path = self.root_dir / "assets/audio/music/island_loop.wav"
        if music_path.exists():
            try:
                self.music_track = pygame.mixer.Sound(str(music_path))
            except pygame.error:
                self.music_track = self._tone(196, 1.8, amplitude=0.08)
        else:
            self.music_track = self._tone(196, 1.8, amplitude=0.08)

    def _load_or_tone(self, rel_path, freq, dur):
        path = self.root_dir / rel_path
        if path.exists():
            try:
                return pygame.mixer.Sound(str(path))
            except pygame.error:
                pass
        return self._tone(freq, dur)

    def _load_or_custom(self, rel_path, generator):
        path = self.root_dir / rel_path
        if path.exists():
            try:
                return pygame.mixer.Sound(str(path))
            except pygame.error:
                pass
        return generator()

    def _tone(self, freq, dur, amplitude=0.18):
        samples = int(MIXER_FREQUENCY * dur)
        buf = array("h")
        for i in range(samples):
            env = 1.0 - (i / max(1, samples))
            wave = math.sin(2 * math.pi * freq * i / MIXER_FREQUENCY)
            value = int(32767 * amplitude * env * wave)
            buf.append(value)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _coin_clink(self):
        dur = 0.34
        samples = int(MIXER_FREQUENCY * dur)
        buf = array("h")
        for i in range(samples):
            t = i / MIXER_FREQUENCY
            env = (1.0 - (i / max(1, samples))) ** 2.1
            body = (
                math.sin(2 * math.pi * 1320 * t)
                + 0.68 * math.sin(2 * math.pi * 1870 * t + 0.9)
                + 0.42 * math.sin(2 * math.pi * 2640 * t + 0.3)
            )
            transient = 0.0
            if t < 0.03:
                transient = math.sin(2 * math.pi * 3250 * t) * (1.0 - (t / 0.03))
            value = int(32767 * 0.12 * (env * body + transient * 0.55))
            value = max(-32767, min(32767, value))
            buf.append(value)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def _apply_volume(self):
        if not self.available:
            return

        music_vol = 0.0 if self.muted else self.music_volume
        sfx_vol = 0.0 if self.muted else self.sfx_volume

        if self.music_channel is not None:
            self.music_channel.set_volume(music_vol)

        for sound in self.sfx.values():
            sound.set_volume(sfx_vol)

        for channel in self.sfx_channels:
            channel.set_volume(sfx_vol)

    def play_music(self):
        if not self.available or self.music_track is None or self.music_channel is None:
            return
        if not self.music_channel.get_busy():
            self.music_channel.play(self.music_track, loops=-1)

    def stop_music(self):
        if self.available and self.music_channel is not None:
            self.music_channel.stop()

    def play_sfx(self, name):
        if not self.available:
            return
        sound = self.sfx.get(name)
        if sound is None:
            return
        if not self.sfx_channels:
            sound.play()
            return
        channel = self.sfx_channels[self._sfx_turn % len(self.sfx_channels)]
        self._sfx_turn += 1
        channel.play(sound)

    def set_music_volume(self, value):
        self.music_volume = max(0.0, min(1.0, float(value)))
        self._apply_volume()

    def set_sfx_volume(self, value):
        self.sfx_volume = max(0.0, min(1.0, float(value)))
        self._apply_volume()

    def set_muted(self, muted):
        self.muted = bool(muted)
        self._apply_volume()


class SpriteManager:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.animations: dict[tuple[str, str], Animation] = {}
        self.portraits: dict[str, pygame.Surface] = {}  # character_id -> surface
        self.portraits_large: dict[str, pygame.Surface] = {}
        self._build_all()
        self._load_character_portraits()

    def _build_all(self):
        self._build_parrot_animations()
        self._build_chest_animations()
        self._build_world_animations()

    def _load_character_portraits(self):
        """Load SVG character portraits for storyline characters."""
        from .dialogue import CHARACTERS

        char_dir = self.root_dir / "assets" / "characters"

        for char_id, info in CHARACTERS.items():
            svg_name = info.get("svg")
            if svg_name is None:
                continue

            svg_path = char_dir / svg_name
            surface = self._try_load_svg(svg_path, (120, 120))
            surface_large = self._try_load_svg(svg_path, (200, 200))

            if surface is None:
                surface = self._make_fallback_portrait(info["name"], info["color"], 120)
            if surface_large is None:
                surface_large = self._make_fallback_portrait(info["name"], info["color"], 200)

            self.portraits[char_id] = surface
            self.portraits_large[char_id] = surface_large

    def _try_load_svg(self, path: Path, size: tuple[int, int]) -> pygame.Surface | None:
        """Try to load SVG using cairosvg, return None if unavailable."""
        if not path.exists():
            return None
        try:
            import cairosvg
            import io
            png_data = cairosvg.svg2png(
                url=str(path),
                output_width=size[0],
                output_height=size[1],
            )
            return pygame.image.load(io.BytesIO(png_data)).convert_alpha()
        except (ImportError, Exception):
            return None

    @staticmethod
    def _make_fallback_portrait(name: str, color: tuple, size: int) -> pygame.Surface:
        """Draw a colored circle with the character's initial as fallback."""
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        radius = size // 2
        pygame.draw.circle(surf, color, (radius, radius), radius)
        pygame.draw.circle(surf, BLACK, (radius, radius), radius, width=3)
        font = pygame.font.SysFont("comicsansms", size // 2, bold=True)
        initial = font.render(name[0], True, WHITE)
        rect = initial.get_rect(center=(radius, radius))
        surf.blit(initial, rect)
        return surf

    def get_portrait(self, char_id: str, large: bool = False) -> pygame.Surface | None:
        """Get a character portrait surface."""
        if large:
            return self.portraits_large.get(char_id)
        return self.portraits.get(char_id)

    def _get_or_generate_sequence(self, group, anim, frame_size, generator, count, fps):
        frames = self._try_load_external(group, anim, frame_size)
        if not frames:
            frames = [generator(i, count) for i in range(count)]
        self.animations[(group, anim)] = Animation(frames=frames, fps=fps)

    def _try_load_external(self, group, anim, frame_size):
        folder = self.root_dir / "assets" / "sprites" / group
        frames = []
        if not folder.exists():
            return frames
        idx = 0
        while True:
            candidate = folder / f"{anim}_{idx}.png"
            if not candidate.exists():
                break
            try:
                img = pygame.image.load(str(candidate)).convert_alpha()
            except pygame.error:
                break
            img = pygame.transform.smoothscale(img, frame_size)
            frames.append(img)
            idx += 1
        return frames

    def _build_parrot_animations(self):
        size = (280, 260)

        def gen_factory(emotion):
            def _gen(i, count):
                surf = pygame.Surface(size, pygame.SRCALPHA)
                t = i / max(1, count)
                x = size[0] // 2
                y = 130
                draw_parrot_fallback(surf, x, y, t * 6.28, emotion=emotion)
                return surf

            return _gen

        for emotion in ("idle", "talk", "angry", "surprised", "cheer"):
            self._get_or_generate_sequence("parrot", emotion, size, gen_factory(emotion), count=12, fps=10.0)

    def _build_chest_animations(self):
        size = (620, 330)

        def gen_closed(i, count):
            surf = pygame.Surface(size, pygame.SRCALPHA)
            draw_chest_fallback(surf, (310, 190), t=i / max(1, count), open_amount=0.0, shake=0.0)
            return surf

        def gen_shake(i, count):
            surf = pygame.Surface(size, pygame.SRCALPHA)
            draw_chest_fallback(surf, (310, 190), t=i / max(1, count), open_amount=0.0, shake=1.0)
            return surf

        def gen_open(i, count):
            surf = pygame.Surface(size, pygame.SRCALPHA)
            amt = i / max(1, count - 1)
            draw_chest_fallback(surf, (310, 190), t=i / max(1, count), open_amount=amt, shake=0.0)
            return surf

        self._get_or_generate_sequence("chest", "closed", size, gen_closed, count=1, fps=1.0)
        self._get_or_generate_sequence("chest", "shake", size, gen_shake, count=6, fps=20.0)
        self._get_or_generate_sequence("chest", "open", size, gen_open, count=8, fps=12.0)

    def _build_world_animations(self):
        wave_size = (900, 180)

        def gen_wave(i, count):
            surf = pygame.Surface(wave_size, pygame.SRCALPHA)
            phase = i / max(1, count) * math.pi * 2
            for x in range(0, wave_size[0], 36):
                y = 32 + int(math.sin(phase + x * 0.04) * 5)
                pygame.draw.arc(surf, (180, 238, 255, 170), (x, y, 34, 12), 0, math.pi, 2)
            return surf

        sparkle_size = (900, 600)

        def gen_sparkle(i, count):
            surf = pygame.Surface(sparkle_size, pygame.SRCALPHA)
            seed = i + 11
            # Deterministic pseudo randomness for stable animation frames.
            for n in range(16):
                px = (seed * (n * 71 + 19)) % 900
                py = 60 + ((seed * (n * 43 + 29)) % 320)
                r = 2 + ((seed + n) % 3)
                col = (255, 244, 170, 110)
                pygame.draw.circle(surf, col, (px, py), r)
            return surf

        self._get_or_generate_sequence("world", "waves", wave_size, gen_wave, count=16, fps=8.0)
        self._get_or_generate_sequence("world", "sparkles", sparkle_size, gen_sparkle, count=12, fps=6.0)

    def frame(self, group, anim, t):
        animation = self.animations.get((group, anim))
        if not animation:
            return None
        return animation.frame_at(t)

    def draw_parrot(self, surface, pos, emotion, t, fallback=None):
        key = emotion if ("parrot", emotion) in self.animations else "idle"
        frame = self.frame("parrot", key, t)
        if frame is None:
            if fallback is not None:
                fallback(surface)
            return
        rect = frame.get_rect(center=pos)
        surface.blit(frame, rect)

    def draw_chest(self, surface, pos, state, t, fallback=None):
        anim_name = state if ("chest", state) in self.animations else "closed"
        frame = self.frame("chest", anim_name, t)
        if frame is None:
            if fallback is not None:
                fallback(surface)
            return
        rect = frame.get_rect(center=pos)
        surface.blit(frame, rect)

    def draw_world_overlays(self, surface, t):
        wave = self.frame("world", "waves", t)
        spark = self.frame("world", "sparkles", t)
        if wave is not None:
            surface.blit(wave, (0, 250))
        if spark is not None:
            surface.blit(spark, (0, 0))

    def draw_badge_icon(self, surface, rect):
        pygame.draw.rect(surface, (60, 76, 130), rect, border_radius=14)
        pygame.draw.rect(surface, WHITE, rect, width=3, border_radius=14)
        cx, cy = rect.center
        pygame.draw.circle(surface, (255, 220, 78), (cx, cy), min(rect.width, rect.height) // 3)
        pygame.draw.polygon(surface, GREEN, [(cx - 10, cy + 1), (cx - 2, cy + 10), (cx + 12, cy - 8)], width=4)
        pygame.draw.circle(surface, BLACK, (cx, cy), min(rect.width, rect.height) // 3, width=2)
