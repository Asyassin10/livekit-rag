"""
Main application: FastAPI + LiveKit Agent for Speech-to-Speech RAG Assistant
"""
import asyncio
import logging
import random
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
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


class SpeechRAGAssistant:
    """Speech-to-Speech RAG Assistant"""

    def __init__(self):
        """Initialize assistant components"""
        self.stt = get_stt()
        self.rag = get_rag()
        self.llm = get_llm()
        self.tts = get_tts()
        self.conversation_detector = ConversationDetector()
        self.is_speaking = False
        logger.info("Speech RAG Assistant initialized")

    async def process_user_input(
        self, text: str, room: rtc.Room, participant: rtc.Participant
    ):
        """
        Process user input and generate response

        Args:
            text: Transcribed user input
            room: LiveKit room
            participant: User participant
        """
        try:
            logger.info(f"Processing user input: {text}")

            # Check for conversation cues (greeting, thanks, goodbye)
            quick_response = self.conversation_detector.get_response(text)

            if quick_response:
                # Respond without RAG for conversational messages
                logger.info(f"Quick response: {quick_response}")
                await self.speak(quick_response, room)
            else:
                # Use RAG pipeline for knowledge queries
                await self.process_rag_query(text, room)

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            await self.speak(
                "Désolé, une erreur s'est produite.", room
            )

    async def process_rag_query(self, query: str, room: rtc.Room):
        """
        Process query using RAG pipeline

        Args:
            query: User query
            room: LiveKit room
        """
        try:
            # 1. Retrieve relevant documents
            documents = await self.rag.retrieve(query)

            # 2. Format context
            context = self.rag.format_context(documents)

            if context:
                logger.info(f"Retrieved {len(documents)} documents")
            else:
                logger.info("No relevant documents found")

            # 3. Stream LLM response
            response_text = ""
            async for chunk in self.llm.stream_response(query, context):
                response_text += chunk

            # 4. Synthesize and speak response
            if response_text:
                await self.speak(response_text, room)

        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            await self.speak(
                "Je n'ai pas pu trouver d'information sur ce sujet.", room
            )

    async def speak(self, text: str, room: rtc.Room):
        """
        Synthesize speech and send to room

        Args:
            text: Text to speak
            room: LiveKit room
        """
        try:
            self.is_speaking = True
            logger.info(f"Speaking: {text}")

            # Synthesize audio with streaming
            audio_source = rtc.AudioSource(24000, 1)  # 24kHz, mono
            track = rtc.LocalAudioTrack.create_audio_track("assistant-voice", audio_source)

            # Publish track
            options = rtc.TrackPublishOptions()
            options.source = rtc.TrackSource.SOURCE_MICROPHONE
            publication = await room.local_participant.publish_track(track, options)

            # Stream TTS audio
            async for audio_chunk in self.tts.synthesize_stream(text):
                if audio_chunk:
                    # Convert WAV bytes to PCM frames
                    # Skip WAV header (44 bytes) and send raw PCM data
                    pcm_data = audio_chunk[44:]

                    # Create audio frame
                    frame = rtc.AudioFrame(
                        data=pcm_data,
                        sample_rate=24000,
                        num_channels=1,
                        samples_per_channel=len(pcm_data) // 2,
                    )
                    await audio_source.capture_frame(frame)

            # Unpublish track
            await room.local_participant.unpublish_track(track.sid)
            self.is_speaking = False

        except Exception as e:
            logger.error(f"Error speaking: {e}")
            self.is_speaking = False

    def should_interrupt(self) -> bool:
        """Check if assistant should be interrupted (barge-in)"""
        return self.is_speaking


# Global assistant instance
assistant: Optional[SpeechRAGAssistant] = None


async def entrypoint(ctx: JobContext):
    """
    LiveKit agent entrypoint

    Args:
        ctx: Job context from LiveKit
    """
    global assistant

    logger.info("Agent starting")

    # Initialize assistant
    if assistant is None:
        assistant = SpeechRAGAssistant()

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"Connected to room: {ctx.room.name}")

    # Setup audio streaming
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Audio buffer for streaming
    audio_buffer = bytearray()

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        """Handle new audio track"""
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"Audio track subscribed: {track.sid}")

            audio_stream = rtc.AudioStream(track)
            asyncio.create_task(process_audio_stream(audio_stream, ctx.room, participant))

    async def process_audio_stream(
        audio_stream: rtc.AudioStream,
        room: rtc.Room,
        participant: rtc.RemoteParticipant,
    ):
        """Process incoming audio stream"""
        logger.info("Processing audio stream")

        async for event in audio_stream:
            # Collect audio frames
            # In production, implement proper VAD and buffering
            # For now, we process on silence detection
            pass

    # Send initial greeting
    await assistant.speak(
        "Bonjour! Je suis l'assistant vocal de Harvard. Comment puis-je vous aider?",
        ctx.room,
    )

    # Keep agent running
    logger.info("Agent running")


# FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting application")

    # Initialize components
    global assistant
    assistant = SpeechRAGAssistant()

    yield

    logger.info("Shutting down application")


app = FastAPI(
    title="Speech-to-Speech RAG Assistant",
    description="LiveKit-powered voice assistant with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan,
)


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


def main():
    """Main entry point"""
    # Run LiveKit agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            ws_url=settings.LIVEKIT_URL,
        )
    )


if __name__ == "__main__":
    main()
