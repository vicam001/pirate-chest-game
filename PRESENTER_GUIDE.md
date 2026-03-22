# Pirate Password Chest -- Presenter Guide

**Audience:** 7-year-old boys (school setting)
**Duration:** 20 minutes (15 min activity + 5 min Q&A)
**Goal:** Teach kids that passwords protect their digital treasure, and that strong passwords are long, mixed, and secret.

---

## Before You Start (Setup Checklist)

- [ ] Laptop connected to projector or large screen
- [ ] Sound ON and volume up (the game has fun sound effects!)
- [ ] Launch the game in presentation mode:
  ```
  .venv/bin/python main.py --presentation
  ```
- [ ] Game should open fullscreen with the pirate map voyage

---

## Step-by-Step Script

### 1. The Hook (2 min)

> **Stand in front of the screen. Speak with energy!**

"Alright crew, who here likes PIRATES?"
*(Let them cheer.)*

"Today we are going on a real pirate adventure. There is a treasure chest locked with a secret code, and we need to crack it open! But first... we have to sail across the ocean and learn the pirate rules of the sea. Are you ready?"

*(Turn to the screen where the Voyage map is showing.)*

"This is our ship! And look -- there is a shark swimming next to us. Let's goooo!"

---

### 2. The Voyage -- Learning the Pirate Rules (4 min)

The ship sails across the map and stops three times to ask a question. Read each question out loud and let the kids shout their answer before clicking.

**Question 1 -- Nina asks:**
> "A stranger asks for your name online. What do you do?"

Let them answer. The correct answer is: **You do NOT tell them!**
Say: "That's right! Pirates never give their name to strangers. Your name, your school, your address -- that's YOUR treasure. Keep it secret!"

**Question 2 -- The Captain asks:**
> "Which password is harder to crack: Sun$et#42! or Pepito?"

Let them guess. The answer is **Sun$et#42!**
Say: "See all those weird symbols and numbers? That makes it super hard for bad guys to guess. 'Pepito' is way too easy!"

**Question 3 -- Ghostly Gibbs asks:**
> "Someone online asks for your home address. What do you do?"

Let them answer. Correct: **You keep it secret!**
Say: "Ghostly Gibbs did not protect his secrets... and now he's a GHOST! Don't be like Gibbs!"

*(The ship arrives at the island. Cheer with the kids!)*

---

### 3. Meet Virgil and the Chest (1 min)

The Landing screen shows a locked treasure chest and a parrot with a pirate hat.

"Look! We made it to Password Island! And this is VIRGIL, our pirate parrot. He is going to help us. But see that chest? It's LOCKED with a secret code. Let's crack it open!"

*(Click PLAY to enter the Crack scene. Keep difficulty on Easy for the demo.)*

---

### 4. Crack the Chest! (4 min)

This is the most interactive part. The screen shows a lock with spinning number dials.

"OK pirates, this chest has a one-number lock. We need to guess the right number! Shout your guesses!"

**How to play it:**
- Let kids shout numbers (0 to 9)
- Use the UP/DOWN arrows to set each number they shout
- Press TRY after each guess
- Wrong guesses make the screen shake and turn red -- the kids will love it!
- The "Weak Password Meter" fills up with each wrong guess

**While guessing, say things like:**
- "Ohhh, wrong one! The screen is shaking! Let's try another!"
- "Look at that meter filling up -- this password is SO weak that we're almost there!"
- "See how easy it is to guess a one-number code? A real pirate would crack this in seconds!"

If it takes too long, click on Virgil for a hint: "Let's ask Virgil! He always knows secrets."

**When they crack it:**
The chest opens with a big celebration! Coins fly everywhere!

"YEEEES! We cracked it! But wait... that was TOO easy, right? Imagine if the code had been longer, with letters AND symbols. It would take FOREVER to guess!"

*(Tap the treasure items inside the chest -- each one teaches a lesson. Read them out loud quickly.)*

---

### 5. The Lessons (1 min)

The Lesson screen shows five cards. Quickly go through the key messages:

1. "Longer passwords are harder to crack!"
2. "Mix letters, numbers, AND symbols!"
3. "Ghostly Gibbs used 'password123'... now he's a ghost!"
4. "NEVER share your password with friends!"
5. "Only share with your parents. SQUAWK!"

Say: "So what did we learn? A strong password is LONG, has WEIRD symbols, and is SECRET. Got it?"

*(Click BUILD PASSWORD.)*

---

### 6. Build a Super Password Together (3 min)

The Builder screen lets you add letters, numbers, and symbols one at a time. The strength bar goes from red to green.

"Now let's build the STRONGEST password ever! Tell me what to add!"

**Run it like this:**
- "Should I add a LETTER, a NUMBER, or a SYMBOL? Shout it!"
- Add what they say. After each one, point at the strength bar.
- "Look! It went from red to orange. We need to make it GREEN!"
- Keep adding characters. Mix types to show the bar climbing.
- When it hits 100%, confetti explodes on screen!

"BOOM! TREASURE-SAFE! No cyber-pirate in the world can crack THAT password!"

---

### 7. Wrap-Up and The Pirate Promise (1 min)

Stand in front of the screen again.

"OK crew, before we go -- let's make the Pirate Promise. Repeat after me:"

> **"My password is my TREASURE!"**
> *(Let them repeat.)*

> **"I will make it LONG and STRONG!"**
> *(Let them repeat.)*

> **"I will NEVER share it with strangers!"**
> *(Let them repeat.)*

"You are all now official Password Pirates! Well done!"

---

### 8. Questions (4 min)

Open the floor for questions. Common ones from this age group:

| Question | Answer |
|---|---|
| "What's the best password?" | "One that is long, has letters, numbers, and symbols, and that only YOU know!" |
| "Can I use my dog's name?" | "Not by itself! But you could hide it: D0g$torm99! -- see how we made it tricky?" |
| "What if I forget it?" | "Tell your mom or dad. They can help you keep it safe." |
| "Can I tell my best friend?" | "Nope! Passwords are like treasure maps -- only for YOU and your parents." |
| "What do hackers look like?" | "They can be anyone! That's why we protect our passwords -- we can't always tell who's a cyber-pirate." |

---

## Presenter Tips

- **Energy is everything.** If you're excited, they're excited. Use your pirate voice!
- **Let them shout.** Seven-year-olds learn by doing and saying, not by watching quietly.
- **Wrong answers are great.** Never say "no, that's wrong." Say "Ohhh, almost! But what if..." and guide them.
- **Keep it moving.** If a section runs long, skip ahead. The Crack scene and Builder are the most impactful parts.
- **Use Virgil.** Click on the parrot whenever energy dips -- he says funny things and the kids love the animations.
- **Three things to remember.** At this age, they'll retain at most three ideas. Hammer these home:
  1. Passwords should be **long**
  2. Passwords should be **mixed up** (letters + numbers + symbols)
  3. Passwords are **secret** (only parents know)

---

## If Something Goes Wrong

| Problem | Solution |
|---|---|
| No sound | Check system volume. Game has a Settings button on the landing screen with volume sliders. |
| Game won't start | Make sure you're using the right Python: `.venv/bin/python main.py --presentation` |
| Kids get stuck on Crack | Click Virgil for a hint -- he reveals one digit. |
| Kids lose focus | Jump ahead to the Builder scene -- building their own password re-engages them instantly. |
| Projector shows black bars | The game auto-scales with letterboxing. This is normal. |
