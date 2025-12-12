FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY speech_to_speech.py .
COPY config.py .
COPY client.html .
COPY .env .
COPY kokoro-v1.0.onnx .
COPY voices-v1.0.bin .

EXPOSE 8765

CMD ["python", "speech_to_speech.py"]