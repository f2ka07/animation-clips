import base64
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from app import config
from app.schemas import GenerateRequest, JobOutput
from app.wan_runner import run_generation


class JobState(str, Enum):
    IN_QUEUE = config.STATUS_IN_QUEUE
    IN_PROGRESS = config.STATUS_IN_PROGRESS
    COMPLETED = config.STATUS_COMPLETED
    FAILED = config.STATUS_FAILED


@dataclass
class Job:
    id: str
    request: GenerateRequest
    status: JobState = JobState.IN_QUEUE
    error: str | None = None
    output_path: Path | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_JOBS)

    def submit(self, request: GenerateRequest) -> str:
        job_id = str(uuid.uuid4())
        job = Job(id=job_id, request=request)
        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(self._run_job, job_id)
        return job_id

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _run_job(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is None:
            return

        self._set_status(job_id, JobState.IN_PROGRESS)
        output_path = config.OUTPUT_DIR / f"{job_id}.mp4"

        try:
            run_generation(
                prompt=job.request.prompt,
                width=job.request.width,
                height=job.request.height,
                duration_seconds=job.request.duration_seconds,
                fps=job.request.fps,
                steps=job.request.steps,
                cfg=job.request.cfg,
                seed=job.request.seed,
                save_file=output_path,
            )
            with self._lock:
                stored = self._jobs[job_id]
                stored.output_path = output_path
                stored.status = JobState.COMPLETED
        except Exception as exc:
            with self._lock:
                stored = self._jobs[job_id]
                stored.status = JobState.FAILED
                stored.error = str(exc)

    def _set_status(self, job_id: str, status: JobState) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].status = status

    def build_output(self, job: Job) -> JobOutput | None:
        if job.status != JobState.COMPLETED or job.output_path is None:
            return None

        if config.OUTPUT_MODE == "base64":
            encoded = base64.b64encode(job.output_path.read_bytes()).decode("ascii")
            return JobOutput(video_base64=encoded)

        if config.OUTPUT_MODE == "s3":
            if not config.AWS_S3_BUCKET:
                raise RuntimeError("OUTPUT_MODE=s3 requires AWS_S3_BUCKET")
            key = (
                f"{config.AWS_S3_PREFIX.strip('/')}/{job.output_path.name}"
                if config.AWS_S3_PREFIX
                else job.output_path.name
            )
            try:
                import boto3
            except ImportError as exc:
                raise RuntimeError(
                    "boto3 is required for OUTPUT_MODE=s3"
                ) from exc

            boto3.client("s3", region_name=config.AWS_REGION).upload_file(
                str(job.output_path),
                config.AWS_S3_BUCKET,
                key,
            )
            return JobOutput(video_s3_uri=f"s3://{config.AWS_S3_BUCKET}/{key}")

        base = config.PUBLIC_BASE_URL
        if not base:
            base = f"http://localhost:{config.SERVER_PORT}"
        video_url = f"{base}/videos/{job.output_path.name}"
        return JobOutput(video_url=video_url)


job_manager = JobManager()
