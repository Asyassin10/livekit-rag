# 🚀 Quick Start Guide

Get your LiveKit RAG system running in 3 simple steps!

---

## ⚡ Super Quick Start (3 Steps)

### Step 1: Start the FastAPI Server (Token Generation)

**Linux/Mac:**
```bash
./start_server.sh
```

**Windows:**
```powershell
start_server.bat
```

**Or manually:**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows PowerShell
.\venv\Scripts\activate.bat  # Windows CMD

# Run server
python server.py
```

You should see:
```
🚀 Starting FastAPI Token Server...
📍 Server will run on http://localhost:8000
📚 API Docs: http://localhost:8000/docs
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Start the LiveKit Agent (Optional for full RAG)

**Open a NEW terminal** and run:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows

# Run agent
python main.py
```

You should see:
```
INFO - registered worker
INFO - Agent starting
```

### Step 3: Open the Test Client

**Open in your browser:**
```bash
# Linux/Mac
open test_client.html

# Windows
start test_client.html

# Or just double-click test_client.html
```

**In the browser:**
1. Click "🔑 Generate Access Token"
2. Click "🚀 Connect & Start"
3. Allow microphone access
4. Start speaking in French!

---

## 📋 What You Need Running

For the **web client to work**, you need:

| Service | Required For | Port | How to Start |
|---------|-------------|------|--------------|
| **FastAPI Server** | ✅ Token generation | 8000 | `python server.py` |
| **LiveKit Server** | ✅ WebRTC audio | 7880 | See below |
| **LiveKit Agent** | ✅ AI responses | - | `python main.py` |
| **Qdrant** | ✅ RAG knowledge | 6333 | See below |

---

## 🔧 Starting All Services

### 1. Start Qdrant (Vector Database)

**Using Docker:**
```bash
docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

**Using Podman:**
```bash
podman run -d -p 6333:6333 --name qdrant qdrant/qdrant
```

**Using Podman Compose (recommended):**
```bash
podman-compose up -d
```

**Verify:**
```bash
curl http://localhost:6333/health
# Should return: {"status":"ok"}
```

### 2. Start LiveKit Server (if using local)

**Option A: Using Podman Compose (easiest)**
```bash
podman-compose up -d
# This starts both LiveKit AND Qdrant
```

**Option B: Download and run manually**
```bash
# Download LiveKit server (Linux example)
wget https://github.com/livekit/livekit/releases/download/v1.5.3/livekit_1.5.3_linux_amd64.tar.gz
tar -xzf livekit_1.5.3_linux_amd64.tar.gz

# Run with config
./livekit-server --config livekit-config.yaml
```

**Option C: Use LiveKit Cloud (no installation)**
- Sign up at https://cloud.livekit.io
- Update `.env` with your cloud credentials
- No local LiveKit server needed!

**Verify:**
```bash
curl http://localhost:7880
# Should return HTML page
```

### 3. Start FastAPI Server

```bash
# Terminal 1
python server.py
```

### 4. Start LiveKit Agent

```bash
# Terminal 2
python main.py
```

---

## 🧪 Quick Test

Once everything is running:

### Test 1: Check Services

```bash
# Test FastAPI
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# Test Qdrant
curl http://localhost:6333/health
# Expected: {"status":"ok"}

# Test LiveKit
curl http://localhost:7880
# Expected: HTML page
```

### Test 2: Generate Token Manually

```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"room_name":"test","participant_name":"TestUser"}'
```

Expected response:
```json
{
  "token": "eyJhbGc...",
  "url": "ws://localhost:7880",
  "room": "test",
  "participant": "TestUser"
}
```

### Test 3: Use Web Client

1. Open `test_client.html`
2. Click "Generate Access Token"
3. Should see: "✅ Access token generated successfully"
4. Click "Connect & Start"
5. Say "Bonjour"
6. Should hear French response!

---

## 🐛 Troubleshooting

### Issue: "Connection refused" on port 8000

**Problem:** FastAPI server not running

**Solution:**
```bash
# Start the server
python server.py

# Check if it's running
curl http://localhost:8000/health
```

### Issue: "Token generation failed"

**Problem:** Missing API keys or wrong configuration

**Solution:**
```bash
# Check your .env file
cat .env

# Make sure these are set:
# LIVEKIT_API_KEY=...
# LIVEKIT_API_SECRET=...

# If missing, copy from example
cp .env.example .env
nano .env  # Edit with your keys
```

### Issue: "Connection failed" in web client

**Problem:** LiveKit server not running

**Solution:**
```bash
# Check if LiveKit is running
curl http://localhost:7880

# If not, start it
podman-compose up -d
# OR use LiveKit Cloud
```

### Issue: "No response from assistant"

**Problem:** LiveKit agent not running

**Solution:**
```bash
# In a NEW terminal, start the agent
python main.py

# You should see:
# INFO - registered worker
# INFO - Agent starting
```

### Issue: "Qdrant connection error"

**Problem:** Qdrant not running

**Solution:**
```bash
# Start Qdrant
podman-compose up -d

# Or with Docker
docker run -d -p 6333:6333 qdrant/qdrant

# Verify
curl http://localhost:6333/health
```

---

## 📝 Minimal Setup (Just Testing Token Generation)

If you just want to test the web client connection (without AI):

```bash
# 1. Start Qdrant
podman-compose up -d qdrant

# 2. Start FastAPI server
python server.py

# 3. Open test_client.html
# - Generate token ✅
# - Connect ✅
# - But no AI responses (need agent)
```

---

## 🎯 Full Setup (With AI Responses)

For complete functionality:

```bash
# Terminal 1: Services (Qdrant + LiveKit)
podman-compose up -d

# Terminal 2: FastAPI Server
python server.py

# Terminal 3: LiveKit Agent
python main.py

# Browser: Open test_client.html
```

---

## 🔄 Typical Workflow

### Development Session

```bash
# Morning: Start everything
podman-compose up -d  # Start services
python server.py &    # Start API server in background
python main.py        # Start agent (foreground)

# Open another terminal for testing
open test_client.html

# Evening: Stop everything
pkill -f server.py    # Stop API server
pkill -f main.py      # Stop agent
podman-compose down   # Stop services
```

### Testing Session

```bash
# Just need the API server for token generation
python server.py

# Open client and test
open test_client.html
```

---

## 📊 Service Ports Reference

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| FastAPI Server | 8000 | http://localhost:8000 | Token generation, API |
| LiveKit Server | 7880 | ws://localhost:7880 | WebRTC signaling |
| LiveKit RTC | 7881 | TCP | WebRTC data |
| LiveKit UDP | 50000-50100 | UDP | WebRTC media |
| Qdrant HTTP | 6333 | http://localhost:6333 | Vector search |
| Qdrant gRPC | 6334 | - | Vector search (internal) |

---

## 🎉 Success Checklist

Before testing, verify all are ✅:

- [ ] Qdrant is running (port 6333)
- [ ] LiveKit server is running (port 7880)
- [ ] FastAPI server is running (port 8000)
- [ ] LiveKit agent is running (shows "registered worker")
- [ ] `.env` file has all required API keys
- [ ] Virtual environment is activated
- [ ] Can curl http://localhost:8000/health successfully

---

## 💡 Pro Tips

1. **Use podman-compose** - Easiest way to start services
   ```bash
   podman-compose up -d
   ```

2. **Check logs** if something fails
   ```bash
   podman logs qdrant
   podman logs livekit-server
   ```

3. **Use LiveKit Cloud** for easier setup (no local server)
   - Sign up at https://cloud.livekit.io
   - Update `.env` with cloud credentials
   - Skip local LiveKit server entirely

4. **API Documentation** is auto-generated
   - Visit http://localhost:8000/docs
   - Interactive API testing with Swagger UI

5. **Test incrementally**
   - First: Just FastAPI + token generation
   - Then: Add LiveKit connection
   - Finally: Add agent for AI responses

---

## 📚 Next Steps

Once everything works:

1. **Add documents to Qdrant** - See TESTING.md
2. **Test different queries** - See CLIENT_USAGE.md
3. **Customize responses** - Edit config.py
4. **Deploy to production** - See README.md

---

## 🆘 Still Having Issues?

1. Check all logs in each terminal
2. Review TESTING.md for detailed tests
3. Review CLIENT_USAGE.md for web client help
4. Ensure all dependencies are installed: `pip install -r requirements.txt`
5. Try `podman-compose restart` to restart services

---

**Happy Testing! 🎉**

For more details, see:
- **CLIENT_USAGE.md** - Complete web client guide
- **TESTING.md** - Detailed testing procedures
- **README.md** - Full documentation
