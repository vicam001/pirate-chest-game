"""Core constants for Pirate Password Chest."""

from __future__ import annotations

WIDTH = 900
HEIGHT = 600
TITLE = "Pirate Password Chest"
FPS = 60

# Colors
SKY_TOP = (78, 201, 255)
SKY_BOTTOM = (163, 235, 255)
OCEAN = (32, 124, 204)
OCEAN_DARK = (20, 93, 156)
SAND = (242, 211, 129)
SAND_DARK = (220, 186, 102)
WOOD = (131, 75, 38)
WOOD_DARK = (99, 53, 27)
GOLD = (250, 205, 55)
GOLD_DARK = (203, 151, 25)
WHITE = (255, 255, 255)
BLACK = (18, 18, 18)
RED = (228, 69, 69)
GREEN = (76, 196, 90)
YELLOW = (255, 245, 91)
PURPLE = (175, 90, 225)
BLUE = (46, 145, 255)
ORANGE = (255, 154, 51)
CYAN = (103, 240, 245)
DARK_BLUE = (28, 61, 116)

# Fonts
FONT_NAME = "comicsansms"
FONT_HUGE_SIZE = 64
FONT_BIG_SIZE = 52
FONT_MED_SIZE = 42
FONT_SMALL_SIZE = 34
FONT_TINY_SIZE = 24

# Save
SAVE_SCHEMA_VERSION = 1
SAVE_FILE = "data/progress.json"

# Audio
MIXER_FREQUENCY = 22050
MIXER_SIZE = -16
MIXER_CHANNELS = 1
MIXER_BUFFER = 512

# Parent mode
PARENT_HOLD_SECONDS = 2.0
PARENT_HOTSPOT = (792, 0, 108, 108)

# Presentation mode font sizes (larger for projection)
PRES_FONT_HUGE_SIZE = 80
PRES_FONT_BIG_SIZE = 64
PRES_FONT_MED_SIZE = 52
PRES_FONT_SMALL_SIZE = 42
PRES_FONT_TINY_SIZE = 32

# Audience cue colors
AUDIENCE_CUE_BG = (255, 235, 59)
AUDIENCE_CUE_BORDER = (245, 127, 23)

# Characters used in storyline
STORY_CHARACTERS = ["captain", "nina", "gibbs"]

# Difficulty labels
DIFFICULTY_ORDER = ["easy", "medium", "hard", "expert"]
