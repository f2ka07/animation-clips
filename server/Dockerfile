FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV WAN_ROOT=/opt/wan
ENV OUTPUT_DIR=/data/videos

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /opt

# Pin a Wan 2.2 commit for reproducible builds. Override at build time if needed.
ARG WAN_GIT_REF=main
RUN git clone --depth 1 --branch "${WAN_GIT_REF}" \
    https://github.com/Wan-Video/Wan2.2.git /opt/wan

WORKDIR /opt/server

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r /opt/wan/requirements.txt \
    && pip install --no-cache-dir boto3

COPY app ./app

RUN mkdir -p /data/videos /models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
