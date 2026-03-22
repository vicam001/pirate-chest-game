"""Centralized dialogue, storyline, and character data."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DialogueLine:
    character: str  # "virgil", "captain", "nina", "gibbs"
    text: str
    emotion: str = "happy"  # happy, excited, worried, angry, silly
    audience_cue: str | None = None  # shown in presentation mode
    auto_advance_ms: int = 0  # 0 = wait for click


@dataclass
class DialogueSequence:
    lines: list[DialogueLine] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Character definitions
# ---------------------------------------------------------------------------

CHARACTERS = {
    "virgil": {
        "name": "Virgil",
        "color": (58, 205, 95),
        "svg": None,  # drawn procedurally
    },
    "captain": {
        "name": "Captain Brinebeard",
        "color": (180, 120, 60),
        "svg": "captain-brinebeard.svg",
    },
    "nina": {
        "name": "Nina",
        "color": (255, 170, 80),
        "svg": "young-deckhand-nina.svg",
    },
    "gibbs": {
        "name": "Ghostly Gibbs",
        "color": (160, 200, 220),
        "svg": "ghostly-gibbs.svg",
    },
}

# Map emotions to parrot sprite animations
EMOTION_TO_PARROT = {
    "happy": "idle",
    "excited": "cheer",
    "worried": "surprised",
    "angry": "angry",
    "silly": "talk",
}

# ---------------------------------------------------------------------------
# Virgil catchphrases
# ---------------------------------------------------------------------------

VIRGIL_CATCHPHRASES = [
    "SQUAWK!",
    "Shiver me passwords!",
    "Arrr-mazing!",
    "Crackers and cannons!",
    "Your password is YOUR treasure!",
]

# ---------------------------------------------------------------------------
# Story dialogue by chapter
# ---------------------------------------------------------------------------

TITLE_DIALOGUE = DialogueSequence([
    DialogueLine("virgil", "Ahoy, brave pirates! I am Virgil, the smartest parrot on all seven seas!", "excited"),
    DialogueLine("virgil", "My crew found treasure -- but cyber-pirates want to steal it!", "worried"),
    DialogueLine("virgil", "Will you help us protect our treasure? SQUAWK!", "excited",
                 audience_cue="WAVE if you are ready!"),
    DialogueLine("captain", "Welcome aboard! I am Captain Brinebeard. Together we sail!", "happy"),
])

VOYAGE_Q1_INTRO = DialogueSequence([
    DialogueLine("virgil", "Nina found a message in a bottle. A stranger wants her address!", "worried"),
    DialogueLine("nina", "Should I tell them where I live? What do YOU think?", "worried",
                 audience_cue="SHOUT the answer!"),
])

VOYAGE_Q1_CORRECT = DialogueSequence([
    DialogueLine("nina", "I knew it! My address is MY secret. Thanks, friends!", "excited"),
])

VOYAGE_Q1_WRONG = DialogueSequence([
    DialogueLine("virgil", "Careful! Your address is secret treasure. Never share it online!", "angry"),
])

VOYAGE_Q2_INTRO = DialogueSequence([
    DialogueLine("virgil", "The Captain needs a password for the treasure chest lock.", "happy"),
    DialogueLine("captain", "Which password should I use to protect our gold?", "happy",
                 audience_cue="POINT to A or B!"),
])

VOYAGE_Q2_CORRECT = DialogueSequence([
    DialogueLine("captain", "Mix letters, numbers AND symbols. That is captain-grade security!", "excited"),
])

VOYAGE_Q2_WRONG = DialogueSequence([
    DialogueLine("captain", "Too simple! Even a baby shark could guess that!", "angry"),
])

VOYAGE_Q3_INTRO = DialogueSequence([
    DialogueLine("virgil", "Poor Ghostly Gibbs has a scary story to tell...", "worried"),
    DialogueLine("gibbs", "I shared my password with a friend... and cyber-pirates stole everything!", "worried"),
    DialogueLine("gibbs", "Now I am a ghost! Do not make MY mistake!", "angry",
                 audience_cue="SHOUT the answer!"),
])

VOYAGE_Q3_CORRECT = DialogueSequence([
    DialogueLine("virgil", "Only share with trusted grown-ups like parents. Never friends!", "excited"),
])

VOYAGE_Q3_WRONG = DialogueSequence([
    DialogueLine("gibbs", "Nooo! That is exactly what I did! Do not be like Gibbs!", "angry"),
])

VOYAGE_ARRIVE = DialogueSequence([
    DialogueLine("virgil", "Land ho! We made it to Password Island! SQUAWK!", "excited"),
])

# Crack Scene
CRACK_INTRO = DialogueSequence([
    DialogueLine("virgil", "See this chest? It has a weak lock. Let us crack it!", "excited"),
    DialogueLine("virgil", "Spin the dials. Try to guess the code!", "happy"),
])

CRACK_INTRO_PRESENTATION = DialogueSequence([
    DialogueLine("virgil", "See this chest? It has a weak lock. Let us crack it to see WHY weak passwords are bad!", "excited"),
    DialogueLine("virgil", "Who is brave enough to come try? SQUAWK!", "excited",
                 audience_cue="RAISE YOUR HAND!"),
])

CRACK_SUCCESS = DialogueSequence([
    DialogueLine("virgil", "SQUAWK! You cracked it! See how easy that was?", "excited"),
    DialogueLine("virgil", "Now imagine a REAL cyber-pirate doing this to YOUR password...", "worried"),
    DialogueLine("nina", "That is why we need STRONG passwords! Let us learn how!", "excited"),
])

CRACK_IDLE_QUOTES = [
    "Short passwords are easy to guess. That is why THIS lock is so weak!",
    "Every extra number makes it 10 times harder. Math is a pirate's friend!",
    "Imagine if this lock had LETTERS too... so many more combinations!",
    "Click on me for a hint! But real pirates try to guess first!",
    "Never share your home address with strangers online!",
    "Your birthday is secret treasure -- keep it private!",
    "A strong password mixes LETTERS, NUMBERS and SYMBOLS!",
    "Never use your pet's name as a password -- pirates guess that!",
    "Only share your password with a trusted grown-up like a parent!",
    "Never click links from strangers!",
]

# Lesson Scene
LESSON_DIALOGUE = DialogueSequence([
    DialogueLine("virgil", "Time for Captain's class! Listen up, crew!", "excited"),
    DialogueLine("captain", "Rule 1: Longer passwords = stronger locks. More combinations to guess!", "happy"),
    DialogueLine("captain", "Rule 2: Mix letters, numbers, AND symbols. Like a secret pirate recipe!", "happy"),
    DialogueLine("gibbs", "I used 'password123'... and look at me now. GHOST!", "silly"),
    DialogueLine("captain", "Rule 3: NEVER share your password. Not even with best friends.", "happy"),
    DialogueLine("virgil", "Only trusted grown-ups like your parents. Got it? SQUAWK!", "excited"),
])

# Builder Scene
BUILDER_INTRO = DialogueSequence([
    DialogueLine("virgil", "Now let us BUILD a treasure-proof password together!", "excited"),
])

BUILDER_INTRO_PRESENTATION = DialogueSequence([
    DialogueLine("virgil", "Now let us BUILD a treasure-proof password together!", "excited"),
    DialogueLine("virgil", "Who wants to help? Come pick: letter, number, or symbol!", "excited",
                 audience_cue="SHOUT: LETTER, NUMBER, or SYMBOL!"),
])

# Builder strength milestones
BUILDER_MILESTONES = {
    0: DialogueLine("virgil", "Empty! Even Gibbs could crack this... and he is a GHOST!", "silly"),
    25: DialogueLine("nina", "Good start! Keep going!", "happy"),
    50: DialogueLine("virgil", "Getting stronger! Add a symbol -- they are like secret pirate marks!", "excited"),
    80: DialogueLine("captain", "Now THAT is captain-grade security!", "excited"),
    100: DialogueLine("virgil", "TREASURE-SAFE! No cyber-pirate can crack THIS!", "excited"),
}

# Finale
FINALE_DIALOGUE = DialogueSequence([
    DialogueLine("virgil", "You did it, brave pirates! You learned to protect your treasure!", "excited"),
    DialogueLine("captain", "Remember: strong passwords, private info, and trust only grown-ups!", "happy"),
    DialogueLine("nina", "I am going to make ALL my passwords super strong!", "excited"),
    DialogueLine("gibbs", "And PLEASE do not end up like me... OoOoOo!", "silly"),
    DialogueLine("virgil", "Virgil's Golden Rule: YOUR PASSWORD IS YOUR TREASURE! SQUAWK!", "excited",
                 audience_cue="All together: MY PASSWORD IS MY TREASURE!"),
])


# ---------------------------------------------------------------------------
# DialogueManager -- sequential dialogue playback
# ---------------------------------------------------------------------------

class DialogueManager:
    """Manages sequential dialogue display with character portraits."""

    def __init__(self) -> None:
        self.current_sequence: DialogueSequence | None = None
        self.current_index: int = 0
        self.timer: float = 0.0
        self.active: bool = False
        self.finished_callback = None

    def start(self, sequence: DialogueSequence, callback=None) -> None:
        self.current_sequence = sequence
        self.current_index = 0
        self.timer = 0.0
        self.active = bool(sequence.lines)
        self.finished_callback = callback

    def advance(self) -> None:
        if not self.active or self.current_sequence is None:
            return
        self.current_index += 1
        self.timer = 0.0
        if self.current_index >= len(self.current_sequence.lines):
            self.active = False
            if self.finished_callback:
                self.finished_callback()

    def update(self, dt: float) -> None:
        if not self.active or self.current_sequence is None:
            return
        line = self.current_line()
        if line and line.auto_advance_ms > 0:
            self.timer += dt * 1000
            if self.timer >= line.auto_advance_ms:
                self.advance()

    def current_line(self) -> DialogueLine | None:
        if not self.active or self.current_sequence is None:
            return None
        if self.current_index < len(self.current_sequence.lines):
            return self.current_sequence.lines[self.current_index]
        return None

    def is_finished(self) -> bool:
        return not self.active

    def reset(self) -> None:
        self.current_sequence = None
        self.current_index = 0
        self.timer = 0.0
        self.active = False
        self.finished_callback = None
