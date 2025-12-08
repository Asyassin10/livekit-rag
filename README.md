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
- **CPU Optimized**: INT8 quantization for weak VPS deployment

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

- Docker and Docker Compose
- Python 3.11+ (for local development)
- API Keys:
  - Groq API key (https://console.groq.com/)
  - OpenRouter API key (https://openrouter.ai/)
  - LiveKit credentials (auto-configured in docker-compose)

## Quick Start with Docker

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd livekit-rag

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Configure Environment Variables

Edit `.env` file:

```bash
# Required API Keys
GROQ_API_KEY=your_groq_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# LiveKit (default values work with docker-compose)
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=APIvKxLq9E7Gwbm
LIVEKIT_API_SECRET=SECRETkey123456789abcdefghijklmnop

# Qdrant (default values)
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=harvard
```

### 3. Start Services

```bash
# Start all services (LiveKit, Qdrant, RAG Assistant)
docker-compose up -d

# View logs
docker-compose logs -f rag-assistant
```

### 4. Verify Services

```bash
# Check health
curl http://localhost:8000/health

# Check LiveKit
curl http://localhost:7880

# Check Qdrant
curl http://localhost:6333/health
```

## Local Development Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Setup Qdrant Collection

```bash
# Start Qdrant only
docker-compose up -d qdrant

# Create collection and upload data
python scripts/setup_qdrant.py
```

### 3. Run Application

```bash
# Set environment variables
export $(cat .env | xargs)

# Run the agent
python main.py

# Or run with uvicorn for FastAPI only
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Project Structure

```
livekit-rag/
├── main.py                 # FastAPI app + LiveKit agent
├── config.py               # Configuration and settings
├── stt.py                  # Faster-Whisper speech-to-text
├── rag.py                  # Qdrant retrieval system
├── llm.py                  # Groq LLM streaming
├── tts.py                  # Kokoro TTS synthesis
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image
├── docker-compose.yml      # Multi-service orchestration
├── livekit-config.yaml     # LiveKit server configuration
├── .env.example            # Environment variables template
└── README.md               # This file
```

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

## API Endpoints

### Health Check
```bash
GET /health
```

### Root
```bash
GET /
```

### Webhook (LiveKit Events)
```bash
POST /webhook
```

## LiveKit Integration

### Connect to Room

```python
from livekit import api

# Generate access token
token = api.AccessToken(
    api_key="APIvKxLq9E7Gwbm",
    api_secret="SECRETkey123456789abcdefghijklmnop"
)

token.with_identity("user-id")
token.with_name("User Name")
token.with_grants(api.VideoGrants(
    room_join=True,
    room="my-room"
))

access_token = token.to_jwt()
```

### Client Connection (JavaScript)

```javascript
import { Room } from 'livekit-client';

const room = new Room();
await room.connect('ws://localhost:7880', accessToken);

// Publish microphone
const audioTrack = await room.localParticipant.createAudioTrack();
await room.localParticipant.publishTrack(audioTrack);
```

## Qdrant Setup

### Create Collection

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url="http://localhost:6333")

client.create_collection(
    collection_name="harvard",
    vectors_config=VectorParams(
        size=3072,  # openai/text-embedding-3-large
        distance=Distance.COSINE
    )
)
```

### Upload Documents

```python
# Upload with embeddings
client.upsert(
    collection_name="harvard",
    points=[
        {
            "id": 1,
            "vector": embedding_vector,
            "payload": {
                "text": "Document content...",
                "metadata": {}
            }
        }
    ]
)
```

## Performance Optimization

### For Weak VPS (CPU Only)

1. **Whisper INT8 Quantization**: Reduces memory and increases speed
2. **Streaming TTS**: Start speaking before LLM completes
3. **Model Caching**: Pre-download models to `/root/.cache`
4. **Resource Limits**: Configure in docker-compose.yml

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
```

### Recommended VPS Specs

- **Minimum**: 4 CPU cores, 4GB RAM
- **Recommended**: 8 CPU cores, 8GB RAM
- **Storage**: 20GB (for models)

## Troubleshooting

### Issue: Models Download Slowly

**Solution**: Pre-download models before deployment

```bash
# Run container once to download models
docker-compose run rag-assistant python -c "from stt import get_stt; get_stt()"
```

### Issue: Qdrant Connection Failed

**Solution**: Ensure Qdrant is running and collection exists

```bash
# Check Qdrant status
curl http://localhost:6333/collections/harvard
```

### Issue: LiveKit Connection Failed

**Solution**: Check firewall and port forwarding

```bash
# Test LiveKit server
curl http://localhost:7880
```

### Issue: High CPU Usage

**Solution**: Adjust model sizes and concurrency

- Use `tiny` or `base` Whisper model
- Reduce `RAG_TOP_K` value
- Limit concurrent sessions

## Production Deployment

### 1. Security Hardening

- Change default LiveKit API keys
- Use HTTPS/WSS for LiveKit
- Enable authentication
- Configure CORS properly

### 2. Scaling

- Use Redis for LiveKit multi-node setup
- Deploy Qdrant cluster
- Load balance with Nginx/Traefik
- Use external object storage for models

### 3. Monitoring

- Add Prometheus metrics
- Configure logging aggregation
- Setup health check alerts
- Monitor resource usage

### 4. Backup

- Backup Qdrant data regularly
- Store model weights externally
- Version control configuration

## System Prompt

The assistant uses this French system prompt:

```
Tu es l'assistant vocal de Harvard. Réponds en français, 1-2 phrases max.
Utilise uniquement le contexte fourni. Si pas d'info, dis: Je n'ai pas cette information.
```

## License

MIT License

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [repository-url]/wiki

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## Acknowledgments

- [LiveKit](https://livekit.io/) - WebRTC infrastructure
- [Faster-Whisper](https://github.com/guillaumekln/faster-whisper) - Speech recognition
- [Qdrant](https://qdrant.tech/) - Vector database
- [Groq](https://groq.com/) - Fast LLM inference
- [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) - Text-to-speech
