# Testing Guide - Speech-to-Speech RAG Assistant

Complete testing guide for your local LiveKit RAG system.

## 🎯 System Overview

Your system has 3 main components:
1. **LiveKit Server** (WebRTC) - Port 7880
2. **Qdrant** (Vector DB) - Port 6333
3. **Python Agent** (STT + RAG + LLM + TTS)

---

## ✅ Pre-Test Checklist

Make sure all services are running:

```powershell
# Check Podman containers
podman ps

# Should show:
# - livekit-server (running)
# - qdrant (running)

# Check Python agent
# Should see: "INFO - registered worker"
```

---

## 🧪 Test 1: Verify Services

### Test Qdrant

```powershell
# Health check
curl http://localhost:6333/health

# Expected: {"status":"ok"}

# Check collections
curl http://localhost:6333/collections
```

### Test LiveKit

```powershell
# Should respond (might show HTML)
curl http://localhost:7880
```

---

## 🧪 Test 2: Setup Qdrant Collection

Create the `harvard` collection:

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Create collection
python
```

In Python console:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

# Create collection
client.create_collection(
    collection_name="harvard",
    vectors_config=VectorParams(
        size=3072,
        distance=Distance.COSINE
    )
)

print("✅ Collection created!")

# Verify
collections = client.get_collections()
print(f"Collections: {[c.name for c in collections.collections]}")

exit()
```

---

## 🧪 Test 3: Add Test Documents to Qdrant

```powershell
python
```

```python
import asyncio
from qdrant_client import QdrantClient
from config import settings
from rag import get_rag

async def add_test_docs():
    rag = get_rag()
    client = rag.qdrant_client

    # Test documents about Harvard
    docs = [
        "Harvard University was founded in 1636 in Cambridge, Massachusetts.",
        "Harvard is the oldest institution of higher education in the United States.",
        "The Harvard Library system is the oldest library system in America.",
        "Harvard has produced 8 U.S. presidents and 188 living billionaires.",
        "The Harvard campus covers 209 acres in Cambridge."
    ]

    print("Adding documents to Qdrant...")
    for i, doc in enumerate(docs):
        # Get embedding
        embedding = await rag.get_embedding(doc)

        # Add to Qdrant
        client.upsert(
            collection_name="harvard",
            points=[{
                "id": i + 1,
                "vector": embedding,
                "payload": {"text": doc}
            }]
        )
        print(f"✅ Added doc {i+1}")

    # Verify
    count = client.count(collection_name="harvard")
    print(f"\n✅ Total documents: {count.count}")

asyncio.run(add_test_docs())
exit()
```

---

## 🧪 Test 4: Test RAG Retrieval

```python
import asyncio
from rag import get_rag

async def test_rag():
    rag = get_rag()

    # Test query
    query = "When was Harvard founded?"

    print(f"Query: {query}\n")

    # Retrieve documents
    docs = await rag.retrieve(query)

    print(f"Found {len(docs)} documents:\n")
    for i, doc in enumerate(docs, 1):
        print(f"{i}. {doc['text']}")
        print(f"   Score: {doc['score']:.4f}\n")

asyncio.run(test_rag())
exit()
```

---

## 🧪 Test 5: Test LLM

```python
import asyncio
from llm import get_llm

async def test_llm():
    llm = get_llm()

    # Test without context
    print("Testing LLM (no context):")
    response = await llm.get_response("Dis bonjour en français")
    print(f"Response: {response}\n")

    # Test with context
    context = "Harvard was founded in 1636 in Cambridge."
    print("Testing LLM (with context):")
    response = await llm.get_response(
        "When was Harvard founded?",
        context=context
    )
    print(f"Response: {response}")

asyncio.run(test_llm())
exit()
```

---

## 🧪 Test 6: Test Speech-to-Text (Whisper)

Create test audio file first or download a sample.

```python
from stt import get_stt

# Initialize (first time will download model)
stt = get_stt()
print("✅ Whisper loaded")

# Test with audio file
# transcription = stt.transcribe("path/to/audio.wav")
# print(f"Transcription: {transcription}")

exit()
```

---

## 🧪 Test 7: Test Text-to-Speech (Kokoro)

```python
from tts import get_tts

# Initialize TTS
tts = get_tts()
print("✅ Kokoro loaded")

# Test synthesis
text = "Bonjour, je suis l'assistant vocal de Harvard."
audio = tts.synthesize(text)

if audio:
    # Save to file
    with open("test_output.wav", "wb") as f:
        f.write(audio)
    print("✅ Audio saved to test_output.wav")
    print("Play it to verify!")

exit()
```

Play the file:
```powershell
# Windows Media Player
start test_output.wav
```

---

## 🧪 Test 8: Test Full Pipeline (Without LiveKit)

```python
import asyncio
from rag import get_rag
from llm import get_llm
from tts import get_tts

async def test_full_pipeline():
    rag = get_rag()
    llm = get_llm()
    tts = get_tts()

    # User question
    question = "Quand Harvard a-t-elle été fondée?"
    print(f"Question: {question}\n")

    # 1. RAG Retrieval
    docs = await rag.retrieve(question)
    context = rag.format_context(docs)
    print(f"Context retrieved: {len(docs)} documents\n")

    # 2. LLM Response
    response = await llm.get_response(question, context)
    print(f"LLM Response: {response}\n")

    # 3. TTS Synthesis
    audio = tts.synthesize(response)
    if audio:
        with open("pipeline_test.wav", "wb") as f:
            f.write(audio)
        print("✅ Full pipeline test complete!")
        print("Audio saved to pipeline_test.wav")

asyncio.run(test_full_pipeline())
exit()
```

---

## 🧪 Test 9: Test LiveKit Connection (Basic)

This requires a LiveKit client. Here's a simple HTML test:

**Create `test_client.html`:**

```html
<!DOCTYPE html>
<html>
<head>
    <title>LiveKit Test Client</title>
    <script src="https://unpkg.com/livekit-client/dist/livekit-client.umd.min.js"></script>
</head>
<body>
    <h1>LiveKit Voice Assistant Test</h1>
    <button id="connect">Connect & Start</button>
    <button id="disconnect">Disconnect</button>
    <div id="status">Not connected</div>

    <script>
        const connectBtn = document.getElementById('connect');
        const disconnectBtn = document.getElementById('disconnect');
        const status = document.getElementById('status');

        let room;

        connectBtn.onclick = async () => {
            try {
                // Generate token (you need to implement this server-side)
                const token = 'YOUR_TOKEN_HERE'; // Get from server

                room = new LivekitClient.Room();

                await room.connect('ws://localhost:7880', token);
                status.textContent = 'Connected!';

                // Publish microphone
                await room.localParticipant.setMicrophoneEnabled(true);

            } catch (e) {
                status.textContent = 'Error: ' + e.message;
            }
        };

        disconnectBtn.onclick = () => {
            if (room) {
                room.disconnect();
                status.textContent = 'Disconnected';
            }
        };
    </script>
</body>
</html>
```

---

## 🧪 Test 10: Generate LiveKit Token

Create `test_token.py`:

```python
from livekit import api
from config import settings

# Generate access token for testing
token = api.AccessToken(
    api_key=settings.LIVEKIT_API_KEY,
    api_secret=settings.LIVEKIT_API_SECRET
)

token.with_identity("test-user")
token.with_name("Test User")
token.with_grants(api.VideoGrants(
    room_join=True,
    room="test-room"
))

access_token = token.to_jwt()
print("Access Token:")
print(access_token)
```

Run:
```powershell
python test_token.py
```

Use this token in your HTML client.

---

## 📊 Expected Results

### ✅ Success Indicators:

1. **Qdrant**: Collection created, documents added
2. **RAG**: Retrieves relevant documents
3. **LLM**: Returns French responses
4. **Whisper**: Transcribes audio (first run downloads model)
5. **Kokoro**: Generates French speech audio
6. **LiveKit**: Agent connects and registers
7. **Full Pipeline**: Question → Context → Response → Audio

### ❌ Common Issues:

1. **API Key Errors**: Check `.env` file
2. **Model Download Slow**: Normal on first run
3. **Qdrant Connection**: Make sure container is running
4. **LiveKit 401**: Check API keys match

---

## 🎯 Complete Test Flow

```powershell
# 1. Start services
podman-compose up -d

# 2. Start agent
python main.py dev

# 3. In another terminal, run tests
.\venv\Scripts\Activate.ps1

# Test RAG
python -c "import asyncio; from rag import get_rag; asyncio.run(get_rag().retrieve('Harvard'))"

# Test LLM
python -c "import asyncio; from llm import get_llm; print(asyncio.run(get_llm().get_response('Bonjour')))"

# Test TTS
python -c "from tts import get_tts; get_tts().synthesize_to_file('Bonjour', 'test.wav')"
```

---

## 🚀 Next Steps

After all tests pass:
1. Build a proper web client
2. Add more documents to Qdrant
3. Improve prompts
4. Add conversation history
5. Deploy to production

---

## 📝 Notes

- First run: Models download (Whisper ~150MB, Kokoro ~50MB)
- Embeddings require internet (OpenRouter API)
- LLM requires internet (Groq API)
- Everything else is 100% local

---

**All tests passing? Your system is ready! 🎉**
