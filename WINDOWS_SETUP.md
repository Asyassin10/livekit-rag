# Windows Local Setup Guide

Complete guide for running the Speech-to-Speech RAG Assistant **100% locally on Windows** (no cloud, no Docker/Podman).

## 📋 Prerequisites

- Windows 10/11
- Python 3.11 or 3.12
- PowerShell
- At least 8GB RAM
- 20GB free disk space

---

## 🚀 Step-by-Step Setup

### Step 1: Install Python

Download and install Python 3.11+ from https://www.python.org/downloads/

**Important:** Check "Add Python to PATH" during installation!

Verify installation:
```powershell
python --version
# Should show: Python 3.11.x or 3.12.x
```

---

### Step 2: Clone/Download Project

```powershell
# Navigate to where you want the project
cd C:\Users\YOUR_USERNAME\Downloads

# If you have git:
git clone <repository-url> livekit-rag
cd livekit-rag

# Or download ZIP and extract it
```

**Important:** You should be in the **livekit-rag** folder (where main.py, config.py are), NOT in the LiveKit server folder!

---

### Step 3: Create Virtual Environment

```powershell
# In the project folder (livekit-rag)
python -m venv venv

# Activate it (PowerShell)
.\venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activating again
```

You should see `(venv)` at the start of your prompt.

---

### Step 4: Install Python Dependencies

```powershell
# Make sure venv is activated!
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This will take 5-10 minutes. Wait for it to complete.

---

### Step 5: Setup LiveKit Server (Local)

#### Download LiveKit Server

```powershell
# Create a separate folder for LiveKit server
mkdir C:\livekit-server
cd C:\livekit-server

# Download latest release for Windows
# Go to: https://github.com/livekit/livekit/releases
# Download: livekit_X.X.X_windows_amd64.zip
# Extract to C:\livekit-server
```

#### Create LiveKit Config

```powershell
# In C:\livekit-server folder
@"
port: 7880
bind_addresses:
  - "127.0.0.1"

rtc:
  port_range_start: 50000
  port_range_end: 50100
  tcp_port: 7881
  udp_port: 7882
  use_external_ip: false

keys:
  devkey: secret

room:
  auto_create: true
  empty_timeout: 300

logging:
  level: info
"@ | Out-File -FilePath livekit.yaml -Encoding UTF8
```

#### Start LiveKit Server

```powershell
# In C:\livekit-server folder
.\livekit-server.exe --config livekit.yaml
```

**Keep this terminal window open!** LiveKit must keep running.

You should see:
```
INFO    Starting LiveKit server
INFO    Listening on :7880
```

---

### Step 6: Setup Qdrant (Local - No Docker!)

#### Option A: Qdrant Standalone Binary (Recommended)

```powershell
# Create folder
mkdir C:\qdrant
cd C:\qdrant

# Download Windows binary
# Go to: https://github.com/qdrant/qdrant/releases
# Download: qdrant-x86_64-pc-windows-msvc.zip
# Extract to C:\qdrant

# Run Qdrant
.\qdrant.exe
```

#### Option B: If Binary Doesn't Work

You'll need Docker Desktop for Windows:
1. Install Docker Desktop from https://www.docker.com/products/docker-desktop/
2. Run: `docker run -p 6333:6333 qdrant/qdrant`

**Keep this terminal window open!** Qdrant must keep running.

You should see:
```
Qdrant started on http://localhost:6333
```

---

### Step 7: Get API Keys

You need these API keys (all have free tiers):

#### Groq API Key
1. Go to https://console.groq.com/
2. Sign up (free)
3. Create API key
4. Copy the key

#### OpenRouter API Key
1. Go to https://openrouter.ai/
2. Sign up (free)
3. Go to Keys section
4. Create API key
5. Copy the key

---

### Step 8: Configure Environment Variables

```powershell
# Go back to your project folder
cd C:\Users\YOUR_USERNAME\Downloads\livekit-rag

# Copy example file
copy .env.example .env

# Edit with notepad
notepad .env
```

**Fill in your .env file:**

```bash
# API Keys (get from respective websites)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxxx

# Local LiveKit Server
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# Local Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=harvard

# Model Settings (defaults are good)
WHISPER_MODEL=small
WHISPER_LANGUAGE=fr
WHISPER_COMPUTE_TYPE=int8
```

Save and close.

---

### Step 9: Setup Qdrant Collection

```powershell
# In your project folder with venv activated
# Create setup script
@"
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url='http://localhost:6333')

try:
    client.create_collection(
        collection_name='harvard',
        vectors_config=VectorParams(
            size=3072,
            distance=Distance.COSINE
        )
    )
    print('✅ Collection created successfully!')
except Exception as e:
    print(f'⚠️  Collection might exist: {e}')
"@ | Out-File -FilePath setup_qdrant.py -Encoding UTF8

# Run it
python setup_qdrant.py
```

You should see: `✅ Collection created successfully!`

---

### Step 10: Run the Application!

```powershell
# Make sure you have 3 terminals open:
# Terminal 1: C:\livekit-server> .\livekit-server.exe --config livekit.yaml
# Terminal 2: C:\qdrant> .\qdrant.exe
# Terminal 3: Your project folder (below)

# In your project folder with venv activated
python main.py
```

The application will:
1. Load Whisper model (takes 1-2 min first time)
2. Load Kokoro TTS model (takes 1-2 min first time)
3. Connect to LiveKit
4. Start listening for connections

---

## ✅ Verification

Test each service:

```powershell
# Test Qdrant
curl http://localhost:6333/health

# Test LiveKit (might not respond to curl, that's ok)
curl http://localhost:7880

# Check Python app imports
python -c "from config import settings; print('Config OK')"
python -c "from stt import get_stt; print('STT OK')"
python -c "from tts import get_tts; print('TTS OK')"
```

---

## 🐛 Troubleshooting

### Error: "No module named 'kokoro_onnx'"

```powershell
pip install kokoro-onnx --upgrade
```

### Error: "Can't find FFmpeg"

Install FFmpeg:
1. Download from https://www.gyan.dev/ffmpeg/builds/
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to PATH
4. Restart PowerShell

### Error: LiveKit connection failed

Check:
- Is livekit-server.exe running?
- Check firewall isn't blocking port 7880
- Try: `netstat -an | findstr 7880`

### Error: Qdrant connection failed

Check:
- Is qdrant.exe running?
- Try: `netstat -an | findstr 6333`
- Verify: `curl http://localhost:6333/health`

### Error: "Execution policy" when activating venv

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Models downloading slowly

First run downloads:
- Whisper model (~150MB)
- Kokoro TTS models (~50MB)

Be patient, they only download once!

---

## 📁 Folder Structure

```
C:\
├── livekit-server\
│   ├── livekit-server.exe
│   └── livekit.yaml
│
├── qdrant\
│   └── qdrant.exe
│
└── Users\YOUR_USERNAME\Downloads\
    └── livekit-rag\          ← Your project (work here!)
        ├── venv\
        ├── main.py
        ├── config.py
        ├── .env
        └── ...
```

---

## 🎯 Summary Checklist

- [ ] Python 3.11+ installed
- [ ] Project folder (livekit-rag) with venv created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] LiveKit server downloaded and running
- [ ] Qdrant downloaded and running
- [ ] API keys obtained (Groq, OpenRouter)
- [ ] .env file configured
- [ ] Qdrant collection created
- [ ] Application runs without errors

---

## 🎉 Next Steps

Once everything is running:

1. Test the STT: Record audio and check if Whisper transcribes correctly
2. Test RAG: Add documents to Qdrant collection
3. Test TTS: Check if Kokoro generates French audio
4. Build a frontend to connect via WebRTC

---

## 💡 Tips

- Keep all 3 terminals open while using the app
- Models are cached after first download
- Use `Ctrl+C` to stop each service
- Check logs if something breaks

---

## 🆘 Still Having Issues?

Check the main README.md or create an issue with:
- Your Windows version
- Python version (`python --version`)
- Error message (full traceback)
- Which step failed
