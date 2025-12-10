# Harvard Voice Assistant

Simple speech-to-speech AI assistant with RAG (Retrieval-Augmented Generation).

## 🎯 Workflow

```
Browser (Your Voice)
    ↓
STT (Speech-to-Text) - Deepgram
    ↓
RAG (Retrieval) - Qdrant + OpenRouter Embeddings
    ↓
LLM (Answer) - OpenAI/Groq
    ↓
TTS (Text-to-Speech) - OpenAI
    ↓
Browser (Assistant Voice)
```

## 📦 Requirements

- Python 3.11+
- Qdrant (vector database)
- LiveKit server (local or cloud)
- API keys: Deepgram, OpenAI, OpenRouter, Groq

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Environment

Edit `.env` file:

```bash
# API Keys - GET THESE FROM:
# Deepgram: https://deepgram.com (for STT)
# OpenAI: https://openai.com (for LLM and TTS)
# OpenRouter: https://openrouter.ai (for embeddings)
# Groq: https://groq.com (alternative LLM)

DEEPGRAM_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
GROQ_API_KEY=your_key_here

# LiveKit (local or cloud)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=harvardkey
LIVEKIT_API_SECRET=harvard_secret_key_2024xyz

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=harvard
```

### 3. Start Qdrant

```bash
docker run -d -p 6333:6333 qdrant/qdrant
```

### 4. Start LiveKit (if using local)

```bash
docker run -d -p 7880:7880 livekit/livekit-server --dev
```

Or use LiveKit Cloud: https://cloud.livekit.io

### 5. Start Token Server

```bash
python server.py
```

Expected output:
```
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 6. Start Voice Agent

Open a NEW terminal:

```bash
python main.py dev
```

Expected output:
```
INFO - registered worker
INFO - Agent starting...
```

### 7. Open Browser Client

Open `test_client.html` in your browser:

```bash
open test_client.html
```

Click "اتصل وابدأ الحديث" (Connect) and start speaking!

## 📁 Files

- `main.py` - Voice agent (STT → RAG → LLM → TTS)
- `server.py` - Token generation server
- `test_client.html` - Web interface
- `config.py` - Configuration
- `stt.py` - Speech-to-text (not used with pipeline)
- `rag.py` - RAG retrieval with Qdrant
- `llm.py` - LLM interface (not used with pipeline)
- `tts.py` - Text-to-speech (not used with pipeline)

## 🎤 How It Works

1. **You speak** in the browser
2. **Deepgram STT** transcribes your voice to text
3. **RAG** searches Qdrant for relevant Harvard info
4. **OpenAI LLM** generates a French response
5. **OpenAI TTS** converts text to speech
6. **You hear** the assistant's response

## 🧪 Testing

### Test Token Generation

```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"room_name":"test","participant_name":"user"}'
```

### Test Qdrant

```bash
curl http://localhost:6333/health
```

## 🔧 Troubleshooting

### "Token generation failed"
- Make sure `server.py` is running
- Check http://localhost:8000/health

### "Connection failed"
- Make sure LiveKit server is running
- Check LiveKit URL in `.env`

### "No voice response"
- Make sure `main.py` agent is running
- Check API keys in `.env`
- Look at terminal logs for errors

### "Can't hear greeting"
- Allow microphone access in browser
- Check browser console for errors
- Make sure you're using HTTPS (or localhost)

## 📚 Add Documents to Qdrant

```python
import asyncio
from rag import get_rag

async def add_docs():
    rag = get_rag()

    docs = [
        "Harvard University was founded in 1636 in Cambridge, Massachusetts.",
        "Harvard is the oldest university in the United States.",
    ]

    for i, doc in enumerate(docs):
        emb = await rag.get_embedding(doc)
        rag.qdrant_client.upsert(
            collection_name="harvard",
            points=[{
                "id": i + 1,
                "vector": emb,
                "payload": {"text": doc}
            }]
        )
    print("✅ Documents added!")

asyncio.run(add_docs())
```

## 🌐 Production

For production:
1. Use LiveKit Cloud
2. Deploy `server.py` on a server
3. Deploy `main.py` agent on a server
4. Host `test_client.html` on web hosting
5. Use HTTPS for all services

## 📝 License

MIT
