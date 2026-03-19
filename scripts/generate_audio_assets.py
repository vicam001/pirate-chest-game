#!/usr/bin/env python3
"""Generate original music and SFX assets for Pirate Password Chest.

Creates WAV files at:
- assets/audio/music/island_loop.wav
- assets/audio/sfx/{click,dial,clunk,success,confetti,reward}.wav
"""

from __future__ import annotations

import argparse
import math
import random
import wave
from pathlib import Path

SAMPLE_RATE = 22050
RNG = random.Random(1337)
TWOPI = 2.0 * math.pi


def midi_to_freq(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def envelope(t: float, dur: float, attack: float, release: float) -> float:
    if dur <= 0:
        return 0.0
    if t < 0 or t > dur:
        return 0.0
    if attack > 0 and t < attack:
        return t / attack
    if release > 0 and t > dur - release:
        return max(0.0, (dur - t) / release)
    return 1.0


def write_wav(path: Path, samples: list[float], target_peak: float = 0.9) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = max((abs(v) for v in samples), default=1.0)
    if peak < 1e-9:
        peak = 1.0
    target_peak = max(0.05, min(0.98, target_peak))
    scale = target_peak / peak

    pcm = bytearray()
    for v in samples:
        v = max(-1.0, min(1.0, v * scale))
        pcm += int(v * 32767.0).to_bytes(2, byteorder="little", signed=True)

    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(bytes(pcm))


def make_buffer(duration_sec: float) -> list[float]:
    return [0.0] * int(SAMPLE_RATE * duration_sec)


def add_tone(
    buf: list[float],
    start_sec: float,
    dur_sec: float,
    freq: float,
    amp: float,
    wave_shape: str = "sine",
    attack: float = 0.005,
    release: float = 0.05,
    vibrato_hz: float = 0.0,
    vibrato_depth: float = 0.0,
) -> None:
    start = int(start_sec * SAMPLE_RATE)
    length = int(dur_sec * SAMPLE_RATE)

    for i in range(length):
        idx = start + i
        if idx >= len(buf):
            break

        t = i / SAMPLE_RATE
        env = envelope(t, dur_sec, attack, release)

        inst_freq = freq
        if vibrato_hz > 0 and vibrato_depth > 0:
            inst_freq = freq * (1.0 + vibrato_depth * math.sin(TWOPI * vibrato_hz * t))

        phase = TWOPI * inst_freq * t
        if wave_shape == "sine":
            osc = math.sin(phase)
        elif wave_shape == "triangle":
            osc = (2.0 / math.pi) * math.asin(math.sin(phase))
        elif wave_shape == "square":
            osc = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave_shape == "pluck":
            osc = (
                0.72 * math.sin(phase)
                + 0.2 * math.sin(2.0 * phase + 0.1)
                + 0.08 * math.sin(3.0 * phase + 0.3)
            )
        else:
            osc = math.sin(phase)

        buf[idx] += amp * env * osc


def add_noise(buf: list[float], start_sec: float, dur_sec: float, amp: float, release: float = 0.05) -> None:
    start = int(start_sec * SAMPLE_RATE)
    length = int(dur_sec * SAMPLE_RATE)
    last = 0.0

    for i in range(length):
        idx = start + i
        if idx >= len(buf):
            break
        t = i / SAMPLE_RATE
        env = envelope(t, dur_sec, 0.001, release)
        white = RNG.uniform(-1.0, 1.0)
        last = (0.84 * last) + (0.16 * white)
        buf[idx] += amp * env * last


def add_kick(buf: list[float], start_sec: float, amp: float = 0.55, dur_sec: float = 0.18) -> None:
    start = int(start_sec * SAMPLE_RATE)
    length = int(dur_sec * SAMPLE_RATE)
    for i in range(length):
        idx = start + i
        if idx >= len(buf):
            break
        t = i / SAMPLE_RATE
        env = math.exp(-16.0 * t)
        freq = 120.0 - 70.0 * min(1.0, t / dur_sec)
        tone = math.sin(TWOPI * freq * t)
        click = math.sin(TWOPI * 1800.0 * t) * math.exp(-90.0 * t)
        buf[idx] += amp * (0.9 * env * tone + 0.1 * click)


def add_snare(buf: list[float], start_sec: float, amp: float = 0.25, dur_sec: float = 0.16) -> None:
    start = int(start_sec * SAMPLE_RATE)
    length = int(dur_sec * SAMPLE_RATE)
    last = 0.0
    for i in range(length):
        idx = start + i
        if idx >= len(buf):
            break
        t = i / SAMPLE_RATE
        env = math.exp(-24.0 * t)
        white = RNG.uniform(-1.0, 1.0)
        last = 0.6 * last + 0.4 * white
        tone = math.sin(TWOPI * 210.0 * t) * math.exp(-20.0 * t)
        buf[idx] += amp * env * (0.82 * last + 0.18 * tone)


def add_hat(buf: list[float], start_sec: float, amp: float = 0.09, dur_sec: float = 0.06) -> None:
    start = int(start_sec * SAMPLE_RATE)
    length = int(dur_sec * SAMPLE_RATE)
    last = 0.0
    for i in range(length):
        idx = start + i
        if idx >= len(buf):
            break
        t = i / SAMPLE_RATE
        env = math.exp(-70.0 * t)
        white = RNG.uniform(-1.0, 1.0)
        hp = white - last
        last = white
        buf[idx] += amp * env * hp


def soft_clip(samples: list[float], drive: float = 1.25) -> list[float]:
    return [math.tanh(drive * x) / math.tanh(drive) for x in samples]


def fade_edges(samples: list[float], fade_sec: float = 0.02) -> None:
    n = int(fade_sec * SAMPLE_RATE)
    if n <= 0 or n * 2 >= len(samples):
        return
    for i in range(n):
        g = i / n
        samples[i] *= g
        samples[-1 - i] *= g


def add_simple_echo(samples: list[float], delay_sec: float, decay: float) -> None:
    delay = int(delay_sec * SAMPLE_RATE)
    if delay <= 0:
        return
    for i in range(delay, len(samples)):
        samples[i] += samples[i - delay] * decay


def generate_music() -> list[float]:
    bpm = 100
    beat = 60.0 / bpm
    bars = 12
    bar_len = beat * 4.0
    total_len = bars * bar_len
    buf = make_buffer(total_len)

    # 12-bar pirate-ish minor progression.
    chords = [
        [57, 60, 64],  # Am
        [55, 59, 62],  # G
        [53, 57, 60],  # F
        [52, 56, 59],  # E
        [57, 60, 64],
        [60, 64, 67],  # C
        [55, 59, 62],
        [52, 56, 59],
        [53, 57, 60],
        [55, 59, 62],
        [57, 60, 64],
        [52, 56, 59],
    ]

    bass = [45, 43, 41, 40, 45, 48, 43, 40, 41, 43, 45, 40]

    for bar in range(bars):
        t0 = bar * bar_len

        # Accordion-like sustained harmony.
        for note in chords[bar]:
            add_tone(
                buf,
                start_sec=t0,
                dur_sec=bar_len,
                freq=midi_to_freq(note),
                amp=0.085,
                wave_shape="pluck",
                attack=0.03,
                release=0.22,
                vibrato_hz=4.6,
                vibrato_depth=0.004,
            )

        # Bass pulses on 1 and 3.
        root = midi_to_freq(bass[bar])
        add_tone(buf, t0 + beat * 0.0, beat * 0.95, root, 0.2, wave_shape="sine", release=0.12)
        add_tone(buf, t0 + beat * 2.0, beat * 0.95, root, 0.18, wave_shape="sine", release=0.12)

        # Percussion bed.
        for b in range(4):
            add_hat(buf, t0 + b * beat)
            add_hat(buf, t0 + b * beat + beat * 0.5, amp=0.07)
        add_kick(buf, t0 + beat * 0.0)
        add_kick(buf, t0 + beat * 2.0, amp=0.48)
        add_snare(buf, t0 + beat * 1.0)
        add_snare(buf, t0 + beat * 3.0)

    motifs = [
        [(0.0, 69, 0.50), (0.5, 72, 0.50), (1.0, 74, 0.50), (1.5, 72, 0.50), (2.0, 69, 1.0)],
        [(0.0, 76, 0.50), (0.5, 74, 0.50), (1.0, 72, 0.50), (1.5, 69, 0.50), (2.0, 72, 1.0)],
        [(0.0, 74, 0.50), (0.5, 76, 0.50), (1.0, 79, 0.50), (1.5, 76, 0.50), (2.0, 74, 1.0)],
        [(0.0, 72, 0.50), (0.5, 74, 0.50), (1.0, 76, 0.50), (1.5, 74, 0.50), (2.0, 72, 1.0)],
    ]

    for bar in range(bars):
        t0 = bar * bar_len
        motif = motifs[bar % len(motifs)]
        for off_beat, midi_note, len_beat in motif:
            add_tone(
                buf,
                start_sec=t0 + (off_beat * beat),
                dur_sec=len_beat * beat,
                freq=midi_to_freq(midi_note),
                amp=0.13,
                wave_shape="triangle",
                attack=0.01,
                release=0.11,
                vibrato_hz=5.0,
                vibrato_depth=0.006,
            )

    add_simple_echo(buf, delay_sec=0.19, decay=0.18)
    buf = soft_clip(buf, drive=1.12)
    fade_edges(buf, fade_sec=0.015)
    return buf


def generate_click() -> list[float]:
    dur = 0.08
    buf = make_buffer(dur)
    add_tone(buf, 0.0, 0.05, 1300.0, 0.26, wave_shape="triangle", attack=0.001, release=0.04)
    add_tone(buf, 0.002, 0.03, 2200.0, 0.15, wave_shape="sine", attack=0.001, release=0.02)
    add_noise(buf, 0.0, 0.03, 0.05, release=0.02)
    fade_edges(buf, 0.004)
    return soft_clip(buf, drive=1.2)


def generate_dial() -> list[float]:
    dur = 0.12
    buf = make_buffer(dur)
    start = 0
    n = len(buf)
    for i in range(n):
        t = i / SAMPLE_RATE
        frac = i / max(1, n - 1)
        freq = 780.0 - 360.0 * frac
        env = math.exp(-16.0 * t)
        body = math.sin(TWOPI * freq * t)
        overtone = math.sin(TWOPI * freq * 2.2 * t + 0.2)
        buf[start + i] += 0.24 * env * (0.8 * body + 0.2 * overtone)
    add_tone(buf, 0.02, 0.04, 2500.0, 0.08, wave_shape="square", release=0.03)
    fade_edges(buf, 0.004)
    return soft_clip(buf, drive=1.1)


def generate_clunk() -> list[float]:
    dur = 0.3
    buf = make_buffer(dur)
    add_kick(buf, 0.0, amp=0.7, dur_sec=0.22)
    add_noise(buf, 0.015, 0.18, 0.1, release=0.14)
    add_tone(buf, 0.01, 0.18, 90.0, 0.15, wave_shape="triangle", attack=0.002, release=0.14)
    fade_edges(buf, 0.01)
    return soft_clip(buf, drive=1.35)


def generate_success() -> list[float]:
    dur = 0.72
    buf = make_buffer(dur)
    notes = [76, 79, 83, 88]
    t = 0.0
    for midi in notes:
        add_tone(buf, t, 0.14, midi_to_freq(midi), 0.19, wave_shape="triangle", release=0.07)
        add_tone(buf, t, 0.16, midi_to_freq(midi + 12), 0.08, wave_shape="sine", release=0.09)
        t += 0.11
    add_simple_echo(buf, 0.14, 0.25)
    fade_edges(buf, 0.01)
    return soft_clip(buf, drive=1.08)


def generate_confetti() -> list[float]:
    dur = 0.56
    buf = make_buffer(dur)
    add_noise(buf, 0.0, 0.25, 0.16, release=0.22)
    for _ in range(24):
        t = RNG.uniform(0.01, dur - 0.08)
        freq = RNG.choice([1200.0, 1500.0, 1800.0, 2100.0, 2400.0])
        note_len = RNG.uniform(0.02, 0.07)
        amp = RNG.uniform(0.05, 0.13)
        add_tone(buf, t, note_len, freq, amp, wave_shape="square", attack=0.001, release=0.03)
    fade_edges(buf, 0.01)
    return soft_clip(buf, drive=1.15)


def generate_reward() -> list[float]:
    dur = 1.12
    buf = make_buffer(dur)
    sequence = [69, 72, 76, 81, 79, 76, 72, 76, 84]
    step = 0.1
    t = 0.0
    for i, midi_note in enumerate(sequence):
        length = 0.14 if i < len(sequence) - 1 else 0.3
        add_tone(buf, t, length, midi_to_freq(midi_note), 0.17, wave_shape="triangle", release=0.09)
        add_tone(buf, t + 0.01, length, midi_to_freq(midi_note + 12), 0.07, wave_shape="sine", release=0.12)
        t += step
    add_simple_echo(buf, 0.2, 0.22)
    fade_edges(buf, 0.012)
    return soft_clip(buf, drive=1.08)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Pirate Password Chest audio assets.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root containing assets/")
    args = parser.parse_args()

    root = args.root.resolve()
    music_dir = root / "assets" / "audio" / "music"
    sfx_dir = root / "assets" / "audio" / "sfx"
    music_dir.mkdir(parents=True, exist_ok=True)
    sfx_dir.mkdir(parents=True, exist_ok=True)

    write_wav(music_dir / "island_loop.wav", generate_music(), target_peak=0.82)
    write_wav(sfx_dir / "click.wav", generate_click(), target_peak=0.9)
    write_wav(sfx_dir / "dial.wav", generate_dial(), target_peak=0.86)
    write_wav(sfx_dir / "clunk.wav", generate_clunk(), target_peak=0.9)
    write_wav(sfx_dir / "success.wav", generate_success(), target_peak=0.9)
    write_wav(sfx_dir / "confetti.wav", generate_confetti(), target_peak=0.88)
    write_wav(sfx_dir / "reward.wav", generate_reward(), target_peak=0.9)

    print("Generated audio assets:")
    print(f"- {music_dir / 'island_loop.wav'}")
    for name in ["click", "dial", "clunk", "success", "confetti", "reward"]:
        print(f"- {sfx_dir / (name + '.wav')}")


if __name__ == "__main__":
    main()
