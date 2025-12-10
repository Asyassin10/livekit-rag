#!/bin/bash

# Start the FastAPI token server
# This provides the /token endpoint for the web client

echo "🚀 Starting FastAPI Token Server..."
echo "📍 Server will run on http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "To stop: Press Ctrl+C"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the server
python server.py
