"""Prompt and action builders for consistent, stitchable stick-figure clips."""

CLIP_DURATION_MIN = 5
CLIP_DURATION_MAX = 10

SETTING_BACKGROUNDS: dict[str, str] = {
    "desk": "Simple desk with a notebook on off white paper.",
    "office": "Simple office desk with a laptop on off white paper.",
    "bed": "Simple bed with a bedside table on off white paper.",
    "kitchen counter": "Simple kitchen counter with a cup on off white paper.",
    "couch": "Simple couch on off white paper.",
    "doorway": "Simple doorway on off white paper.",
    "chair": "Simple chair on off white paper.",
    "bus stop": "Simple bus stop sign on off white paper.",
    "hallway": "Simple hallway on off white paper.",
    "bathroom mirror": "Simple bathroom mirror on off white paper.",
    "grocery aisle": "Simple grocery shelf on off white paper.",
}

BEAT_TYPES = (
    "setup",
    "trigger",
    "reaction",
    "loop",
    "choice",
    "relief",
    "regret",
    "reset",
)

EVERYDAY_SETTINGS = (
    "desk",
    "office",
    "bed",
    "kitchen counter",
    "couch",
    "doorway",
    "chair",
    "bus stop",
    "hallway",
    "bathroom mirror",
    "grocery aisle",
)

ALLOWED_PROPS = (
    "phone",
    "clock",
    "notebook",
    "book",
    "cup",
    "door",
    "chair",
    "box",
    "arrow",
    "circle",
    "thought bubble",
    "speech bubble",
    "checklist",
    "wallet",
    "keys",
    "laptop",
    "bag",
)

NEGATIVE_PROMPT = (
    "photorealistic, 3d render, anime, cartoon character, detailed face, complex background, "
    "color, text, subtitles, watermark, logo, distorted body, extra limbs, extra fingers, "
    "broken anatomy, flickering, blurry, camera shake, fast cuts, messy scene, over detailed, "
    "crowd, city street, restaurant, party, classroom, multiple rooms, scene change, "
    "different character design, hair, clothes, shaded face, realistic human"
)

# Channel protagonist — same wording in every clip prompt.
DEFAULT_CHARACTER_DESCRIPTION = (
    "The same stick figure protagonist in every clip: simple round head, two dot eyes, "
    "one short curved mouth line, straight stick limbs, three-finger hands, same body "
    "proportions and black ink line weight, no hair, no clothes detail, no nose, no ears."
)


def normalize_duration(duration_seconds: int | None) -> int:
    if duration_seconds is None:
        return CLIP_DURATION_MIN
    return max(CLIP_DURATION_MIN, min(CLIP_DURATION_MAX, duration_seconds))


def build_character_block(character_description: str | None = None) -> str:
    text = (character_description or DEFAULT_CHARACTER_DESCRIPTION).strip()
    return f"Character: {text}"


def build_style_prefix(duration_seconds: int | None = None) -> str:
    duration = normalize_duration(duration_seconds)
    return (
        "Minimalist hand drawn stick figure animation on an off white paper texture background. "
        "Black ink line art, simple expressive stick figures, clean educational psychology "
        "documentary style, smooth motion, consistent character proportions, subtle sketch "
        "imperfections, no text, no subtitles, no logos, no watermark, no color, no shading, "
        f"fixed camera, single location, {duration} second clip."
    )


def build_background(setting: str | None = None, background: str | None = None) -> str:
    if background:
        return background.strip()
    if setting and setting in SETTING_BACKGROUNDS:
        return SETTING_BACKGROUNDS[setting]
    if setting and setting in EVERYDAY_SETTINGS:
        return f"Simple {setting} on off white paper."
    return ""


def build_prompt(
    action_prompt: str,
    duration_seconds: int | None = None,
    *,
    setting: str | None = None,
    background: str | None = None,
    character_description: str | None = None,
) -> str:
    style = build_style_prefix(duration_seconds)
    character = build_character_block(character_description)
    action = normalize_action_subject(action_prompt.strip())
    bg = build_background(setting=setting, background=background)
    if bg:
        return f"{style} {character} Background: {bg} Action: {action}"
    return f"{style} {character} Action: {action}"


def normalize_action_subject(action: str) -> str:
    """Use the channel protagonist phrasing when the action names a generic figure."""
    lowered = action.lower()
    replacements = (
        ("a stick figure ", "The same stick figure protagonist "),
        ("stick figure ", "The same stick figure protagonist "),
        ("the stick figure ", "The same stick figure protagonist "),
    )
    for old, new in replacements:
        if lowered.startswith(old):
            return new + action[len(old) :]
    return action


def build_action(
    *,
    setting: str,
    beat: str,
    subject: str = "The same stick figure protagonist",
    props: list[str] | None = None,
    motion: str = "",
    emotion_change: str = "",
    actors: int = 1,
) -> str:
    """Build a reusable action sentence from the clip grammar."""
    if beat not in BEAT_TYPES:
        raise ValueError(f"beat must be one of: {', '.join(BEAT_TYPES)}")

    if actors > 2:
        raise ValueError("Use at most two stick figures per clip.")

    prop_phrase = ""
    if props:
        allowed = [prop for prop in props if prop in ALLOWED_PROPS]
        if allowed:
            prop_phrase = f" Props: {', '.join(allowed)}."

    parts = [f"{subject} at a {setting}."]
    if motion:
        parts.append(motion.strip())
    if emotion_change:
        parts.append(emotion_change.strip())
    if prop_phrase:
        parts.append(prop_phrase.strip())

    action = " ".join(part for part in parts if part)
    if not action.endswith("."):
        action += "."
    return action


def validate_action(action: str) -> list[str]:
    """Return warnings when an action may be too complex for reliable generation."""
    warnings: list[str] = []
    lowered = action.lower()

    if len(action.split()) > 55:
        warnings.append("Action is long; aim for 20-45 words.")

    complex_words = (
        "crowd",
        "city",
        "restaurant",
        "party",
        "classroom",
        "battle",
        "car chase",
        "forest",
        "mountain",
        "ocean",
        "dance floor",
    )
    for word in complex_words:
        if word in lowered:
            warnings.append(f"Avoid complex visual word: {word}")

    if lowered.count("then") > 3:
        warnings.append("Too many beats in one clip; split into multiple clips.")

    if "stick figures" in lowered or "three" in lowered or "several" in lowered:
        warnings.append("Prefer one or two stick figures only.")

    return warnings
