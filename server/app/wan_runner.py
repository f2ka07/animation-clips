import random
import subprocess
import sys
from pathlib import Path

from app import config


def frames_for_duration(duration_seconds: int, fps: int) -> int:
    target = max(5, duration_seconds * fps)
    n = round((target - 1) / 4)
    return max(5, 4 * n + 1)


def resolve_size(width: int, height: int) -> str:
    exact = config.ALLOWED_SIZES.get((width, height))
    if exact:
        return exact
    return config.WAN_DEFAULT_SIZE


def resolve_seed(seed: int) -> int:
    if seed >= 0:
        return seed
    return random.randint(0, 2_147_483_647)


def build_generate_command(
    *,
    prompt: str,
    width: int,
    height: int,
    duration_seconds: int,
    fps: int,
    steps: int,
    cfg: float,
    seed: int,
    save_file: Path,
) -> list[str]:
    generate_script = config.WAN_ROOT / "generate.py"
    if not generate_script.exists():
        raise FileNotFoundError(
            f"Official Wan generate.py not found at {generate_script}"
        )

    cmd = [
        sys.executable,
        str(generate_script),
        "--task",
        config.WAN_TASK,
        "--size",
        resolve_size(width, height),
        "--ckpt_dir",
        str(config.WAN_CKPT_DIR),
        "--prompt",
        prompt,
        "--save_file",
        str(save_file),
        "--base_seed",
        str(resolve_seed(seed)),
        "--sample_steps",
        str(steps),
        "--sample_guide_scale",
        str(cfg),
        "--frame_num",
        str(frames_for_duration(duration_seconds, fps)),
    ]

    if config.WAN_OFFLOAD_MODEL:
        cmd.extend(["--offload_model", "True"])
    if config.WAN_CONVERT_MODEL_DTYPE:
        cmd.append("--convert_model_dtype")
    if config.WAN_T5_CPU:
        cmd.append("--t5_cpu")

    return cmd


def run_generation(
    *,
    prompt: str,
    width: int,
    height: int,
    duration_seconds: int,
    fps: int,
    steps: int,
    cfg: float,
    seed: int,
    save_file: Path,
) -> Path:
    config.WAN_CKPT_DIR.mkdir(parents=True, exist_ok=True)
    save_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = build_generate_command(
        prompt=prompt,
        width=width,
        height=height,
        duration_seconds=duration_seconds,
        fps=fps,
        steps=steps,
        cfg=cfg,
        seed=seed,
        save_file=save_file,
    )

    result = subprocess.run(
        cmd,
        cwd=str(config.WAN_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise RuntimeError(f"Wan generation failed: {stderr}")

    if not save_file.exists():
        raise RuntimeError(
            f"Wan generation finished but output file is missing: {save_file}"
        )

    return save_file
