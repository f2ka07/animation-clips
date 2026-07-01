STYLE_PREFIX = (
    "Minimalist hand drawn stick figure animation on an off white paper texture background. "
    "Black ink line art, simple expressive stick figures, clean educational psychology "
    "documentary style, smooth motion, consistent character proportions, subtle sketch "
    "imperfections, no text, no subtitles, no logos, no watermark, no color, no shading, "
    "fixed camera, 5 second clip."
)

NEGATIVE_PROMPT = (
    "photorealistic, 3d render, anime, cartoon character, detailed face, complex background, "
    "color, text, subtitles, watermark, logo, distorted body, extra limbs, extra fingers, "
    "broken anatomy, flickering, blurry, camera shake, fast cuts, messy scene, over detailed"
)


def build_prompt(action_prompt: str) -> str:
    return f"{STYLE_PREFIX} {action_prompt.strip()}"
