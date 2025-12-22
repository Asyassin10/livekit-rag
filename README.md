# Voice AI Assistant

WebSocket-based speech-to-speech AI assistant with RAG for Harvard University queries.

## Stack

- **STT**: Whisper (faster-whisper)
- **RAG**: Qdrant + OpenRouter embeddings
- **LLM**: Qwen2.5 (via Ollama)
- **TTS**: Kokoro
- **Interface**: WebSocket + HTML client

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure `.env`:
```bash
GROQ_API_KEY=your_key
OPENROUTER_API_KEY=your_key
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=harvard
```

3. Start services:
```bash
# Qdrant
docker run -d -p 6333:6333 qdrant/qdrant

# Ollama with Qwen2.5
ollama pull qwen2.5:7b
```

4. Ingest data (optional):
```bash
python ingest_data.py
```

5. Run server:
```bash
python speech_to_speech.py
```

6. Open `client.html` in browser and start speaking!

## How It Works

1. Speak into microphone
2. Whisper transcribes audio → text
3. RAG retrieves relevant Harvard docs from Qdrant
4. Qwen2.5 generates French response
5. Kokoro synthesizes speech
6. Audio plays in browser

## Files

- `speech_to_speech.py` - Main WebSocket server
- `config.py` - Configuration
- `ingest_data.py` - Load documents into Qdrant
- `client.html` - Browser interface

## License

MIT
