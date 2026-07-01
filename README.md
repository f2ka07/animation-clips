# wan-stick-clips

Local CLI tool for generating reusable 5-second stick figure psychology clips using Runpod text-to-video. Clips are labelled, indexed, and searchable for reuse in a YouTube channel called "The Psychology of".

## Requirements

- Python 3.11
- A Runpod account with a serverless text-to-video endpoint (WAN 2.6 T2V or compatible handler)

## Quick start

1. Set up a Runpod endpoint (see below).
2. Configure `.env`.
3. Install dependencies.
4. Generate a test clip.

```bash
cd D:\VideoApp\wan-stick-clips
copy .env.example .env
```

Edit `.env` and set `RUNPOD_API_KEY` and `RUNPOD_ENDPOINT_ID`.

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

1. Log in to [Runpod](https://www.runpod.io/) and open **Serverless**.
2. Create a new endpoint that runs a **WAN 2.6 text-to-video** worker (or any handler that accepts the input format below).
3. Deploy the endpoint and note the **Endpoint ID**.
4. Create an **API key** under your Runpod account settings.
5. Paste both values into `.env`.

The client sends this JSON body to `POST https://api.runpod.ai/v2/{endpoint_id}/run`:

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

Your worker should return either:

```json
{ "output": { "video_url": "https://..." } }
```

or:

```json
{ "output": { "video_base64": "..." } }
```

Adjust your Runpod handler if field names differ, but keep this project aligned with the format above.

## Local setup

From the project root:

```bash
cd D:\VideoApp\wan-stick-clips
copy .env.example .env
```

Open `.env` and set:

```
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

Defaults are in `.env.example`:

| Variable | Default |
|----------|---------|
| `OUTPUT_DIR` | `outputs` |
| `CLIP_INDEX` | `data/clips_index.json` |
| `DEFAULT_DURATION_SECONDS` | `5` |
| `DEFAULT_FPS` | `16` |
| `DEFAULT_WIDTH` | `832` |
| `DEFAULT_HEIGHT` | `480` |
| `DEFAULT_STEPS` | `25` |
| `DEFAULT_CFG` | `5` |
| `DEFAULT_SEED` | `-1` |

Runpod polling defaults (in `config.py`):

- Poll interval: 5 seconds
- Job timeout: 10 minutes
- Max retries per clip in batch: 2

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
├── runpod_client.py
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
