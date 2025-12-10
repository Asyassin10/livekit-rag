"""
Simple LiveKit Voice Agent: Voice → STT → RAG → LLM → TTS → Voice
"""
import asyncio
import logging
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero

from config import settings
from rag import get_rag

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prewarm(proc: JobProcess):
    """Prewarm models"""
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    """Main agent entrypoint"""
    logger.info("Starting voice agent...")

    # Initialize RAG
    rag = get_rag()

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"Connected to room: {ctx.room.name}")

    # Wait for participant
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Define the chat context with RAG function
    async def search_knowledge(query: str):
        """Search Harvard knowledge base"""
        logger.info(f"RAG search: {query}")
        try:
            documents = await rag.retrieve(query)
            if documents:
                context = rag.format_context(documents)
                logger.info(f"Found {len(documents)} documents")
                return context
            return "No information found."
        except Exception as e:
            logger.error(f"RAG error: {e}")
            return "Error searching knowledge base."

    # Create assistant with French instructions
    assistant = llm.AssistantLlmContext(
        instructions="""Tu es l'assistant vocal de Harvard University.
Réponds en français de façon claire et concise (1-2 phrases maximum).
Pour répondre aux questions sur Harvard, utilise la fonction search_knowledge.
Pour les salutations simples, réponds directement sans chercher.""",
        functions=[
            llm.FunctionContext(
                name="search_knowledge",
                description="Search the Harvard knowledge base for information",
                callable=search_knowledge,
            )
        ],
    )

    # Create voice pipeline agent
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(),  # Speech-to-Text
        llm=openai.LLM(),     # LLM (works with Groq-compatible APIs)
        tts=openai.TTS(),     # Text-to-Speech
        chat_ctx=assistant,
    )

    # Start the agent
    agent.start(ctx.room, participant)
    logger.info("Agent started successfully!")

    # Send greeting
    await agent.say(
        "Bonjour! Je suis l'assistant vocal de Harvard. Comment puis-je vous aider?",
        allow_interruptions=True
    )

    logger.info("Agent ready - waiting for voice input...")


def main():
    """Run the agent"""
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
