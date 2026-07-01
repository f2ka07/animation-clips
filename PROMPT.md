# wan-stick-clips — clip scripting system

Build a reusable library of **5–10 second** stick-figure clips about everyday life. Each clip is one small moment. Stitch many clips together to make any video idea.

Channel context: **"The Psychology of"** — but clips should stay generic enough to reuse across psychology, self-help, habits, money, relationships, and productivity videos.

---

## Core idea

Think in **Lego blocks**, not finished videos.

| Layer | What it is | File |
|-------|------------|------|
| **Atom** | One 5–10s clip, one beat | `data/clip_specs.json` |
| **Library** | Generated MP4s + metadata | `data/clips_index.json` |
| **Recipe** | Ordered list of clips for one video | `data/video_recipes.json` |
| **Video** | Recipe stitched in an editor | DaVinci / Premiere / CapCut |

Generate atoms once. Recombine atoms forever.

---

## Atomic clip rules

Every clip must obey these rules or generation will fail or look inconsistent.

### One clip = one beat

A beat is a **single change**: notice, hesitate, reach, scroll, slump, freeze, smile, regret.

| Duration | Beats allowed | Use when |
|----------|---------------|----------|
| **5s** | 1 beat | trigger, reaction, loop moment |
| **6–10s** | 1–2 beats | setup + reaction, choice + regret |

Never put a full story in one clip. Split it.

### Visual limits

- **1–2 stick figures** only
- **1 location** only (desk, bed, doorway, couch, kitchen counter, chair, hallway)
- **Fixed camera** — no pans, zooms, or cuts
- **0–2 props** from the allowed list
- **No text** on screen (no subtitles, signs, UI)

### Allowed props

```
phone, clock, notebook, book, cup, door, chair, box, arrow, circle,
thought bubble, speech bubble, checklist, wallet, keys, laptop, bag
```

### Avoid (breaks the model)

Crowds, streets, restaurants, parties, classrooms, forests, detailed faces, color, camera movement, scene changes, more than two figures.

---

## Action sentence grammar

Every `action` field in `clip_specs.json` should follow this pattern:

```
[Who] at [setting]. [Motion]. [Emotion or posture change]. [Optional prop cue].
```

### Beat types

| Beat | Purpose | Example motion |
|------|---------|----------------|
| `setup` | Normal state | sits at desk with notebook |
| `trigger` | Cue appears | phone buzzes on desk |
| `reaction` | Response | picks up phone and scrolls |
| `loop` | Repeating habit | taps phone again and again |
| `choice` | Decision point | stands between two arrows |
| `relief` | Short calm | exhales and unclenches shoulders |
| `regret` | Aftermath | slumps and stares at floor |
| `reset` | Try again | stands up and takes one step forward |

### Good action (5s)

```
A stick figure sits at a desk with a notebook. The figure looks at the work,
hesitates, notices a phone, picks it up, smiles while scrolling, then looks
worried as a clock appears in the background.
```

### Bad action (too much)

```
A stick figure wakes up, makes coffee, commutes on a bus, opens laptop at
office, argues with boss, then goes home sad.
```

Split that into **six clips**.

---

## Categories and tags

### Categories (theme of the moment)

```
procrastination, anxiety, social_pressure, reward_loop, decision_making,
comfort_zone, conflict, attention, habit, money
```

Add more as needed: `sleep`, `relationships`, `work`, `health`, `parenting`.

### Tags (how you find and reuse clips)

Use **cross-cutting tags** so one clip fits many videos:

```
phone, morning, alone, delay, worry, desk, scrolling, regret, posture,
doorway, kitchen, tired, relief, temptation
```

**Rule:** 3–6 tags per clip. At least one **object tag** (phone, desk) and one **emotion tag** (worry, relief).

---

## clip_specs.json schema

```json
{
  "title": "Avoiding Work",
  "category": "procrastination",
  "tags": ["delay", "work", "phone", "avoidance", "desk"],
  "beat": "loop",
  "setting": "desk",
  "duration_seconds": 5,
  "action": "A stick figure sits at a desk with a notebook..."
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `title` | yes | Unique per category |
| `category` | yes | Theme bucket |
| `tags` | yes | Search + recipe matching |
| `action` | yes | 20–45 words |
| `duration_seconds` | no | 5–10, default 5 |
| `beat` | no | Helps you plan sequences |
| `setting` | no | Helps consistency |

---

## video_recipes.json (stitch plans)

A recipe is an ordered playlist of clips for one video idea:

```json
{
  "id": "why_we_procrastinate",
  "title": "Why We Procrastinate",
  "description": "Setup distraction, loop, then deadline panic.",
  "target_duration_seconds": 20,
  "clips": [
    {"title": "Avoiding Work", "category": "procrastination"},
    {"title": "Phone Distraction", "category": "attention"},
    {"title": "Deadline Panic", "category": "procrastination"}
  ]
}
```

List recipes:

```bash
python compose_recipe.py --list
python compose_recipe.py --recipe why_we_procrastinate
```

Shows which clips exist in your library and which still need generation.

---

## Tools in this project

### Build a new script entry

```bash
python script_builder.py \
  --title "Morning Snooze" \
  --category "habit" \
  --tags "sleep,morning,bed,delay" \
  --setting bed \
  --beat trigger \
  --motion "An alarm clock appears. The figure reaches to turn it off and pulls the blanket back up." \
  --emotion-change "The figure curls back into bed with a relieved expression." \
  --duration 5
```

Outputs the `action` sentence and a ready `clip_specs.json` entry.

### Generate one clip

```bash
python generate_clip.py \
  --title "Morning Snooze" \
  --category "habit" \
  --tags "sleep,morning,bed,delay" \
  --duration 5 \
  --action "A stick figure lies in bed. An alarm clock appears..."
```

### Batch generate library

```bash
python batch_generate.py
```

### Search library

```bash
python library.py --tag phone
python library.py --category procrastination
```

---

## Prompt template (style + action)

Implemented in `prompts.py`:

**Style prefix** (auto-includes duration):

```
Minimalist hand drawn stick figure animation on an off white paper texture
background. Black ink line art, simple expressive stick figures, clean
educational psychology documentary style, smooth motion, consistent character
proportions, subtle sketch imperfections, no text, no subtitles, no logos,
no watermark, no color, no shading, fixed camera, single location,
{N} second clip.
```

**Negative prompt:** photorealistic, 3d, anime, color, text, crowds, complex backgrounds, camera shake, etc.

---

## LLM prompt — generate unlimited everyday clips

Use this when asking Cursor or another LLM to expand `clip_specs.json`:

```
You are writing clip_specs.json entries for a stick-figure everyday-life video library.

Rules:
- Each clip is 5 or 10 seconds, one location, 1-2 stick figures, fixed camera.
- One beat per 5s clip. At most two beats in a 10s clip.
- Use only these props: phone, clock, notebook, book, cup, door, chair, box,
  arrow, circle, thought bubble, speech bubble, checklist, wallet, keys,
  laptop, bag.
- Action must be 20-45 words, present tense, concrete motion.
- No crowds, no outdoor scenes, no text on screen, no scene changes.
- Categories: procrastination, anxiety, social_pressure, reward_loop,
  decision_making, comfort_zone, conflict, attention, habit, money.
- Include beat, setting, duration_seconds, title, category, tags, action.

Generate 10 NEW clips about everyday life that are NOT duplicates of:
Avoiding Work, Phone Distraction, Overthinking Message.

Focus on: {TOPIC e.g. morning routine / waiting / chores / texting / tired after work}

Output valid JSON array only.
```

Swap `{TOPIC}` to produce unlimited batches: mornings, laundry, groceries, waiting room, gym avoidance, late-night scrolling, etc.

---

## Recipe patterns (mix clips into video types)

| Video type | Clip pattern | Example beats |
|------------|--------------|---------------|
| **Explain a habit** | setup → trigger → loop | Habit Trigger → Phone Distraction → Social Media Loop |
| **Anxiety arc** | worry → avoidance → small win | Overthinking Message → Fear of Judgment → Confidence Shift |
| **Money mistake** | temptation → reward → regret | Impulse Buying → Reward Loop → Regret After Choice |
| **Procrastination** | avoid → distract → panic | Avoiding Work → Phone Distraction → Deadline Panic |
| **Conflict** | silence → resentment → reset | People Pleasing → Silent Resentment → Learning From Failure |

Same clips, different order = different video.

---

## Quality checklist (before batch generate)

- [ ] Action is 20–45 words
- [ ] Only 1–2 stick figures
- [ ] One location
- [ ] At most 2 props named
- [ ] At most 3 "then" transitions
- [ ] No banned complex words (crowd, city, party, etc.)
- [ ] Tags include object + emotion
- [ ] Duration is 5 or 10 seconds
- [ ] Clip can stand alone AND fit a recipe

Run `python script_builder.py ...` — it prints warnings automatically.

---

## Everyday life idea bank (generate from)

Use these topics to create unlimited scripts:

**Morning:** snooze, rush, coffee, mirror, outfit indecision, leaving late  
**Work:** open laptop, stare at screen, meeting dread, slack notification  
**Home:** dishes, laundry pile, couch collapse, fridge stare, remote search  
**Social:** typing reply, read receipt wait, cancel plans, awkward hello  
**Phone:** scroll loop, battery low, notification stack, compare post  
**Money:** cart add, price shock, buy anyway, check balance  
**Health:** skip gym, short walk, water bottle, snack instead  
**Sleep:** can't sleep, one more video, alarm dread, tired morning  

Each bullet can become 3–5 atomic clips.

---

## Technical project notes (current stack)

- CLI: `generate_clip.py`, `batch_generate.py`, `library.py`
- Providers: `PROVIDER=aws` (EC2 g5.xlarge Wan server), `minimax`, `runpod`
- Inference: `server/` Docker image around official Wan 2.2
- Clips indexed in `data/clips_index.json`, MP4s in `outputs/`
- Duration: set per clip with `--duration` or `duration_seconds` in specs

---

## Success metric

You have the idea right when:

1. You can describe any video as **3–6 clip titles**
2. Most clips already exist in the library
3. Missing clips take **one script_builder command** to add
4. A new video is mostly **recipe + stitch**, not new generation

That is unlimited reusable everyday-life production.

---

## Quality workflow

Quality is enforced in three layers: **prompt design**, **pre-generation checks**, and **human review**.

### 1. Prompt design (before generation)

- One beat, one location, 1-2 stick figures (see atomic clip rules above).
- Use **Background + Action** format so settings stay consistent across clips:
  - `Background: Simple office desk, white wall, minimal props.`
  - `Action: Stick figure hesitates over notebook, then picks up phone and scrolls.`
- Pass `--setting office` or `--background "..."` to `generate_clip.py` / `script_builder.py`.
- Keep `enable_prompt_expansion=false` for RunPod MiniMax Hailuo (expansion adds unwanted detail).

### 2. Pre-generation preflight (`quality.py`)

Before calling the API, `generate_clip.py` runs `preflight_clip()`:

- Errors block generation (use `--force` to override).
- Warnings print but still generate.

Checks include: action length, prompt word count, duration 5-10s, photoreal triggers, expansion flag, Background+Action format.

Dry-run without spending credits:

```bash
python generate_clip.py --title "Test" --category "work" --tags "test" \
  --action "Stick figure opens laptop and stares at blank screen." \
  --setting office --duration 6 --dry-run
```

### 3. Human review (after generation)

New clips are saved with `review_status=pending_review`. Watch the MP4 in `outputs/`, then:

```bash
python library.py --pending-review
python library.py --approve --title "Avoiding Work" --clip-category procrastination
python library.py --reject --title "Bad Take" --clip-category procrastination
```

Only **approved** clips are used when resolving recipes (`compose_recipe.py`). Pending or rejected clips show as yellow/red in the recipe table.

### RunPod MiniMax Hailuo (matches `D:\VideoApp\API`)

Put `RUNPOD_API_KEY` in `D:\VideoApp\.env` (loaded automatically) or `wan-stick-clips/.env`:

```env
PROVIDER=runpod
RUNPOD_ENDPOINT_ID=minimax-hailuo-02-std
RUNPOD_PAYLOAD_PROFILE=minimax_hailuo
MINIMAX_HAILUO_ENABLE_PROMPT_EXPANSION=false
```

Payload shape matches your curl: `input.prompt`, `input.duration` (6 or 10), `input.enable_prompt_expansion`.

