"""
Main application: FastAPI + LiveKit Agent for Speech-to-Speech RAG Assistant
Manual pipeline using local Whisper STT, Groq LLM, and Kokoro TTS
"""
import asyncio
import logging
import random
import io
import wave
import numpy as np
from typing import Optional, Annotated
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import rtc, api
from livekit.agents import (
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import silero

from config import (
    settings,
    GREETING_RESPONSES,
    THANKS_RESPONSES,
    GOODBYE_RESPONSES,
)
from stt import get_stt
from rag import get_rag
from llm import get_llm
from tts import get_tts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Initialize RAG components globally
rag_instance = None


def get_rag_instance():
    """Get or create RAG instance"""
    global rag_instance
    if rag_instance is None:
        rag_instance = get_rag()
    return rag_instance


class ConversationDetector:
    """Detect greetings, thanks, and goodbye messages"""

    @staticmethod
    def is_greeting(text: str) -> bool:
        """Check if text is a greeting"""
        text_lower = text.lower().strip()
        return any(keyword in text_lower for keyword in settings.GREETING_KEYWORDS)

    @staticmethod
    def is_thanks(text: str) -> bool:
        """Check if text is a thank you message"""
        text_lower = text.lower().strip()
        return any(keyword in text_lower for keyword in settings.THANKS_KEYWORDS)

    @staticmethod
    def is_goodbye(text: str) -> bool:
        """Check if text is a goodbye message"""
        text_lower = text.lower().strip()
        return any(keyword in text_lower for keyword in settings.GOODBYE_KEYWORDS)

    @staticmethod
    def get_response(text: str) -> Optional[str]:
        """Get appropriate response for conversation cues"""
        if ConversationDetector.is_greeting(text):
            return random.choice(GREETING_RESPONSES)
        elif ConversationDetector.is_thanks(text):
            return random.choice(THANKS_RESPONSES)
        elif ConversationDetector.is_goodbye(text):
            return random.choice(GOODBYE_RESPONSES)
        return None


def prewarm(proc: JobProcess):
    """Prewarm function to load models"""
    # Load VAD model
    proc.userdata["vad"] = silero.VAD.load()
    
    # Prewarm STT, LLM, TTS
    proc.userdata["stt"] = get_stt()
    proc.userdata["llm"] = get_llm()
    proc.userdata["tts"] = get_tts()
    proc.userdata["rag"] = get_rag_instance()
    
    logger.info("All models prewarmed (VAD, STT, LLM, TTS, RAG)")


def wav_to_audio_frame(wav_data: bytes, sample_rate: int = 24000) -> rtc.AudioFrame:
    """Convert WAV bytes to LiveKit AudioFrame"""
    # Parse WAV data
    with wave.open(io.BytesIO(wav_data), 'rb') as wav_file:
        frames = wav_file.readframes(wav_file.getnframes())
        # Convert to int16 numpy array
        audio_array = np.frombuffer(frames, dtype=np.int16)
    
    # Create AudioFrame
    return rtc.AudioFrame(
        data=audio_array.tobytes(),
        sample_rate=sample_rate,
        num_channels=1,
        samples_per_channel=len(audio_array)
    )


async def entrypoint(ctx: JobContext):
    """
    LiveKit agent entrypoint with manual STT/LLM/TTS pipeline
    """
    logger.info("Agent starting")

    # Connect to room
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    # Get local components from prewarm
    vad = ctx.proc.userdata["vad"]
    stt_instance = ctx.proc.userdata["stt"]
    llm_instance = ctx.proc.userdata["llm"]
    tts_instance = ctx.proc.userdata["tts"]
    rag_instance = ctx.proc.userdata["rag"]

    # Create audio source for agent's voice
    audio_source = rtc.AudioSource(24000, 1)  # 24kHz, mono
    audio_track = rtc.LocalAudioTrack.create_audio_track("agent-voice", audio_source)
    
    # Publish audio track
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    await ctx.room.local_participant.publish_track(audio_track, options)
    logger.info("Agent audio track published")

    # Wait for participant
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Send initial greeting
    greeting_text = "Bonjour! Je suis l'assistant vocal de Harvard. Comment puis-je vous aider?"
    logger.info(f"Greeting: {greeting_text}")
    
    greeting_audio = tts_instance.synthesize(greeting_text)
    if greeting_audio:
        frame = wav_to_audio_frame(greeting_audio)
        await audio_source.capture_frame(frame)
        logger.info("Greeting sent")

    # Buffer for collecting audio chunks
    audio_buffer = []
    is_speaking = False
    silence_duration = 0
    SILENCE_THRESHOLD = 1.5  # seconds of silence before processing
    
    # Track to process
    processing_track = None
    
    async def process_speech():
        """Process collected speech audio"""
        nonlocal audio_buffer, is_speaking, silence_duration
        
        try:
            if not audio_buffer:
                return
                
            # Combine audio buffer
            combined_audio = b''.join(audio_buffer)
            
            # Convert to WAV format for STT
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(24000)
                wav_file.writeframes(combined_audio)
            
            wav_data = wav_buffer.getvalue()
            
            # Transcribe
            transcription = stt_instance.transcribe_stream(wav_data)
            
            if not transcription:
                logger.warning("No transcription received")
                return
            
            logger.info(f"User said: {transcription}")
            
            # Check for conversation cues
            quick_response = ConversationDetector.get_response(transcription)
            
            if quick_response:
                response_text = quick_response
                logger.info(f"Quick response: {response_text}")
            else:
                # Check if RAG search is needed
                context = None
                if any(keyword in transcription.lower() for keyword in ["harvard", "université", "campus", "programme", "étudiant"]):
                    try:
                        documents = await rag_instance.retrieve(transcription)
                        if documents:
                            context = rag_instance.format_context(documents)
                            logger.info(f"RAG context retrieved: {len(documents)} documents")
                    except Exception as e:
                        logger.error(f"RAG error: {e}")
                
                # Get LLM response
                response_text = await llm_instance.get_response(transcription, context)
                logger.info(f"LLM response: {response_text}")
            
            # Synthesize response
            response_audio = tts_instance.synthesize(response_text)
            
            if response_audio:
                frame = wav_to_audio_frame(response_audio)
                await audio_source.capture_frame(frame)
                logger.info("Response sent")
            else:
                logger.error("Failed to synthesize response")
                
        except Exception as e:
            logger.error(f"Error processing speech: {e}", exc_info=True)
        finally:
            # Reset buffer
            audio_buffer = []
            is_speaking = False
            silence_duration = 0

    async def process_audio_stream(track: rtc.RemoteAudioTrack):
        """Process audio from remote track"""
        nonlocal audio_buffer, is_speaking, silence_duration
        
        logger.info("Starting audio stream processing")
        audio_stream = rtc.AudioStream(track)
        
        try:
            async for audio_frame_event in audio_stream:
                audio_frame = audio_frame_event.frame
                
                # Convert frame to numpy for VAD
                audio_data = np.frombuffer(audio_frame.data, dtype=np.int16)
                audio_float = audio_data.astype(np.float32) / 32768.0
                
                # Check if speech is detected
                speech_detected = await vad.stream(audio_float)

                
                if speech_detected:
                    is_speaking = True
                    silence_duration = 0
                    audio_buffer.append(audio_frame.data)
                elif is_speaking:
                    # Still in speech but this frame is silent
                    silence_duration += len(audio_data) / audio_frame.sample_rate
                    audio_buffer.append(audio_frame.data)
                    
                    # Check if silence threshold reached
                    if silence_duration >= SILENCE_THRESHOLD:
                        # Process the collected audio
                        await process_speech()
        except Exception as e:
            logger.error(f"Error in audio stream processing: {e}", exc_info=True)

    # Subscribe to participant's audio track
    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.RemoteAudioTrack,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        nonlocal processing_track
        
        logger.info(f"Subscribed to audio track from {participant.identity}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            # Start processing audio in background
            processing_track = asyncio.create_task(process_audio_stream(track))
            logger.info("Audio processing task created")

    # Keep running - wait forever until cancelled
    logger.info("Agent running - listening for audio")
    
    try:
        await asyncio.Future()  # Wait forever
    except asyncio.CancelledError:
        logger.info("Agent task cancelled, cleaning up")


# FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting FastAPI application")

    # Initialize RAG instance
    get_rag_instance()

    yield

    logger.info("Shutting down FastAPI application")


app = FastAPI(
    title="Speech-to-Speech RAG Assistant",
    description="LiveKit-powered voice assistant with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Token request model
class TokenRequest(BaseModel):
    room_name: str
    participant_name: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Speech-to-Speech RAG Assistant",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/webhook")
async def webhook(request: Request):
    """LiveKit webhook endpoint"""
    try:
        body = await request.json()
        logger.info(f"Webhook received: {body}")
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/token")
async def generate_token(request: TokenRequest):
    """Generate LiveKit access token for client"""
    try:
        # Create access token
        token = api.AccessToken(
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        )

        # Set identity and grants
        token.with_identity(request.participant_name)
        token.with_name(request.participant_name)
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=request.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )

        # Generate JWT
        access_token = token.to_jwt()

        logger.info(f"Generated token for {request.participant_name} in room {request.room_name}")

        return {
            "token": access_token,
            "url": settings.LIVEKIT_URL,
            "room": request.room_name,
            "participant": request.participant_name,
        }

    except Exception as e:
        logger.error(f"Token generation error: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


def main():
    """Main entry point"""
    # Run LiveKit agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            ws_url=settings.LIVEKIT_URL,
        )
    )


if __name__ == "__main__":
    main()