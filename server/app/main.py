from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse

from app import config
from app.jobs import job_manager
from app.schemas import GenerateRequest, GenerateResponse, JobOutput, StatusResponse

app = FastAPI(
    title="wan-stick-clips inference server",
    description="Stable REST API around official Wan 2.2 text-to-video generation.",
    version="1.0.0",
)


def verify_auth(authorization: str | None = Header(default=None)) -> None:
    if not config.API_AUTH_TOKEN:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    prefix = "Bearer "
    token = (
        authorization[len(prefix) :]
        if authorization.startswith(prefix)
        else authorization
    )
    if token != config.API_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API token")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "wan_task": config.WAN_TASK,
        "wan_ckpt_dir": str(config.WAN_CKPT_DIR),
    }


@app.post("/generate", response_model=GenerateResponse)
def generate(
    request: GenerateRequest,
    _: None = Depends(verify_auth),
) -> GenerateResponse:
    if not config.WAN_CKPT_DIR.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Model checkpoint not found at {config.WAN_CKPT_DIR}. "
                "Mount weights before generating."
            ),
        )

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    job_id = job_manager.submit(request)
    return GenerateResponse(id=job_id)


@app.get("/status/{job_id}", response_model=StatusResponse)
def status(job_id: str, _: None = Depends(verify_auth)) -> StatusResponse:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    output: JobOutput | None = None
    if job.status.value == config.STATUS_COMPLETED:
        output = job_manager.build_output(job)

    return StatusResponse(
        status=job.status.value,
        output=output,
        error=job.error,
    )


@app.get("/videos/{filename}")
def download_video(filename: str) -> FileResponse:
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    path = config.OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(path, media_type="video/mp4", filename=filename)
