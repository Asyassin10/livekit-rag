# Simple RAG Pipeline Guide

## 🎯 Simple Flow

```
User speaks → Whisper (STT) → Text
                                 ↓
                         Search Qdrant (embeddings)
                                 ↓
                         Get relevant chunks
                                 ↓
                         Chunks + Question → LLM
                                 ↓
                         LLM Answer
                                 ↓
                         Kokoro TTS → Audio
                                 ↓
                         User hears response
```

---

## 📁 Files

### Core Components (Keep These)

1. **config.py** - Settings (API keys, models)
2. **stt.py** - Speech to Text (Whisper)
3. **rag.py** - RAG with Qdrant (embeddings + search)
4. **llm.py** - LLM (Groq streaming)
5. **tts.py** - Text to Speech (Kokoro)

### Simple Versions (Use These)

6. **simple_main.py** - Simple LiveKit agent
7. **test_pipeline.py** - Test without LiveKit

---

## 🚀 Quick Start

### Test the Pipeline (No LiveKit needed)

```powershell
# 1. Make sure Qdrant is running
podman ps  # Check qdrant container

# 2. Add test documents to Qdrant
python
```

```python
import asyncio
from rag import get_rag

async def add_docs():
    rag = get_rag()
    docs = [
        "Harvard University was founded in 1636 in Cambridge, Massachusetts.",
        "Harvard is the oldest university in the United States.",
        "Harvard has 12 schools offering undergraduate and graduate programs."
    ]

    for i, doc in enumerate(docs):
        emb = await rag.get_embedding(doc)
        rag.qdrant_client.upsert(
            collection_name="harvard",
            points=[{"id": i+1, "vector": emb, "payload": {"text": doc}}]
        )
    print("✅ Added documents")

asyncio.run(add_docs())
exit()
```

### Test the Full Flow

```powershell
python test_pipeline.py
```

This will:
1. Search Qdrant for "Quand Harvard a été fondée?"
2. Get relevant docs
3. Ask LLM with context
4. Generate French audio response
5. Save to `test_answer.wav`

---

## 🎤 With LiveKit (Full WebRTC)

### Run the Simple Agent

```powershell
python simple_main.py dev
```

Flow:
1. User speaks (WebRTC audio)
2. Whisper transcribes
3. Search Qdrant
4. Ask LLM with context
5. Generate speech
6. Send audio back (WebRTC)

---

## 📊 What Each Component Does

### 1. STT (stt.py)
- **Input**: Audio bytes
- **Output**: Text (French)
- **Model**: Faster-Whisper (small, int8)

### 2. RAG (rag.py)
- **Input**: Text question
- **Process**:
  - Convert text to embeddings (OpenRouter API)
  - Search Qdrant for similar vectors
  - Get top 3 matching documents
- **Output**: Context chunks (text)

### 3. LLM (llm.py)
- **Input**: Question + Context chunks
- **Process**: Send to Groq API
- **Output**: French answer

### 4. TTS (tts.py)
- **Input**: Text (French)
- **Output**: Audio bytes (WAV, 24kHz)
- **Model**: Kokoro (French voice)

---

## 🧪 Test Each Component

### Test RAG Only

```python
import asyncio
from rag import get_rag

async def test():
    rag = get_rag()
    docs = await rag.retrieve("Harvard founding")
    for doc in docs:
        print(f"- {doc['text']} ({doc['score']:.2f})")

asyncio.run(test())
```

### Test LLM Only

```python
import asyncio
from llm import get_llm

async def test():
    llm = get_llm()
    answer = await llm.get_response("Hello in French", "")
    print(answer)

asyncio.run(test())
```

### Test TTS Only

```python
from tts import get_tts

tts = get_tts()
audio = tts.synthesize("Bonjour, je suis Harvard")
with open("test.wav", "wb") as f:
    f.write(audio)
print("✅ Saved to test.wav")
```

---

## 🔧 Configuration

Edit `.env`:

```bash
# Required for LLM
GROQ_API_KEY=your_key

# Required for embeddings
OPENROUTER_API_KEY=your_key

# LiveKit (local)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=harvardkey
LIVEKIT_API_SECRET=harvard_secret_key_2024xyz

# Qdrant (local)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=harvard
```

---

## 📋 Checklist

- [ ] Podman running (LiveKit + Qdrant)
- [ ] .env configured with API keys
- [ ] Qdrant collection created
- [ ] Test documents added
- [ ] `test_pipeline.py` works
- [ ] `simple_main.py dev` connects

---

## 💡 Tips

1. **Test without LiveKit first** - Use `test_pipeline.py`
2. **Check each component** - Test STT, RAG, LLM, TTS separately
3. **Add your own documents** - Use the code above to add to Qdrant
4. **Adjust chunk size** - Edit RAG_TOP_K in config.py

---

## 🐛 Common Issues

### "No documents found"
- Add documents to Qdrant first
- Check collection name matches

### "API key error"
- Verify .env has correct keys
- Check GROQ_API_KEY and OPENROUTER_API_KEY

### "Model loading slow"
- First time downloads models
- Whisper: ~150MB
- Kokoro: ~50MB

---

## 🎯 That's It!

The flow is simple:
```
Speech → Text → RAG Search → LLM → Speech
```

All local except LLM and embeddings API calls.
