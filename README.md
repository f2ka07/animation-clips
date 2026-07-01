# wan-stick-clips

Local CLI tool for generating reusable 5-second stick figure psychology clips via a configurable video provider. Clips are labelled, indexed, and searchable for reuse in a YouTube channel called "The Psychology of".

## Architecture

```
generate_clip.py
        |
        v
  VideoProvider  (PROVIDER in .env)
        |
   +----+----+----+----+
   |         |    |    |
   AWS   Minimax Runpod Fal   (future providers)
```

Each provider is self-contained under `providers/`. Switch backends by setting `PROVIDER` in `.env` only — the CLI, payload builder, and library code stay the same.

Model selection is also configuration-only:

```
MODEL_FAMILY=wan
MODEL_NAME=wan2.2
MODEL_TASK=t2v
MODEL_VERSION=v43
```

Switching to `wan3`, `hunyuanvideo`, `ltx`, or another family is an `.env` change, not a code change.

## Requirements

- Python 3.11
- An AWS **EC2 g5.xlarge** (or similar GPU instance) running the `server/` Wan 2.2 container

## Quick start

1. Deploy your WAN video API on AWS (see below).
2. Configure `.env`.
3. Install dependencies.
4. Generate a test clip.

```bash
cd D:\VideoApp\wan-stick-clips
copy .env.example .env
```

Edit `.env` and set at minimum `PROVIDER=aws`, `AWS_MODE`, `API_HOST` (REST), or `AWS_SAGEMAKER_ENDPOINT_NAME` (SageMaker).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

```bash
python generate_clip.py --title "Avoiding Work" --category "procrastination" --tags "delay,work,phone,avoidance" --action "A stick figure sits at a desk with a notebook. The figure looks at the work, hesitates, notices a phone, picks it up, smiles while scrolling, then looks worried as a clock appears in the background."
```

On Linux/macOS, use `cp .env.example .env` and `source .venv/bin/activate` instead.

## AWS endpoint setup

We ship our own inference server in `server/`, built around the [official Wan 2.2 code](https://github.com/Wan-Video/Wan2.2) with a lightweight FastAPI wrapper. This replaces community Docker images (for example `docker.io/antilopax/wan22:v43`) with a stable API that matches this project's `.env` defaults.

See **[server/README.md](server/README.md)** for build and deploy steps.

Summary:

1. Launch an **EC2 g5.xlarge** GPU instance.
2. Build the Docker image from `server/`.
3. Download **Wan2.2-TI2V-5B** weights (fits the A10G 24 GB GPU).
4. Run the container on the instance.
5. Point the CLI `.env` at the instance public DNS.

**Note:** ComfyUI templates are allowed only for manual visual testing. This production stack uses our FastAPI server around official Wan 2.2 inference.

### REST mode (default) - g5.xlarge with our Wan server

Set in `.env`:

```
PROVIDER=aws
AWS_MODE=rest
AWS_REGION=us-east-1
API_PROTOCOL=https
API_HOST=ec2-xx-xx-xx-xx.compute.amazonaws.com
API_PORT=8000
API_GENERATE_PATH=/generate
API_STATUS_PATH=/status
```

The client posts to:

`{API_PROTOCOL}://{API_HOST}:{API_PORT}{API_GENERATE_PATH}`

Status polling uses:

`{API_PROTOCOL}://{API_HOST}:{API_PORT}{API_STATUS_PATH}/{job_id}`

For API Gateway with a key:

```
USE_AUTH_HEADER=true
AUTH_HEADER_NAME=x-api-key
API_AUTH_TOKEN=your_api_gateway_key
```

### SageMaker mode (optional alternative)

Set in `.env`:

```
PROVIDER=aws
AWS_MODE=sagemaker
AWS_REGION=us-east-1
AWS_SAGEMAKER_ENDPOINT_NAME=wan-t2v-endpoint
```

Credentials use `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` if set, otherwise the default boto3 credential chain (IAM role, `~/.aws/credentials`, etc.).

### Video output formats

Your worker can return any of:

```json
{ "video_url": "https://..." }
```

```json
{ "video_base64": "..." }
```

```json
{ "video_s3_uri": "s3://bucket/path/clip.mp4" }
```

Field names are configurable via `VIDEO_URL_FIELD`, `VIDEO_BASE64_FIELD`, and `VIDEO_S3_FIELD`.

## MiniMax provider

Use hosted MiniMax video generation without a GPU server. Set `PROVIDER=minimax` and add your API key:

```
PROVIDER=minimax
MINIMAX_API_KEY=your_api_key_here
```

Optional:

```
MINIMAX_API_BASE=https://api.minimax.io/v1
MINIMAX_MODEL=MiniMax-Hailuo-2.3
MINIMAX_RESOLUTION=768P
```

The provider maps the standard CLI payload (`prompt`, `width`, `height`, `duration_seconds`, etc.) to the [MiniMax video API](https://platform.minimax.io/docs/guides/video-generation). No `API_HOST`, `AWS_MODE`, or Runpod settings are required.

China mainland base URL: `https://api.minimaxi.com/v1`

## Runpod (legacy provider)

To use Runpod instead of AWS, set `PROVIDER=runpod` and configure `RUNPOD_MODE`, `RUNPOD_API_KEY`, and `RUNPOD_ENDPOINT_ID` (serverless) or `API_HOST` (pod). See commented variables at the bottom of `.env.example`.

The project loads `RUNPOD_API_KEY` from `wan-stick-clips/.env` or the parent `D:\VideoApp\.env` automatically.

### MiniMax Hailuo on RunPod (recommended for hosted generation)

Matches the curl in `D:\VideoApp\API`:

```env
PROVIDER=runpod
RUNPOD_MODE=serverless
RUNPOD_ENDPOINT_ID=minimax-hailuo-02-std
RUNPOD_PAYLOAD_PROFILE=minimax_hailuo
DURATION_FIELD=duration
MINIMAX_HAILUO_ENABLE_PROMPT_EXPANSION=false
```

Response uses `output.result` as the MP4 URL (set `VIDEO_URL_FIELD=result`). Duration is sent as `6` or `10` (MiniMax Hailuo accepts those values).

```bash
python generate_clip.py --title "Desk Stare" --category work --tags "office,focus" \
  --setting office --duration 6 \
  --action "Stick figure opens laptop, stares at screen, then slumps slightly."
```

### Scene pipeline (T2I master + I2V clip) — matches `D:\VideoApp\API`

Three RunPod endpoints, one API key from `.env`, prompts from `data/scenes.json`:

| Step | Endpoint | CLI |
|------|----------|-----|
| Master still image | `seedream-v4-t2i` | `generate_master.py` |
| Animate master | `kling-v2-1-i2v-pro` | `generate_scene_clip.py` |
| Direct text-to-video | `minimax-hailuo-02-std` | `generate_clip.py` |

```env
RUNPOD_API_KEY=...          # D:\VideoApp\.env
RUNPOD_T2I_ENDPOINT_ID=seedream-v4-t2i
RUNPOD_I2V_ENDPOINT_ID=kling-v2-1-i2v-pro
RUNPOD_T2V_ENDPOINT_ID=minimax-hailuo-02-std
SEEDREAM_SIZE=1280*720
VIDEO_URL_FIELD=result
IMAGE_URL_FIELD=result
```

**1. Generate master PNG** (prompt built from scene record in JSON):

```bash
python generate_master.py --scene office_two_people_meeting --dry-run
python generate_master.py --scene office_two_people_meeting
```

Saves `masters/office_two_people_meeting.png` and registers the RunPod image URL in `data/scene_assets.json`.

**2. Animate master** (action from JSON `example_actions` or `--action`):

```bash
python generate_scene_clip.py --scene office_two_people_meeting --action-index 0 --dry-run
python generate_scene_clip.py --scene office_two_people_meeting --action-index 0 --duration 5
```

**3. Batch missing masters:**

```bash
python generate_master.py --all-missing
```

### Configurable request payload

Field names are fully configurable in `.env`. The default serverless payload maps to:

```json
{
  "input": {
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
}
```

If your worker expects different names (for example `text` instead of `prompt`, or `num_steps` instead of `steps`), update the `*_FIELD` variables in `.env` without changing Python code.

Example for an alternate API:

```
PROMPT_FIELD=text
STEPS_FIELD=num_steps
REQUEST_WRAPPER_KEY=
```

An empty `REQUEST_WRAPPER_KEY` sends the payload directly without an `input` wrapper.

### Expected response

Your worker should return either:

```json
{ "output": { "video_url": "https://..." } }
```

or:

```json
{ "output": { "video_base64": "..." } }
```

Response field names are also configurable via `OUTPUT_FIELD`, `VIDEO_URL_FIELD`, and `VIDEO_BASE64_FIELD`.

Switching images (for example from `docker.io/antilopax/wan22:v43` to a future WAN build) is usually a matter of updating `.env`, not code.

## Local setup

From the project root:

```bash
cd D:\VideoApp\wan-stick-clips
copy .env.example .env
```

Open `.env` and set connection values for your deployment. Minimum for AWS REST:

```
PROVIDER=aws
AWS_MODE=rest
API_HOST=ec2-xx-xx-xx-xx.compute.amazonaws.com
API_PORT=8000
```

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Generate one clip

```bash
python generate_clip.py ^
  --title "Avoiding Work" ^
  --category "procrastination" ^
  --tags "delay,work,phone,avoidance" ^
  --action "A stick figure sits at a desk with a notebook. The figure looks at the work, hesitates, notices a phone, picks it up, smiles while scrolling, then looks worried as a clock appears in the background."
```

Single-line version:

```bash
python generate_clip.py --title "Avoiding Work" --category "procrastination" --tags "delay,work,phone,avoidance" --action "A stick figure sits at a desk with a notebook. The figure looks at the work, hesitates, notices a phone, picks it up, smiles while scrolling, then looks worried as a clock appears in the background."
```

On Linux/macOS, replace `^` with `\` for line continuation.

The MP4 is saved under `outputs/` with a filename like `procrastination_avoiding_work_YYYYMMDD_HHMMSS.mp4` and indexed in `data/clips_index.json`.

## Quality workflow

Quality is enforced at three stages:

1. **Prompt design** — atomic beats, Background + Action format, `--setting` for reusable backgrounds ([PROMPT.md](PROMPT.md)).
2. **Preflight** — `quality.preflight_clip()` runs before every API call; errors block unless you pass `--force`.
3. **Human review** — completed clips stay `pending_review` until you approve them; only approved clips resolve in recipes.

**Dry-run (no API cost):**

```bash
python generate_clip.py --title "Test" --category work --tags test \
  --setting office --duration 6 --dry-run \
  --action "Stick figure opens laptop and stares at blank screen."
```

**Review after watching the MP4:**

```bash
python library.py --pending-review
python library.py --approve --title "Desk Stare" --clip-category work
python compose_recipe.py --recipe why_we_procrastinate
```

`compose_recipe.py` shows `pending_review` in yellow and only stitches **approved** clips.

### Character consistency

Every prompt includes a locked **Character:** block (round head, dot eyes, stick limbs, same line weight). Actions are rewritten to **"The same stick figure protagonist"**. Approve clips that match your golden look; reject drift. Optional override in `.env`:

```env
CHARACTER_DESCRIPTION=Your refined protagonist wording after you approve a golden clip.
```

MiniMax Hailuo has no reference-image or seed control in this API — language + review is the standard.

## Generate batch clips

`data/clip_specs.json` contains 20 starter psychology clips.

```bash
python batch_generate.py
```

Batch behavior:

- Skips clips that already exist with the same **title + category** and `status: completed`
- Retries failed clips on the next batch run
- Retries up to 2 times per clip during a single batch (3 attempts total)
- Continues even if one clip fails
- Writes failures to `logs/batch_failures_<timestamp>.json`

## Clip scripting (5–10 second reusable atoms)

Clips are designed to be **stitched into longer videos**. See [PROMPT.md](PROMPT.md) for the full scripting system.

**Build a new script entry:**

```bash
python script_builder.py --title "Morning Snooze" --category habit --tags "sleep,morning,bed" --setting bed --beat trigger --motion "An alarm clock appears. The figure reaches to turn it off and pulls the blanket back up." --emotion-change "The figure curls back into bed."
```

**Plan a video from existing clips:**

```bash
python compose_recipe.py --list
python compose_recipe.py --recipe why_we_procrastinate
```

**Per-clip duration (5–10 seconds):**

```bash
python generate_clip.py --title "..." --category "..." --tags "..." --duration 10 --action "..."
```

## Search the library

```bash
python library.py --tag delay
python library.py --category procrastination
python library.py --title "Avoiding Work"
python library.py --pending-review
python library.py --approved
python library.py --approve --title "Avoiding Work" --clip-category procrastination
```

## Configuration

All generation behavior is driven by `.env`. No URLs, JSON field names, model families, or provider details are hardcoded in Python.

### Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVIDER` | `aws` | Video provider backend (`aws`, `minimax`, `runpod`) |

### MiniMax connection

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIMAX_API_KEY` | | API key (required when `PROVIDER=minimax`) |
| `MINIMAX_API_BASE` | `https://api.minimax.io/v1` | API base URL |
| `MINIMAX_MODEL` | `MiniMax-Hailuo-2.3` | MiniMax video model |
| `MINIMAX_RESOLUTION` | | Override resolution (`720P`, `768P`, `1080P`); auto from height if empty |
| `MINIMAX_PROMPT_OPTIMIZER` | `true` | Enable MiniMax prompt optimization |

### AWS connection

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_MODE` | `rest` | `rest` (EC2/ALB/API Gateway) or `sagemaker` |
| `AWS_REGION` | `us-east-1` | AWS region |
| `AWS_ACCESS_KEY_ID` | | Optional; uses boto3 default chain if empty |
| `AWS_SECRET_ACCESS_KEY` | | Optional |
| `AWS_SESSION_TOKEN` | | Optional |
| `AWS_SAGEMAKER_ENDPOINT_NAME` | | SageMaker endpoint name |

### Generic API connection (AWS REST, Runpod pod)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PROTOCOL` | `http` | Transport protocol (`http`, `https`) |
| `API_HOST` | | API hostname (EC2 DNS, ALB, API Gateway) |
| `API_PORT` | `8000` | API port |
| `API_AUTH_TOKEN` | | Optional bearer or API key token |

Legacy `POD_HOST`, `POD_PORT`, and `POD_SCHEME` are accepted as fallbacks.

### Runpod connection (legacy)

| Variable | Default | Description |
|----------|---------|-------------|
| `RUNPOD_API_KEY` | | API key (serverless) |
| `RUNPOD_MODE` | `serverless` | `serverless` or `pod` |
| `RUNPOD_ENDPOINT_ID` | | Serverless endpoint ID |
| `SERVERLESS_BASE_URL` | `https://api.runpod.ai/v2` | Serverless API base URL |

### API paths

| Variable | Default | Description |
|----------|---------|-------------|
| `API_TYPE` | `rest` | API transport type |
| `API_GENERATE_PATH` | `/generate` | Generate path |
| `API_STATUS_PATH` | `/status` | Status path prefix |
| `AUTH_HEADER_NAME` | `Authorization` | Auth header name |
| `AUTH_HEADER_PREFIX` | `Bearer` | Auth header prefix |
| `USE_AUTH_HEADER` | `false` | Send auth header when token is set |
| `REQUEST_WRAPPER_KEY` | | Wrap payload key; empty = no wrapper |
| `POLLING_ENABLED` | `true` | Poll for async jobs; `false` for sync APIs |

### Response mapping

| Variable | Default |
|----------|---------|
| `JOB_ID_FIELD` | `id` |
| `STATUS_FIELD` | `status` |
| `OUTPUT_FIELD` | `output` |
| `ERROR_FIELD` | `error` |
| `STATUS_COMPLETED` | `COMPLETED` |
| `STATUS_FAILED` | `FAILED` |
| `STATUS_IN_QUEUE` | `IN_QUEUE` |
| `STATUS_IN_PROGRESS` | `IN_PROGRESS` |
| `VIDEO_URL_FIELD` | `video_url` |
| `VIDEO_BASE64_FIELD` | `video_base64` |
| `VIDEO_S3_FIELD` | `video_s3_uri` |

### Model metadata

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_FAMILY` | `wan` | Model family (`wan`, `hunyuanvideo`, `ltx`, etc.) |
| `MODEL_BACKEND` | `wan` | Alias for `MODEL_FAMILY` |
| `MODEL_NAME` | `wan2.2` | Specific model name |
| `MODEL_TASK` | `t2v` | Task type (`t2v`, `i2v`, etc.) |
| `MODEL_VERSION` | `v43` | Model version or image tag |
| `MODEL_INCLUDE_IN_PAYLOAD` | `false` | Send model fields in the request body |
| `MODEL_FAMILY_FIELD` | `model_family` | Payload key for family |
| `MODEL_NAME_FIELD` | `model_name` | Payload key for name |
| `MODEL_TASK_FIELD` | `model_task` | Payload key for task |
| `MODEL_VERSION_FIELD` | `model_version` | Payload key for version |

Legacy `MODEL_VARIANT` and `MODEL_VARIANT_FIELD` are accepted as fallbacks for `MODEL_TASK`.

### Request field mapping

| Variable | Default |
|----------|---------|
| `PROMPT_FIELD` | `prompt` |
| `NEGATIVE_PROMPT_FIELD` | `negative_prompt` |
| `WIDTH_FIELD` | `width` |
| `HEIGHT_FIELD` | `height` |
| `FPS_FIELD` | `fps` |
| `DURATION_FIELD` | `duration_seconds` |
| `STEPS_FIELD` | `steps` |
| `CFG_FIELD` | `cfg` |
| `SEED_FIELD` | `seed` |

### Video defaults

| Variable | Default |
|----------|---------|
| `WIDTH` | `832` |
| `HEIGHT` | `480` |
| `FPS` | `16` |
| `DURATION` | `5` |
| `STEPS` | `25` |
| `CFG` | `5` |
| `SEED` | `-1` |

Legacy names `DEFAULT_WIDTH`, `DEFAULT_HEIGHT`, etc. are still accepted as fallbacks.

### Polling and local paths

| Variable | Default |
|----------|---------|
| `POLL_INTERVAL` | `5` |
| `TIMEOUT` | `600` |
| `OUTPUT_DIR` | `outputs` |
| `CLIP_INDEX` | `data/clips_index.json` |

Batch max retries per clip: 2 (in `batch_generate.py`).

## Clip status values

Each indexed clip uses one of:

- `pending`
- `running`
- `completed`
- `failed`

## Project layout

```
wan-stick-clips/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── config.py
├── providers/
│   ├── __init__.py      # create_video_provider()
│   ├── base.py          # VideoProvider interface
│   ├── aws.py           # AWS REST + SageMaker
│   ├── minimax.py       # MiniMax hosted API
│   └── runpod.py        # Runpod (legacy)
├── prompts.py
├── generate_clip.py
├── batch_generate.py
├── library.py
├── server/              # Wan 2.2 FastAPI inference (Docker, deploy on AWS GPU)
│   ├── Dockerfile
│   ├── README.md
│   └── app/
├── data/
│   ├── clip_specs.json
│   └── clips_index.json
├── outputs/
│   └── .gitkeep
└── logs/
    └── .gitkeep
```

Generated MP4s, logs, and `.env` are excluded from git. `outputs/.gitkeep` and `logs/.gitkeep` are kept so the folders exist in a fresh clone.
