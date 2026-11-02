FROM python:3.12-slim
# opencv (pulled in by ultralytics) needs these at import time
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# CPU torch: ~1 GB instead of the 4.4 GB CUDA build; only ingest is heavy
RUN pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt ultralytics==8.4.162 open_clip_torch==3.3.0 transformers==5.18.0
COPY . .
# model weights, images, .env and the Vertex key are mounted at run time (see ../docker-compose.yml)
EXPOSE 8001
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers", "--forwarded-allow-ips", "*"]
