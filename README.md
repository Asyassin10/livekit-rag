# Speech-to-Speech RAG AI Assistant with LiveKit

A production-ready Python backend for a real-time voice assistant using LiveKit WebRTC, RAG (Retrieval-Augmented Generation), and French language support.

## Features

- **Real-time Voice Communication**: LiveKit WebRTC for low-latency audio streaming
- **Speech-to-Text**: Faster-Whisper with French language support and CPU optimization
- **RAG System**: Qdrant vector database for semantic search
- **Streaming LLM**: Groq API with llama-3.1-8b-instant model
- **Text-to-Speech**: Kokoro TTS with French voice (af_sarah)
- **Smart Conversation Detection**: Handles greetings, thanks, and goodbyes without RAG
- **Barge-in Support**: User can interrupt the assistant
- **CPU Optimized**: INT8 quantization for deployment

## Architecture

```
User Speech (WebRTC)
    ↓
Faster-Whisper STT (French)
    ↓
Conversation Detection
    ├─→ Greeting/Thanks/Goodbye → Direct Response
    └─→ Query → RAG Pipeline
                  ↓
              Qdrant Vector Search (OpenRouter Embeddings)
                  ↓
              Groq LLM (Streaming)
                  ↓
              Kokoro TTS (French)
                  ↓
            WebRTC Audio Stream
```

## Prerequisites

- Python 3.11+
- FFmpeg (for audio processing)
- API Keys:
  - Groq API key (https://console.groq.com/)
  - OpenRouter API key (https://openrouter.ai/)
  - LiveKit credentials (get from https://cloud.livekit.io or run local server)
- Qdrant running locally or remotely

## Quick Start

### Automated Setup (Recommended)

```bash
# 1. Clone the repository
git clone <repository-url>
cd livekit-rag

# 2. Run setup script
./setup.sh

# 3. Edit .env with your API keys
nano .env

# 4. Start Qdrant (in another terminal)
# Option A: Using Docker
docker run -p 6333:6333 qdrant/qdrant

# Option B: Download and run Qdrant binary
# See: https://qdrant.tech/documentation/quick-start/

# 5. Run the application
source venv/bin/activate
python main.py
```

### Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Setup environment variables
cp .env.example .env
nano .env  # Add your API keys

# 4. Run the application
python main.py
```

## Environment Configuration

Edit `.env` file with your credentials:

```bash
# Required API Keys
GROQ_API_KEY=your_groq_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# LiveKit Configuration
# Option 1: Use LiveKit Cloud (https://cloud.livekit.io)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Option 2: Use Local LiveKit Server
# LIVEKIT_URL=ws://localhost:7880
# LIVEKIT_API_KEY=devkey
# LIVEKIT_API_SECRET=secret

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=harvard

# Optional: Model Settings (defaults in config.py)
WHISPER_MODEL=small
WHISPER_LANGUAGE=fr
WHISPER_COMPUTE_TYPE=int8
```

## Project Structure

```
livekit-rag/
├── main.py              # FastAPI app + LiveKit agent
├── config.py            # Configuration and settings
├── stt.py               # Faster-Whisper speech-to-text
├── rag.py               # Qdrant retrieval system
├── llm.py               # Groq LLM streaming
├── tts.py               # Kokoro TTS synthesis
├── requirements.txt     # Python dependencies
├── setup.sh             # Automated setup script
├── .env.example         # Environment variables template
└── README.md            # This file
```

## System Requirements

### Minimum
- 4 CPU cores
- 4GB RAM
- 10GB disk space (for models)

### Recommended
- 8 CPU cores
- 8GB RAM
- 20GB disk space

### Dependencies
- Python 3.11+
- FFmpeg
- libsndfile1

### Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg libsndfile1
```

**macOS:**
```bash
brew install python@3.11 ffmpeg libsndfile
```

**Windows:**
- Install Python 3.11+ from python.org
- Install FFmpeg from ffmpeg.org
- Install libsndfile

## Configuration

### Model Settings

#### Speech-to-Text (Faster-Whisper)
- Model: `small` (French optimized)
- Compute Type: `int8` (CPU optimized)
- Language: French (`fr`)

#### Embeddings (OpenRouter)
- Model: `openai/text-embedding-3-large`
- Dimensions: 3072

#### LLM (Groq)
- Model: `llama-3.1-8b-instant`
- Temperature: 0.7
- Max Tokens: 150 (concise responses)

#### TTS (Kokoro)
- Voice: `af_sarah` (French female voice)
- Sample Rate: 24kHz
- Speed: 1.0x

### RAG Settings

- Collection: `harvard`
- Top-K: 3 documents
- Score Threshold: 0.7
- Embedding Dimension: 3072

### Conversation Detection Keywords

**Greetings**: bonjour, salut, hello, hey, coucou, bonsoir
**Thanks**: merci, merci beaucoup, je te remercie
**Goodbyes**: au revoir, bye, à bientôt, à plus, ciao

## Qdrant Setup

### 1. Start Qdrant

**Using Docker:**
```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage \
    qdrant/qdrant
```

**Using Binary:**
Download from https://qdrant.tech/documentation/quick-start/

### 2. Create Collection

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

# Create collection
client.create_collection(
    collection_name="harvard",
    vectors_config=VectorParams(
        size=3072,  # openai/text-embedding-3-large
        distance=Distance.COSINE
    )
)
```

### 3. Upload Documents

```python
# Get embeddings and upload
from rag import get_rag
import asyncio

async def upload_documents():
    rag = get_rag()

    documents = [
        "Harvard University was founded in 1636...",
        "The Harvard Library system is the oldest...",
        # Add your documents
    ]

    for i, doc in enumerate(documents):
        embedding = await rag.get_embedding(doc)
        rag.qdrant_client.upsert(
            collection_name="harvard",
            points=[{
                "id": i,
                "vector": embedding,
                "payload": {"text": doc}
            }]
        )

asyncio.run(upload_documents())
```

## Running the Application

### Start the LiveKit Agent

```bash
# Activate virtual environment
source venv/bin/activate

# Run the agent
python main.py
```

The agent will:
1. Connect to LiveKit server
2. Initialize AI models (Whisper, Kokoro)
3. Wait for participants to join rooms
4. Process audio streams in real-time

### Testing the Setup

```bash
# Test FastAPI endpoints
curl http://localhost:8000/health

# Test Qdrant
curl http://localhost:6333/health

# Test collection
curl http://localhost:6333/collections/harvard
```

## API Endpoints

### Health Check
```bash
GET http://localhost:8000/health
```

### Root
```bash
GET http://localhost:8000/
```

### Webhook (LiveKit Events)
```bash
POST http://localhost:8000/webhook
```

## LiveKit Integration

### Using LiveKit Cloud

1. Sign up at https://cloud.livekit.io
2. Create a project
3. Get API credentials
4. Update `.env` with your credentials

### Using Local LiveKit Server

Download and run LiveKit server:
```bash
# Download LiveKit server
wget https://github.com/livekit/livekit/releases/download/v1.5.3/livekit_1.5.3_linux_amd64.tar.gz
tar -xvf livekit_1.5.3_linux_amd64.tar.gz

# Create config file
cat > livekit.yaml <<EOF
port: 7880
rtc:
  port_range_start: 50000
  port_range_end: 50100
keys:
  devkey: secret
EOF

# Run server
./livekit-server --config livekit.yaml
```

## Troubleshooting

### Issue: ModuleNotFoundError

**Solution**: Make sure virtual environment is activated and dependencies installed
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: FFmpeg not found

**Solution**: Install FFmpeg
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### Issue: Qdrant Connection Failed

**Solution**: Ensure Qdrant is running
```bash
# Check Qdrant status
curl http://localhost:6333/health

# Start Qdrant if not running
docker run -p 6333:6333 qdrant/qdrant
```

### Issue: Models Download Slowly

**Solution**: Models download on first run. Be patient or pre-download:
```bash
python -c "from stt import get_stt; get_stt()"
python -c "from tts import get_tts; get_tts()"
```

### Issue: High CPU Usage

**Solution**: Adjust model sizes
- Use `tiny` or `base` Whisper model instead of `small`
- Reduce `RAG_TOP_K` in config
- Limit concurrent sessions

### Issue: LiveKit Connection Failed

**Solution**: Check your LiveKit configuration
- Verify URL format (ws:// or wss://)
- Check API key and secret
- Test LiveKit server connectivity

## Performance Optimization

### For CPU-Only Systems

1. **Whisper INT8 Quantization**: Already enabled (configured in config.py)
2. **Streaming TTS**: Starts speaking before LLM completes
3. **Model Caching**: Models cached after first download
4. **Batch Processing**: Adjust RAG_TOP_K for faster retrieval

### Reduce Memory Usage

```python
# In config.py, adjust:
WHISPER_MODEL = "tiny"  # or "base" instead of "small"
RAG_TOP_K = 2  # instead of 3
LLM_MAX_TOKENS = 100  # instead of 150
```

## System Prompt

The assistant uses this French system prompt:

```
Tu es l'assistant vocal de Harvard. Réponds en français, 1-2 phrases max.
Utilise uniquement le contexte fourni. Si pas d'info, dis: Je n'ai pas cette information.
```

## Development

### Run in Development Mode

```bash
# Activate venv
source venv/bin/activate

# Run with auto-reload
python main.py

# Or use uvicorn for FastAPI
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Add Custom Responses

Edit `config.py` to add custom conversation responses:

```python
GREETING_RESPONSES = [
    "Bonjour! Comment puis-je vous aider?",
    # Add your custom greetings
]
```

## License

MIT License

## Support

For issues and questions:
- GitHub Issues: <repository-url>/issues

## Acknowledgments

- [LiveKit](https://livekit.io/) - WebRTC infrastructure
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Speech recognition
- [Qdrant](https://qdrant.tech/) - Vector database
- [Groq](https://groq.com/) - Fast LLM inference
- [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) - Text-to-speech
