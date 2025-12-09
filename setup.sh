#!/bin/bash

# Setup script for local development

set -e

echo "🚀 Setting up Speech-to-Speech RAG Assistant (Local Development)"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python3 --version

# Create virtual environment
echo ""
echo "🔧 Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   Virtual environment already exists. Skipping..."
else
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Check if .env exists
echo ""
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "   ✅ .env file created. Please edit it with your API keys:"
    echo "      - GROQ_API_KEY"
    echo "      - OPENROUTER_API_KEY"
    echo "      - LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET"
    echo ""
    echo "   Then run: source venv/bin/activate && python main.py"
else
    echo "✅ .env file exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys: nano .env"
echo "2. Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant"
echo "3. Make sure LiveKit server is running (or use cloud LiveKit)"
echo "4. Run the application:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
