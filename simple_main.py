"""
Simple Speech-to-Speech RAG Assistant
Flow: Audio → Whisper → RAG (Qdrant) → LLM → TTS → Audio
"""
import asyncio
import logging
from livekit.agents import (
    WorkerOptions,
    cli,
    JobContext,
)
from livekit import rtc

from config import settings
from stt import get_stt
from rag import get_rag
from llm import get_llm
from tts import get_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleVoiceAgent:
    """Simple voice agent: Speech → RAG → LLM → Speech"""

    def __init__(self):
        self.stt = get_stt()
        self.rag = get_rag()
        self.llm = get_llm()
        self.tts = get_tts()
        logger.info("✅ Agent initialized")

    async def process_audio(self, audio_data: bytes) -> bytes:
        """
        Process audio through the full pipeline

        Flow:
        1. Audio → Text (Whisper)
        2. Text → RAG → Context chunks (Qdrant)
        3. Context + Question → LLM → Answer
        4. Answer → Audio (TTS)
        """
        try:
            # Step 1: Speech to Text
            logger.info("🎤 Transcribing audio...")
            text = self.stt.transcribe_stream(audio_data)
            if not text:
                logger.warning("No text transcribed")
                return None
            logger.info(f"📝 User said: {text}")

            # Step 2: Get relevant context from RAG
            logger.info("🔍 Searching knowledge base...")
            documents = await self.rag.retrieve(text)
            context = self.rag.format_context(documents)
            logger.info(f"📚 Found {len(documents)} relevant documents")

            # Step 3: Generate answer with LLM
            logger.info("🤖 Generating response...")
            answer = await self.llm.get_response(text, context)
            logger.info(f"💬 Response: {answer}")

            # Step 4: Convert answer to speech
            logger.info("🔊 Synthesizing speech...")
            audio_response = self.tts.synthesize(answer)
            logger.info("✅ Audio generated")

            return audio_response

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return None


async def entrypoint(ctx: JobContext):
    """LiveKit agent entry point"""
    logger.info("🚀 Starting agent...")

    # Initialize agent
    agent = SimpleVoiceAgent()

    # Connect to room
    await ctx.connect()
    logger.info(f"📡 Connected to room: {ctx.room.name}")

    # Wait for participant
    participant = await ctx.wait_for_participant()
    logger.info(f"👤 Participant joined: {participant.identity}")

    # Send greeting
    greeting = "Bonjour! Je suis l'assistant de Harvard. Comment puis-je vous aider?"
    greeting_audio = agent.tts.synthesize(greeting)

    # Create audio track and publish greeting
    audio_source = rtc.AudioSource(24000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("assistant", audio_source)
    await ctx.room.local_participant.publish_track(track)

    # Send greeting audio
    if greeting_audio:
        await audio_source.capture_frame(
            rtc.AudioFrame(
                data=greeting_audio[44:],  # Skip WAV header
                sample_rate=24000,
                num_channels=1,
                samples_per_channel=len(greeting_audio[44:]) // 2
            )
        )

    logger.info("✅ Agent ready and waiting for audio...")

    # Keep running
    await asyncio.Future()


def main():
    """Run the agent"""
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
