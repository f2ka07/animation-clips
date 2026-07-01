from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    negative_prompt: str = ""
    width: int = Field(default=832, ge=64, le=4096)
    height: int = Field(default=480, ge=64, le=4096)
    duration_seconds: int = Field(default=5, ge=1, le=30)
    fps: int = Field(default=16, ge=1, le=60)
    steps: int = Field(default=25, ge=1, le=200)
    cfg: float = Field(default=5.0, ge=0.0, le=30.0)
    seed: int = Field(default=-1)


class GenerateResponse(BaseModel):
    id: str


class JobOutput(BaseModel):
    video_url: str | None = None
    video_base64: str | None = None
    video_s3_uri: str | None = None


class StatusResponse(BaseModel):
    status: str
    output: JobOutput | None = None
    error: str | None = None
