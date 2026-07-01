# Wan 2.2 inference server

Self-hosted FastAPI service built around the [official Wan 2.2 repository](https://github.com/Wan-Video/Wan2.2). It exposes a stable REST API that matches the `wan-stick-clips` CLI `.env` contract, so you are not tied to community Docker images such as `docker.io/antilopax/wan22:v43`.

The CLI app is not dockerized. Only the GPU inference server runs in Docker on AWS (EC2, ECS, etc.).

## API contract

Matches the default CLI configuration:

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Health check |
| `POST /generate` | Submit a generation job |
| `GET /status/{id}` | Poll job status |
| `GET /videos/{filename}` | Download completed MP4 (`OUTPUT_MODE=url`) |

### POST /generate

```json
{
  "prompt": "...",
  "negative_prompt": "...",
  "width": 832,
  "height": 480,
  "duration_seconds": 5,
  "fps": 16,
  "steps": 25,
  "cfg": 5,
  "seed": -1
}
```

Response:

```json
{ "id": "job-uuid" }
```

### GET /status/{id}

```json
{
  "status": "COMPLETED",
  "output": {
    "video_url": "https://your-host:8000/videos/job-uuid.mp4"
  }
}
```

Status values: `IN_QUEUE`, `IN_PROGRESS`, `COMPLETED`, `FAILED`.

`negative_prompt` is accepted for API compatibility. The official Wan 2.2 `generate.py` CLI does not expose it today, so it is not passed through yet.

## Build the image

From this directory:

```bash
cd server
cp .env.example .env
docker build -t wan-stick-server .
```

Pin a specific Wan commit for reproducibility:

```bash
docker build --build-arg WAN_GIT_REF=<commit-sha> -t wan-stick-server .
```

## Download model weights

Weights are not bundled in the image. On your GPU host:

```bash
mkdir -p models
pip install huggingface_hub
huggingface-cli download Wan-AI/Wan2.2-T2V-A14B --local-dir ./models/Wan2.2-T2V-A14B
```

For smaller GPUs:

```bash
huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./models/Wan2.2-TI2V-5B
```

Then set in `.env`:

```
WAN_TASK=ti2v-5B
WAN_CKPT_DIR=/models/Wan2.2-TI2V-5B
WAN_T5_CPU=true
```

## Run on AWS EC2 (GPU)

```bash
docker run --gpus all \
  -p 8000:8000 \
  --env-file .env \
  -v /opt/models:/models \
  -v /opt/videos:/data/videos \
  wan-stick-server
```

Set `PUBLIC_BASE_URL` to the URL your CLI will use to download videos, for example:

```
PUBLIC_BASE_URL=http://ec2-xx-xx-xx-xx.compute.amazonaws.com:8000
```

## Wire up the CLI

In the project root `.env`:

```
PROVIDER=aws
AWS_MODE=rest
API_PROTOCOL=http
API_HOST=ec2-xx-xx-xx-xx.compute.amazonaws.com
API_PORT=8000
API_GENERATE_PATH=/generate
API_STATUS_PATH=/status
USE_AUTH_HEADER=true
API_AUTH_TOKEN=same-token-as-server
POLLING_ENABLED=true
```

If server and CLI use the same field names (defaults), no `*_FIELD` overrides are needed.

## Output modes

| `OUTPUT_MODE` | Result |
|---------------|--------|
| `url` | `video_url` pointing to `/videos/{id}.mp4` |
| `base64` | `video_base64` in the status response |
| `s3` | Upload to `AWS_S3_BUCKET` and return `video_s3_uri` |

## Official Wan mapping

| CLI field | Wan `generate.py` flag |
|-----------|------------------------|
| `prompt` | `--prompt` |
| `width` x `height` | `--size 832*480` |
| `steps` | `--sample_steps` |
| `cfg` | `--sample_guide_scale` |
| `seed` | `--base_seed` |
| `duration_seconds` + `fps` | `--frame_num` (nearest 4n+1) |

Supported sizes include `832*480`, `1280*720`, and others listed in the official Wan docs.
