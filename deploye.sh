#!/bin/bash
set -e

echo "🎓 Harvard Assistant Deployment"

# Build and start
podman-compose build
podman-compose up -d

# Pull Ollama model
echo "📥 Pulling qwen2.5:7b model..."
podman exec ollama ollama pull qwen2.5:7b

echo ""
echo "✅ Done!"
echo "WebSocket: ws://localhost:8765"
echo "Qdrant:    http://localhost:6333/dashboard"