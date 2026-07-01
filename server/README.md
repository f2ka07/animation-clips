# Wan 2.2 inference server

Self-hosted FastAPI service built around the [official Wan 2.2 repository](https://github.com/Wan-Video/Wan2.2). It exposes a stable REST API that matches the `wan-stick-clips` CLI `.env` contract, so you are not tied to community Docker images such as `docker.io/antilopax/wan22:v43`.

The CLI app is not dockerized. Only the GPU inference server runs in Docker on AWS EC2.

## AWS EC2 g5.xlarge (recommended)

This project is tuned for **g5.xlarge**:

| Resource | g5.xlarge |
|----------|-----------|
| GPU | 1x NVIDIA A10G (24 GB VRAM) |
| vCPU | 4 |
| RAM | 16 GB |

**Recommended model:** `Wan2.2-TI2V-5B` with `WAN_T5_CPU=true`. It fits the A10G at `832*480` for 5-second stick-figure clips. `T2V-A14B` is too large for reliable inference on 24 GB VRAM.

### EC2 setup checklist

1. Launch **g5.xlarge** with a Deep Learning AMI (Ubuntu) or install NVIDIA drivers + Docker + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
2. Open inbound **TCP 8000** in the instance security group (or put an ALB in front).
3. Clone this repo on the instance and build the server image from `server/`.
4. Download TI2V-5B weights (see below).
5. Set `PUBLIC_BASE_URL` to the instance public DNS on port 8000.

```bash
# On the g5.xlarge instance
cd server
cp .env.example .env
# Edit PUBLIC_BASE_URL to your instance DNS

docker build -t wan-stick-server .

mkdir -p models
pip install huggingface_hub
huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./models/Wan2.2-TI2V-5B

docker run --gpus all \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/models:/models \
  -v $(pwd)/videos:/data/videos \
  wan-stick-server
```

Verify:

```bash
curl http://localhost:8000/health
```

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

Weights are not bundled in the image. On your **g5.xlarge** host, download TI2V-5B (default):

```bash
mkdir -p models
pip install huggingface_hub
huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir ./models/Wan2.2-TI2V-5B
```

`.env.example` already points at this model. No changes needed unless you move to a larger GPU instance.

For **g5.2xlarge or larger** (still 24 GB A10G per GPU, but more system RAM), the same TI2V-5B settings apply. For multi-GPU instances with 40 GB+ VRAM (for example g5.12xlarge), you may try T2V-A14B:

```bash
huggingface-cli download Wan-AI/Wan2.2-T2V-A14B --local-dir ./models/Wan2.2-T2V-A14B
```

```
WAN_TASK=t2v-A14B
WAN_CKPT_DIR=/models/Wan2.2-T2V-A14B
WAN_T5_CPU=true
```

## Run on AWS EC2 (GPU)

On **g5.xlarge**, use the command from the setup checklist above. Generic form:

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
