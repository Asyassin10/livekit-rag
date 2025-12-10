# 🎤 LiveKit Test Client Usage Guide

Complete guide for testing the Speech-to-Speech RAG Assistant using the web client.

---

## 📋 Prerequisites

Before using the test client, ensure:

1. ✅ **Qdrant is running** (port 6333)
2. ✅ **LiveKit server is running** (port 7880 or cloud)
3. ✅ **FastAPI backend is running** (port 8000)
4. ✅ **Environment variables are configured** (.env file)

---

## 🚀 Quick Start

### Step 1: Start the Backend

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\Activate.ps1  # Windows

# Start the FastAPI backend with LiveKit agent
python main.py

# You should see:
# INFO - registered worker
# INFO - Agent starting
```

### Step 2: Open the Test Client

Open `test_client.html` in your web browser:

```bash
# Linux/Mac
open test_client.html

# Windows
start test_client.html

# Or simply double-click the file
```

### Step 3: Configure Settings

In the web interface:

1. **LiveKit Server URL**:
   - Local: `ws://localhost:7880`
   - Cloud: `wss://your-project.livekit.cloud`

2. **FastAPI Backend URL**:
   - Local: `http://localhost:8000`
   - Remote: Your deployed API URL

3. **Room Name**: Any name (e.g., `test-room`)

4. **Your Name**: Your participant name (e.g., `Test User`)

### Step 4: Generate Token

Click **"🔑 Generate Access Token"**

- The client will call `/token` endpoint
- You'll see: "✅ Access token generated successfully"
- The "Connect" button will be enabled

### Step 5: Connect & Talk

Click **"🚀 Connect & Start"**

- Browser will request microphone permission
- You'll see: "✅ Connected"
- Status will show: "🎤 Microphone enabled - Start speaking!"

### Step 6: Test Conversation

Try these French phrases:

**Greetings:**
- "Bonjour"
- "Salut"
- "Bonsoir"

**Questions about Harvard:**
- "Quand Harvard a-t-elle été fondée?"
- "Parle-moi de Harvard"
- "Qu'est-ce que Harvard?"

**Thanks:**
- "Merci"
- "Merci beaucoup"

**Goodbye:**
- "Au revoir"
- "À bientôt"

---

## 🎨 User Interface Guide

### Status Indicator

- **❌ Disconnected** (Red) - Not connected
- **⏳ Connecting** (Yellow) - Connecting to server
- **✅ Connected** (Green) - Active connection

### Audio Indicator

Animated bars appear when connected, showing audio activity.

### Stats Dashboard

- **Participants**: Number of users in the room
- **Audio Tracks**: Active audio streams
- **Connection**: Connection quality rating

### Conversation Panel

Shows all messages with timestamps:
- **Blue messages**: Your speech (if transcription is sent)
- **Green messages**: Assistant responses
- **Yellow messages**: System notifications

---

## 🔧 Configuration Options

### Local Development Setup

```javascript
LiveKit URL: ws://localhost:7880
API URL: http://localhost:8000
Room: test-room
Name: Test User
```

### Cloud LiveKit Setup

```javascript
LiveKit URL: wss://your-project.livekit.cloud
API URL: https://your-api.example.com
Room: production-room
Name: Your Name
```

---

## 🔍 Troubleshooting

### Issue: "Failed to generate token"

**Causes:**
- FastAPI backend not running
- Wrong API URL
- CORS issues

**Solutions:**
```bash
# Check if backend is running
curl http://localhost:8000/health

# Expected: {"status":"healthy"}

# Check token endpoint manually
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"room_name":"test","participant_name":"user"}'
```

### Issue: "Connection failed"

**Causes:**
- LiveKit server not running
- Wrong LiveKit URL
- Network/firewall issues

**Solutions:**
```bash
# Test LiveKit server
curl http://localhost:7880

# Check if LiveKit is accessible
# Should return HTML page or error
```

### Issue: "Microphone not working"

**Causes:**
- Browser permissions denied
- No microphone detected
- HTTPS required (for remote servers)

**Solutions:**
- Check browser microphone permissions
- Use Chrome/Firefox (best compatibility)
- For remote testing, use HTTPS
- Test microphone in browser settings

### Issue: "No response from assistant"

**Causes:**
- Agent not running
- RAG not configured
- API keys missing
- Qdrant not running

**Solutions:**
```bash
# Check agent logs
# You should see:
# INFO - Participant joined: Test User
# INFO - Transcription: ...
# INFO - RAG retrieved N documents

# Test RAG manually
python test_pipeline.py

# Check Qdrant
curl http://localhost:6333/health
```

### Issue: CORS errors in browser console

**Cause:** FastAPI CORS not configured

**Solution:** Already fixed in main.py with:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🎯 Testing Scenarios

### Test 1: Basic Connection

1. Generate token
2. Connect
3. Should see "Connected" status
4. Should see participant count: 2 (you + agent)

### Test 2: Greeting Detection

1. Say: "Bonjour"
2. Should get direct response (no RAG)
3. Expected: "Bonjour! Comment puis-je vous aider?"

### Test 3: RAG Query

1. Say: "Quand Harvard a-t-elle été fondée?"
2. Agent should search Qdrant
3. Should hear answer with Harvard founding date

### Test 4: Thanks & Goodbye

1. Say: "Merci"
2. Expected: "Je vous en prie!" or similar
3. Say: "Au revoir"
4. Expected: "Au revoir! Bonne journée!" or similar

### Test 5: Multiple Turns

1. Say: "Bonjour"
2. Wait for response
3. Say: "Parle-moi de Harvard"
4. Wait for response
5. Say: "Merci"
6. Say: "Au revoir"

---

## 📊 What to Monitor

### Browser Console (F12)

Monitor for:
- ✅ "Participant connected"
- ✅ "Track subscribed: audio"
- ✅ Connection quality updates
- ❌ WebSocket errors
- ❌ Audio playback errors

### FastAPI Logs

Monitor for:
- ✅ "Generated token for..."
- ✅ "Agent starting"
- ✅ "Participant joined"
- ✅ "Transcription: ..."
- ✅ "RAG retrieved N documents"
- ✅ "LLM response: ..."

### Network Tab

Monitor:
- POST `/token` → 200 OK
- WebSocket connection → 101 Switching Protocols
- No CORS errors

---

## 🔐 Security Notes

### Development Mode

The current setup uses:
- `allow_origins=["*"]` - Accepts all origins
- No authentication on token endpoint
- Tokens valid indefinitely

**⚠️ This is OK for local development only!**

### Production Recommendations

1. **Restrict CORS origins:**
```python
allow_origins=["https://yourdomain.com"]
```

2. **Add authentication:**
```python
@app.post("/token")
async def generate_token(request: TokenRequest, api_key: str = Header(...)):
    # Verify API key
    if api_key != settings.CLIENT_API_KEY:
        raise HTTPException(401, "Unauthorized")
    # ... rest of code
```

3. **Add rate limiting:**
```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/token")
@limiter.limit("5/minute")
async def generate_token(...):
    # ...
```

4. **Set token expiration:**
```python
token.with_ttl("1h")  # Token expires in 1 hour
```

---

## 🎨 Customization

### Change UI Colors

Edit `test_client.html`:

```css
/* Line 15 - Background gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Line 135 - Connect button */
.btn-connect {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

### Add Custom Messages

```javascript
// Line ~320 - After connection
addMessage('system', 'Custom welcome message!');
```

### Change Default Values

```html
<!-- Line ~90 -->
<input type="text" id="livekit-url" value="ws://localhost:7880">
<input type="text" id="room-name" value="my-custom-room">
```

---

## 📱 Mobile Testing

The client works on mobile browsers:

1. **Deploy backend to public URL** (use ngrok or similar)
2. **Update URLs in client** to use HTTPS
3. **Open on mobile browser**
4. **Grant microphone permissions**

**Note:** Mobile requires HTTPS for microphone access!

---

## 🔄 Testing Workflow

### Complete Testing Flow

```bash
# Terminal 1: Start Qdrant (if not running)
docker run -p 6333:6333 qdrant/qdrant

# Terminal 2: Add test documents to Qdrant
python
>>> from rag import get_rag
>>> import asyncio
>>> # ... add documents (see TESTING.md)

# Terminal 3: Start FastAPI + LiveKit agent
python main.py

# Browser: Open test_client.html
# 1. Generate token
# 2. Connect
# 3. Start talking!
```

---

## 📝 Advanced Features

### Data Messages (Future Enhancement)

The client already listens for data messages:

```javascript
// If agent sends transcriptions via data channel
room.on(LivekitClient.RoomEvent.DataReceived, (payload, participant) => {
    const message = JSON.parse(new TextDecoder().decode(payload));
    if (message.type === 'transcription') {
        addMessage('user', `You said: ${message.text}`);
    }
});
```

To implement in agent, add:
```python
# In agent code
await room.local_participant.publish_data(
    json.dumps({"type": "transcription", "text": transcription}).encode()
)
```

### Recording Sessions

Add recording button:

```javascript
let recorder = null;

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    recorder.start();
}
```

---

## 🎉 Success Indicators

You'll know everything is working when:

1. ✅ Token generated successfully
2. ✅ "Connected" status is green
3. ✅ Participant count shows 2
4. ✅ Audio tracks count shows 1+
5. ✅ You hear the greeting: "Bonjour! Je suis l'assistant vocal de Harvard..."
6. ✅ Your questions get French responses
7. ✅ Conversation appears in the panel

---

## 📚 Related Documentation

- **TESTING.md** - Complete testing guide
- **SIMPLE_GUIDE.md** - Simple RAG pipeline guide
- **README.md** - Full project documentation

---

## 🐛 Common Pitfalls

1. **Forgetting to start backend** → No token generation
2. **Wrong LiveKit URL format** → Connection fails
3. **HTTP instead of HTTPS on remote** → Microphone blocked
4. **No documents in Qdrant** → Empty RAG responses
5. **Missing API keys in .env** → Embedding/LLM errors

---

## 💡 Tips

1. **Test locally first** before deploying
2. **Use Chrome DevTools** to monitor network/console
3. **Check all three logs**: Browser, FastAPI, and Qdrant
4. **Test simple greetings** before complex queries
5. **Add test documents** to Qdrant for better responses
6. **Speak clearly** for better transcription
7. **Wait for responses** before speaking again

---

**Happy Testing! 🎉**

For issues or questions, check the troubleshooting section or review the logs.
