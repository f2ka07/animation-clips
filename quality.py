"""Pre-generation quality checks for stick-figure clips."""

from dataclasses import dataclass, field

from prompts import validate_action


@dataclass
class QualityReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def preflight_clip(
    *,
    action: str,
    prompt: str,
    duration_seconds: int,
    provider: str,
    enable_prompt_expansion: bool,
) -> QualityReport:
    report = QualityReport()

    for warning in validate_action(action):
        report.warnings.append(warning)

    word_count = len(prompt.split())
    if word_count > 220:
        report.warnings.append(
            f"Prompt is {word_count} words; MiniMax/Hailuo works best under ~180 words."
        )
    if word_count < 25:
        report.errors.append("Prompt is too short; add style + background + action detail.")

    if duration_seconds < 5 or duration_seconds > 10:
        report.errors.append("Duration must be between 5 and 10 seconds.")

    photoreal_triggers = ("kitten", "photorealistic", "3d render", "anime", "city skyline")
    lowered = prompt.lower()
    for trigger in photoreal_triggers:
        if trigger in lowered:
            report.warnings.append(
                f"Prompt contains '{trigger}', which often breaks stick-figure style."
            )

    if provider == "runpod" and enable_prompt_expansion:
        report.warnings.append(
            "enable_prompt_expansion=true can add unwanted detail to stick-figure "
            "clips. Prefer false for consistent ink style."
        )

    if "background:" not in lowered and "action:" not in lowered:
        report.warnings.append(
            "Consider Background + Action format for visual consistency across clips."
        )

    if "character:" not in lowered:
        report.warnings.append(
            "Prompt has no Character block; use the default channel protagonist wording."
        )

    if action.count(".") > 4:
        report.warnings.append("Too many sentences in action; simplify to one beat.")

    return report
