FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app/raspberry

# System deps for OpenCV and GPIO
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    python3-rpi.gpio \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (cache-friendly)
COPY raspberry/requirements.txt /app/raspberry/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY raspberry /app/raspberry

# Default entrypoint runs RTSP pipeline; override with CMD for USB pipeline if needed
CMD ["python", "main.py"]
