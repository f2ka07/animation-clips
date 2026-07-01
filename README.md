# wan-stick-clips

Local CLI tool for generating reusable 5-second stick figure psychology clips via a configurable video provider. Clips are labelled, indexed, and searchable for reuse in a YouTube channel called "The Psychology of".

## Architecture

```
generate_clip.py
        |
        v
  VideoProvider  (PROVIDER in .env)
        |
   +----+----+----+
   |         |    |
 Runpod    Fal   Local   (future providers)
```

Each provider is self-contained under `providers/`. HTTP transport, polling, and response parsing for Runpod live in `providers/runpod.py`. Future providers such as `providers/fal.py` or `providers/local.py` follow the same pattern with no shared client layer.

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
- A Runpod account with a serverless text-to-video endpoint (WAN 2.2 or WAN 2.6 T2V compatible handler)

## Quick start

1. Set up a Runpod endpoint (see below).
2. Configure `.env`.
3. Install dependencies.
4. Generate a test clip.

```bash
cd D:\VideoApp\wan-stick-clips
copy .env.example .env
```

Edit `.env` and set at minimum `PROVIDER`, `RUNPOD_MODE`, and either `RUNPOD_ENDPOINT_ID` (serverless) or `POD_HOST` (pod).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

```bash
python generate_clip.py --title "Avoiding Work" --category "procrastination" --tags "delay,work,phone,avoidance" --action "A stick figure sits at a desk with a notebook. The figure looks at the work, hesitates, notices a phone, picks it up, smiles while scrolling, then looks worried as a clock appears in the background."
```

On Linux/macOS, use `cp .env.example .env` and `source .venv/bin/activate` instead.

## Runpod endpoint setup

You do not need a confirmed endpoint before cloning this project, but you will need one before generating clips.

1. Log in to [Runpod](https://www.runpod.io/) and deploy a **WAN 2.2 or WAN 2.6 T2V compatible handler** as either a **Pod** or **Serverless** endpoint.
2. Create an **API key** under your Runpod account settings.
3. Copy `.env.example` to `.env` and fill in the connection settings for your deployment mode.

**Note:** ComfyUI templates are allowed only for manual visual testing. This production CLI assumes a direct Runpod serverless or pod REST endpoint.

### Serverless mode (default)

Set in `.env`:

```
PROVIDER=runpod
RUNPOD_MODE=serverless
RUNPOD_API_KEY=your_api_key_here
RUNPOD_ENDPOINT_ID=your_endpoint_id_here
```

The client posts to:

`{SERVERLESS_BASE_URL}/{RUNPOD_ENDPOINT_ID}{API_GENERATE_PATH}`

Default: `https://api.runpod.ai/v2/{endpoint_id}/run`

Status polling uses:

`{SERVERLESS_BASE_URL}/{RUNPOD_ENDPOINT_ID}{API_STATUS_PATH}/{job_id}`

Default: `https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}`

### Pod mode

Set in `.env`:

```
PROVIDER=runpod
RUNPOD_MODE=pod
API_PROTOCOL=http
POD_HOST=xxx.runpod.net
POD_PORT=8000
API_GENERATE_PATH=/generate
API_STATUS_PATH=/status
```

The client posts to:

`{API_PROTOCOL}://{POD_HOST}:{POD_PORT}{API_GENERATE_PATH}`

`API_PROTOCOL` supports `http` and `https` for REST today. Values like `grpc` or `websocket` are reserved for future provider implementations.

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

Open `.env` and set connection values for your deployment. Minimum for serverless:

```
PROVIDER=runpod
RUNPOD_MODE=serverless
RUNPOD_API_KEY=your_api_key_here
RUNPOD_ENDPOINT_ID=your_endpoint_id_here
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

## Search the library

```bash
python library.py --tag delay
python library.py --category procrastination
python library.py --title "Avoiding Work"
```

## Configuration

All generation behavior is driven by `.env`. No URLs, JSON field names, model families, or provider details are hardcoded in Python.

### Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVIDER` | `runpod` | Video provider backend (`runpod` today; more later) |

### Connection (Runpod provider)

| Variable | Default | Description |
|----------|---------|-------------|
| `RUNPOD_API_KEY` | | API key (required for serverless) |
| `RUNPOD_MODE` | `serverless` | `serverless` or `pod` |
| `API_PROTOCOL` | `http` | Pod transport protocol (`http`, `https`) |
| `POD_HOST` | | Pod hostname |
| `POD_PORT` | `8000` | Pod port |
| `RUNPOD_ENDPOINT_ID` | | Serverless endpoint ID |
| `SERVERLESS_BASE_URL` | `https://api.runpod.ai/v2` | Serverless API base URL |

Legacy `POD_SCHEME` is accepted as a fallback for `API_PROTOCOL`.

### API paths

| Variable | Default | Description |
|----------|---------|-------------|
| `API_TYPE` | `rest` | API transport type |
| `API_GENERATE_PATH` | `/run` | Generate path (pod: often `/generate`) |
| `API_STATUS_PATH` | `/status` | Status path prefix |
| `AUTH_HEADER_NAME` | `Authorization` | Auth header name |
| `AUTH_HEADER_PREFIX` | `Bearer` | Auth header prefix |
| `USE_AUTH_HEADER` | `true` | Send auth header when key is set |
| `REQUEST_WRAPPER_KEY` | `input` | Wrap payload key; empty = no wrapper |
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
│   └── runpod.py        # Runpod HTTP transport + generation
├── prompts.py
├── generate_clip.py
├── batch_generate.py
├── library.py
├── data/
│   ├── clip_specs.json
│   └── clips_index.json
├── outputs/
│   └── .gitkeep
└── logs/
    └── .gitkeep
```

Generated MP4s, logs, and `.env` are excluded from git. `outputs/.gitkeep` and `logs/.gitkeep` are kept so the folders exist in a fresh clone.
