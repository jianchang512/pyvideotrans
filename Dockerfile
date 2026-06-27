# ============================================================
# pyVideoTrans WebUI Dockerfile
#
# CPU:  docker build -t pyvideotrans-webui .
# GPU:  docker build --build-arg USE_CUDA=true -t pyvideotrans-webui:gpu .
# ============================================================

ARG USE_CUDA=false

FROM python:3.10-slim AS cpu-base
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04 AS gpu-base

FROM  AS final-base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT=7860
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV FONTCONFIG_PATH=/etc/fonts

WORKDIR /app



RUN apt-get update && apt-get install -y --no-install-recommends fontconfig fonts-noto-cjk  fonts-liberation fonts-dejavu wget xz-utils git libglib2.0-0 libgl1 libsm6 libxext6 libxrender-dev libxkbcommon-x11-0 libdbus-1-3 libsndfile1 python3-dev rubberband-cli libsndfile1-dev && wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && tar -Jxf ffmpeg-release-amd64-static.tar.xz && cp ffmpeg-*-static/ffmpeg /usr/local/bin/ && cp ffmpeg-*-static/ffprobe /usr/local/bin/ && rm -rf ffmpeg-* && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN git clone -b dev https://github.com/jianchang512/pyvideotrans.git .

RUN if [ "" = "true" ]; then echo ">>> CUDA" && uv pip install --system -r pyproject.toml --all-extras && uv pip install --system torch==2.7.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128 && uv pip install --system nvidia-cublas-cu12 nvidia-cudnn-cu12; else echo ">>> CPU" && uv pip install --system -r pyproject.toml --all-extras; fi

RUN rm -rf /root/.cache/uv /tmp/*

EXPOSE 7860

CMD ["python", "webui.py"]